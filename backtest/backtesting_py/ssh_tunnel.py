"""SSH tunnel for remote ClickHouse access.

ADR: docs/adr/2026-02-06-repository-creation.md

Copied from rangebar-py/python/rangebar/clickhouse/tunnel.py (canonical implementation).
ClickHouse on BigBlack only listens on localhost:8123 — SSH tunnel is required.
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType


def _find_free_port() -> int:
    """Find a free local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except OSError:
        return False


class SSHTunnel:
    """SSH tunnel to remote ClickHouse host (context manager).

    Creates an SSH tunnel from a local port to the remote host's
    ClickHouse HTTP API (port 8123).

    Examples
    --------
    >>> with SSHTunnel("bigblack") as local_port:
    ...     client = clickhouse_connect.get_client("localhost", local_port)
    """

    def __init__(
        self,
        ssh_alias: str,
        remote_port: int = 8123,
        local_port: int | None = None,
    ) -> None:
        self.ssh_alias = ssh_alias
        self.remote_port = remote_port
        self._local_port = local_port
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def local_port(self) -> int | None:
        return self._local_port

    @property
    def is_active(self) -> bool:
        return (
            self._process is not None
            and self._process.poll() is None
            and self._local_port is not None
            and _is_port_open("localhost", self._local_port)
        )

    def start(self, timeout: float = 5.0) -> int:
        """Start the SSH tunnel. Returns local port."""
        if self._process is not None:
            msg = "Tunnel already started"
            raise RuntimeError(msg)

        if self._local_port is None:
            self._local_port = _find_free_port()

        self._process = subprocess.Popen(
            [
                "ssh",
                "-N",
                "-o", "ExitOnForwardFailure=yes",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
                "-L", f"{self._local_port}:localhost:{self.remote_port}",
                self.ssh_alias,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if _is_port_open("localhost", self._local_port):
                return self._local_port

            exit_code = self._process.poll()
            if exit_code is not None:
                if exit_code == 0:
                    time.sleep(0.2)
                    if _is_port_open("localhost", self._local_port):
                        self._process = None
                        return self._local_port
                stderr = ""
                if self._process.stderr:
                    stderr = self._process.stderr.read().decode()
                msg = f"SSH tunnel to {self.ssh_alias} failed (exit={exit_code}): {stderr}"
                self._process = None
                raise RuntimeError(msg)

            time.sleep(0.1)

        self._cleanup()
        msg = f"SSH tunnel to {self.ssh_alias} timed out after {timeout}s"
        raise RuntimeError(msg)

    def stop(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self._process.kill()
                    self._process.wait(timeout=1)
                except (subprocess.TimeoutExpired, OSError):
                    pass
            finally:
                for stream in (self._process.stdin, self._process.stdout, self._process.stderr):
                    if stream is not None:
                        with contextlib.suppress(OSError):
                            stream.close()
                self._process = None

    def __enter__(self) -> int:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()

    def __del__(self) -> None:
        self._cleanup()
