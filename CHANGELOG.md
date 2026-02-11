# [1.2.0](https://github.com/terrylica/rangebar-patterns/compare/v1.1.0...v1.2.0) (2026-02-11)


### Features

* add sweep-methodology skill — invariant-based guidelines for brute-force pattern discovery ([d20e6a7](https://github.com/terrylica/rangebar-patterns/commit/d20e6a7331ae9ad1963e1588e1e296fe9c46bd08))

# [1.1.0](https://github.com/terrylica/rangebar-patterns/compare/v1.0.0...v1.1.0) (2026-02-11)


### Features

* atomic trade reconstruction — bar-by-bar inspection of ClickHouse configs ([#13](https://github.com/terrylica/rangebar-patterns/issues/13)) ([be87872](https://github.com/terrylica/rangebar-patterns/commit/be87872ece0860c2672ec948adb4ab63f90bad43)), closes [hi#performing](https://github.com/hi/issues/performing)

# 1.0.0 (2026-02-08)


### Bug Fixes

* add repo root to sys.path in backtesting tests ([1f3fda6](https://github.com/terrylica/rangebar-patterns/commit/1f3fda62ea6c645217e5083ddbff4bfb8dc5eb2d))
* correct DSR var_sr bug (unit variance) + NaN Kelly correlation filter ([f4d4c22](https://github.com/terrylica/rangebar-patterns/commit/f4d4c22c931340dc6667d9ab5ff1df4297bced4b)), closes [#12](https://github.com/terrylica/rangebar-patterns/issues/12)
* **gen300:** rolling 1000-bar window, barrier grid, AP-10 rewrite ([b6d84af](https://github.com/terrylica/rangebar-patterns/commit/b6d84af0883ac32c733c18dcaa17b18a86189661)), closes [#10](https://github.com/terrylica/rangebar-patterns/issues/10)


### Features

* add ClickHouse anti-pattern skill (13 SQL + 3 infra constraints) ([609c3be](https://github.com/terrylica/rangebar-patterns/commit/609c3beaefd8e72652e5d4e64fd7ad32d4395e08)), closes [#8](https://github.com/terrylica/rangebar-patterns/issues/8)
* atomic validation + backtesting.py barrier alignment ([c85d2c3](https://github.com/terrylica/rangebar-patterns/commit/c85d2c311aa10088b7723a922bc7bc4a8aa78c8e)), closes [#6](https://github.com/terrylica/rangebar-patterns/issues/6) [#7](https://github.com/terrylica/rangebar-patterns/issues/7)
* beyond-Kelly 9-agent POC — 6-metric stack recommendation ([cd6ecc0](https://github.com/terrylica/rangebar-patterns/commit/cd6ecc0a09a9c85c0d62b9d32f98a5d920500d09)), closes [#12](https://github.com/terrylica/rangebar-patterns/issues/12)
* collect Gen500-520 overnight sweep results (15,300 configs) ([d73254b](https://github.com/terrylica/rangebar-patterns/commit/d73254b72c006bd808e190a803b897b60380fadf))
* Gen200-202 triple barrier + trailing stop SQL framework ([d7979f9](https://github.com/terrylica/rangebar-patterns/commit/d7979f99a6dad4c2920779d6851d21fdf37c8704)), closes [#3](https://github.com/terrylica/rangebar-patterns/issues/3) [#4](https://github.com/terrylica/rangebar-patterns/issues/4) [#5](https://github.com/terrylica/rangebar-patterns/issues/5)
* Gen300 feature filter sweep — 4 positive-Kelly configs found ([64370c0](https://github.com/terrylica/rangebar-patterns/commit/64370c00e1416fe72a8d519a27f1ee1a18b612fb))
* Gen300+400 telemetry archive with brotli auto-compression hook ([6b844ed](https://github.com/terrylica/rangebar-patterns/commit/6b844edf7fad926d809233639e1a942fc1fde8b7))
* Gen400 multi-feature sweep templates + archive scaffolding ([bc23123](https://github.com/terrylica/rangebar-patterns/commit/bc2312363c4de665fe1c56c0de45132a26c0d839))
* Gen500-520 overnight sweep pipeline (cross-asset + barrier grid + multi-threshold) ([745740e](https://github.com/terrylica/rangebar-patterns/commit/745740ef0229e7365e8a8d7a55bbcfdbc6097766))
* initial rangebar-patterns repository ([813689f](https://github.com/terrylica/rangebar-patterns/commit/813689f52ef2d15d47e76787eda87c7365d9db53))
* lenient 5-metric screening (3 tiers) for forensic re-evaluation ([4f2c975](https://github.com/terrylica/rangebar-patterns/commit/4f2c975c38a4bbf2096a04317d4850a108b938ea))
* local ClickHouse + SSH tunnel + rolling 1000-bar p95 ([9079e0e](https://github.com/terrylica/rangebar-patterns/commit/9079e0ea1e79c5a31a2f5a6a7cf9d736f5743197))
* relocate eval framework to permanent package + centralize research params in mise ([7d6a3e0](https://github.com/terrylica/rangebar-patterns/commit/7d6a3e03d5de74dc5adf2b8c714162c9509a6186)), closes [#12](https://github.com/terrylica/rangebar-patterns/issues/12)
* sanitize repo for public visibility — remove hardcoded hostnames and secrets ([81e3fce](https://github.com/terrylica/rangebar-patterns/commit/81e3fce00063edf2f84bbc02940824bc3da4811a))

# Changelog

All notable changes to this project will be documented in this file.
