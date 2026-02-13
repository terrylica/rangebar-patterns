# [1.7.0](https://github.com/terrylica/rangebar-patterns/compare/v1.6.0...v1.7.0) (2026-02-13)


### Features

* add Gemini 3 Pro tail-risk evaluation findings — Rachev, CDaR, OU barriers, TAMRS ([e43fdf7](https://github.com/terrylica/rangebar-patterns/commit/e43fdf70c2f49e00fa733f1736ad218f05ffac92)), closes [#15](https://github.com/terrylica/rangebar-patterns/issues/15) [#16](https://github.com/terrylica/rangebar-patterns/issues/16)
* Gen610 barrier grid sweep results — 65 configs positive on all 10 combos ([a2fed32](https://github.com/terrylica/rangebar-patterns/commit/a2fed32907de62728d8165eeeff00919cddb40f0))

# [1.6.0](https://github.com/terrylica/rangebar-patterns/compare/v1.5.0...v1.6.0) (2026-02-13)


### Features

* Gen600 cross-asset consistency analysis + exhaustion oracle validation ([2e7029f](https://github.com/terrylica/rangebar-patterns/commit/2e7029fd78e159f18beb3be438430eb8558850c9))
* Gen610 barrier grid optimization + backtesting.py cross-asset validation ([4f8ebfe](https://github.com/terrylica/rangebar-patterns/commit/4f8ebfee490223f77384be842ed34991a532baf6))

# [1.5.0](https://github.com/terrylica/rangebar-patterns/compare/v1.4.0...v1.5.0) (2026-02-13)


### Bug Fixes

* AP-15 signal timing alignment — reduce all lags by 1 to match backtesting.py ([a1ba117](https://github.com/terrylica/rangebar-patterns/commit/a1ba1174128cc78ad1c0dbbf5a7fb2a2ce7d6747))


### Features

* add AP-15 SQL vs Python oracle verification scripts ([36efe46](https://github.com/terrylica/rangebar-patterns/commit/36efe4635e1d7a1f24c9410008e4d839d0591113))
* add backtesting-py-oracle skill for SQL/Python alignment ([053c00c](https://github.com/terrylica/rangebar-patterns/commit/053c00ca90058003f7148311084815fe95824ddc))
* Gen600 oracle validation — SQL vs backtesting.py trade-by-trade match ([a535502](https://github.com/terrylica/rangebar-patterns/commit/a535502abd33e4d51d4749139130cc5050868d37))
* Gen600 sweep results — 300K configs, 1.3M lines, 13K Bonferroni survivors ([2fc2d21](https://github.com/terrylica/rangebar-patterns/commit/2fc2d2155f70d3653a2c0bc7d4e22de7fce33a65))

# [1.4.0](https://github.com/terrylica/rangebar-patterns/compare/v1.3.0...v1.4.0) (2026-02-12)


### Features

* add AP-14 self-join forward arrays anti-pattern (11x speedup discovery) ([44c81e7](https://github.com/terrylica/rangebar-patterns/commit/44c81e76465b892ba3b4e8021ddf2cf365457316))


### Performance Improvements

* apply AP-14 window-based forward arrays to all 22 Gen600 templates ([5c99f63](https://github.com/terrylica/rangebar-patterns/commit/5c99f631918568cd2369f0fc7064e20a7d849427))

# [1.3.0](https://github.com/terrylica/rangebar-patterns/compare/v1.2.0...v1.3.0) (2026-02-11)


### Features

* Gen600 hybrid feature sweep — 22 SQL templates (11 LONG + 11 SHORT) ([db29a5e](https://github.com/terrylica/rangebar-patterns/commit/db29a5eafaa65fc214b583e09e9ba18331bd2fcb)), closes [#14](https://github.com/terrylica/rangebar-patterns/issues/14)
* Gen600 infrastructure — generate/submit/collect pipeline for 301K configs ([0d075e0](https://github.com/terrylica/rangebar-patterns/commit/0d075e0139100e53be282737b18769ac9d112785)), closes [#14](https://github.com/terrylica/rangebar-patterns/issues/14)

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
