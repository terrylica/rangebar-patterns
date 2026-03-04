# [2.2.0](https://github.com/terrylica/rangebar-patterns/compare/v2.1.0...v2.2.0) (2026-03-04)


### Features

* add results/published/ hierarchy for presentation-ready artifacts ([3443bd9](https://github.com/terrylica/rangebar-patterns/commit/3443bd96fef7884d33a0c7a01c97b8aa7e2ef829)), closes [#1](https://github.com/terrylica/rangebar-patterns/issues/1)
* Cloudflare Workers static hosting for published equity charts ([bc38c64](https://github.com/terrylica/rangebar-patterns/commit/bc38c645b0c639ce79305be6fe3c0b79401aed11))
* **eval:** add trade-level stagnation metrics to walk_forward evaluation ([f66c003](https://github.com/terrylica/rangebar-patterns/commit/f66c0031bf2bb5ecd85846235fa0218748347af7)), closes [#40](https://github.com/terrylica/rangebar-patterns/issues/40) [#41](https://github.com/terrylica/rangebar-patterns/issues/41)
* **gen800:** add Binance USDM taker fee (5 bps/side) to backtesting ([68e3f69](https://github.com/terrylica/rangebar-patterns/commit/68e3f69b627741487f1153a0162241a364187de0))
* **gen800:** add infrastructure — mise tasks, Laguerre dependency, LFS tracking ([5d94acd](https://github.com/terrylica/rangebar-patterns/commit/5d94acd254fa5ac4d689e70ad64db80fabe7de83)), closes [#40](https://github.com/terrylica/rangebar-patterns/issues/40)
* **gen800:** add Laguerre RSI wrapper and barrier simulator modules ([976944a](https://github.com/terrylica/rangebar-patterns/commit/976944a02e8543df7012b14c88218080626877f8)), closes [#40](https://github.com/terrylica/rangebar-patterns/issues/40)
* **gen800:** cross-asset validation — 13 assets @ 750dbps, all profitable ([96cd093](https://github.com/terrylica/rangebar-patterns/commit/96cd093838a1a0fc289ab07ae5fa325861abf723)), closes [#40](https://github.com/terrylica/rangebar-patterns/issues/40)
* **gen800:** log scale equity, cube-root volume transform in Bokeh plots ([5026162](https://github.com/terrylica/rangebar-patterns/commit/50261626cebf411e008ec3cdb1e06fde46b6e6e2))
* **gen800:** re-run SOL baseline configs with futures margin (100x) ([4b928de](https://github.com/terrylica/rangebar-patterns/commit/4b928de40b118b57ffcf7b2e91a9ee05a22f59aa)), closes [#1](https://github.com/terrylica/rangebar-patterns/issues/1) [#40](https://github.com/terrylica/rangebar-patterns/issues/40)
* **gen800:** reconstruct script with RangeIndex plotting (AP-20 fix) ([4543faf](https://github.com/terrylica/rangebar-patterns/commit/4543fafe4cb7782d6d6cb18b286969c05b1dd346)), closes [#42](https://github.com/terrylica/rangebar-patterns/issues/42) [#40](https://github.com/terrylica/rangebar-patterns/issues/40)
* **gen800:** rolling 90-day return/drawdown ratio cross-asset ranking ([9543142](https://github.com/terrylica/rangebar-patterns/commit/954314206cd1f739b05def0658a79e455be385fb)), closes [#1](https://github.com/terrylica/rangebar-patterns/issues/1) [#2](https://github.com/terrylica/rangebar-patterns/issues/2) [#3](https://github.com/terrylica/rangebar-patterns/issues/3) [#40](https://github.com/terrylica/rangebar-patterns/issues/40)
* **gen800:** sweep + rank scripts with bar-level stagnation (AP-18 fix) ([583ee1b](https://github.com/terrylica/rangebar-patterns/commit/583ee1bb0f6acd54e5c1022e27838efdcba83229)), closes [#41](https://github.com/terrylica/rangebar-patterns/issues/41) [#40](https://github.com/terrylica/rangebar-patterns/issues/40)
* **gen800:** sweep results — 86,400 configs, bar-level stagnation ranking ([405f89b](https://github.com/terrylica/rangebar-patterns/commit/405f89bfb4851af8f7e994284ce86e0ef807daa5)), closes [#40](https://github.com/terrylica/rangebar-patterns/issues/40)

# [2.1.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v2.0.0...v2.1.0) (2026-02-18)


### Features

* **eval:** Gen720 MCDM ranking experiments — 5 methods + cross-round comparison ([aace940](https://github.com/terrylica/opendeviationbar-patterns/commit/aace940340e4f3a68d79e6ec3e68021999cae98e)), closes [#37](https://github.com/terrylica/opendeviationbar-patterns/issues/37)

# [2.0.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.10.0...v2.0.0) (2026-02-18)


### Bug Fixes

* correct GT-composite DSR calibration and normalize Stage 3 telemetry ([12a2cfe](https://github.com/terrylica/opendeviationbar-patterns/commit/12a2cfe5cd0e7c00451418602e039b3dae507735))
* direction-prefix error stub and parent subprocess reader paths ([d9eb5fd](https://github.com/terrylica/opendeviationbar-patterns/commit/d9eb5fdd0d13e316f0ee41989b825dd73dca5c66))
* direction-prefix telemetry filenames to prevent cross-contamination ([679f35b](https://github.com/terrylica/opendeviationbar-patterns/commit/679f35ba6a6f3cf61c231c8819abbfc1127f8ff6))
* **eval:** comprehensive Gen720 audit — PF cap, Rachev cap, Vorob'ev diagnostics, provenance ([7efd561](https://github.com/terrylica/opendeviationbar-patterns/commit/7efd561c362edf1d726330e93756199b33429e0b))
* **eval:** gate build_wfo_folds for insufficient signals ([13e731d](https://github.com/terrylica/opendeviationbar-patterns/commit/13e731df0e1e15354488e5a68be6bf7b788ad256))
* Gen720 production results — direction-split artifacts, aggregate-only robustness ([6240a7b](https://github.com/terrylica/opendeviationbar-patterns/commit/6240a7b9b22f4f0abf74340788336538a18678b5))


### Code Refactoring

* **barriers:** align threshold units with rangebar-py (÷100,000) ([24ea724](https://github.com/terrylica/opendeviationbar-patterns/commit/24ea724935912584cbef46ce79d56b8a3a53cf69))


### Features

* **eval:** cross-asset Pareto ranking + Kelly removal + MCDM research archival ([4a37472](https://github.com/terrylica/opendeviationbar-patterns/commit/4a3747251caff9532b37b21616c1d5560e433587)), closes [16/#17](https://github.com/terrylica/opendeviationbar-patterns/issues/17) [#28](https://github.com/terrylica/opendeviationbar-patterns/issues/28)
* **eval:** integrate NumPy TOPSIS into Pareto ranking pipeline ([c16cb2d](https://github.com/terrylica/opendeviationbar-patterns/commit/c16cb2da6929d2e0d2d93d935957f4bcb5ba3823)), closes [#28](https://github.com/terrylica/opendeviationbar-patterns/issues/28)
* **eval:** MCDM benchmark POC — NumPy TOPSIS 36x faster, pymcdm uses non-standard normalization ([9acae06](https://github.com/terrylica/opendeviationbar-patterns/commit/9acae066ce4ec62500c6c96fd486d75764322061)), closes [#28](https://github.com/terrylica/opendeviationbar-patterns/issues/28)
* **eval:** retrospective TOPSIS re-ranking of 75 Pareto solutions ([5fbd8dd](https://github.com/terrylica/opendeviationbar-patterns/commit/5fbd8dd322932bee6822fa0a4365e1afd40261d7)), closes [#28](https://github.com/terrylica/opendeviationbar-patterns/issues/28)
* Gen720 walk-forward barrier optimization with subprocess isolation ([76ea346](https://github.com/terrylica/opendeviationbar-patterns/commit/76ea34672e71eae592c75018498adc24433d38b8)), closes [#28](https://github.com/terrylica/opendeviationbar-patterns/issues/28)
* Gen720-L WFO results — 77.5% cross-asset positive OOS, 12 knee points ([b40da2f](https://github.com/terrylica/opendeviationbar-patterns/commit/b40da2f2e4d173b2b8bf2d8809a7b9e2f65811bc)), closes [#28](https://github.com/terrylica/opendeviationbar-patterns/issues/28)
* Gen720-S SHORT WFO results — 93.1% cross-asset positive OOS, Strategy B dominant ([912449c](https://github.com/terrylica/opendeviationbar-patterns/commit/912449c6a6ac4aaac0e6a429bf7992db0f3d1396)), closes [#28](https://github.com/terrylica/opendeviationbar-patterns/issues/28)
* wire 4-stage WFO pipeline (CPCV + bootstrap + GT-composite) into Gen720 ([fa42051](https://github.com/terrylica/opendeviationbar-patterns/commit/fa420517b24e351aeee6ec6624e8dc737fb78560))


### BREAKING CHANGES

* **barriers:** threshold_pct removed, use bar_range instead.
Barrier multipliers are now in bar-width units (2.5 = 2.5 bar-widths).

SRED-Type: support-work
SRED-Claim: RANGEBAR-PATTERNS

# [1.10.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.9.0...v1.10.0) (2026-02-15)


### Features

* Gen710 time-decay SL sweep — 48/48 positive Kelly, best +0.410 (8x baseline) ([f0d4976](https://github.com/terrylica/opendeviationbar-patterns/commit/f0d4976b5b65c34112c61d30b07b8a0abe5c528d))

# [1.9.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.8.0...v1.9.0) (2026-02-15)


### Features

* champion oracle validation — ALL 5 GATES PASS, SQN=3.44, WR=78.8% (Issue [#26](https://github.com/terrylica/opendeviationbar-patterns/issues/26)) ([918d8a8](https://github.com/terrylica/opendeviationbar-patterns/commit/918d8a8c99c31aaf27fbee68aa0ca9525bd1bb8d)), closes [#27](https://github.com/terrylica/opendeviationbar-patterns/issues/27)

# [1.8.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.7.0...v1.8.0) (2026-02-14)


### Features

* 10K-trial optimization results — 5 objectives, universal champion identified ([a6f7b9d](https://github.com/terrylica/opendeviationbar-patterns/commit/a6f7b9d0e3c8d4138875cc0b5bb2cb682e59dd24))
* add per-metric percentile ranking system with Optuna cutoff optimizer (Issue [#17](https://github.com/terrylica/opendeviationbar-patterns/issues/17)) ([0c6d53f](https://github.com/terrylica/opendeviationbar-patterns/commit/0c6d53f64ef8a62bc9e8f108fe4c8b2d0afbc66c))
* add signal regularity gate, remove Kelly from screening (Issue [#17](https://github.com/terrylica/opendeviationbar-patterns/issues/17)) ([4ee7980](https://github.com/terrylica/opendeviationbar-patterns/commit/4ee798068b3fcb30b106d9af681994c5048b547e))
* rolling 1000-bar OU calibration per signal — Option A (Issue [#16](https://github.com/terrylica/opendeviationbar-patterns/issues/16)) ([1847d33](https://github.com/terrylica/opendeviationbar-patterns/commit/1847d33b1432e892297bc3d946eb124e55c4aad6))
* TAMRS evaluation stack — Rachev, CDaR, OU barriers, screening integration (Issue [#16](https://github.com/terrylica/opendeviationbar-patterns/issues/16)) ([181af9d](https://github.com/terrylica/opendeviationbar-patterns/commit/181af9ddfe136f58b075e92cfbdc6d95a4d61e40))

# [1.7.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.6.0...v1.7.0) (2026-02-13)


### Features

* add Gemini 3 Pro tail-risk evaluation findings — Rachev, CDaR, OU barriers, TAMRS ([e43fdf7](https://github.com/terrylica/opendeviationbar-patterns/commit/e43fdf70c2f49e00fa733f1736ad218f05ffac92)), closes [#15](https://github.com/terrylica/opendeviationbar-patterns/issues/15) [#16](https://github.com/terrylica/opendeviationbar-patterns/issues/16)
* Gen610 barrier grid sweep results — 65 configs positive on all 10 combos ([a2fed32](https://github.com/terrylica/opendeviationbar-patterns/commit/a2fed32907de62728d8165eeeff00919cddb40f0))

# [1.6.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.5.0...v1.6.0) (2026-02-13)


### Features

* Gen600 cross-asset consistency analysis + exhaustion oracle validation ([2e7029f](https://github.com/terrylica/opendeviationbar-patterns/commit/2e7029fd78e159f18beb3be438430eb8558850c9))
* Gen610 barrier grid optimization + backtesting.py cross-asset validation ([4f8ebfe](https://github.com/terrylica/opendeviationbar-patterns/commit/4f8ebfee490223f77384be842ed34991a532baf6))

# [1.5.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.4.0...v1.5.0) (2026-02-13)


### Bug Fixes

* AP-15 signal timing alignment — reduce all lags by 1 to match backtesting.py ([a1ba117](https://github.com/terrylica/opendeviationbar-patterns/commit/a1ba1174128cc78ad1c0dbbf5a7fb2a2ce7d6747))


### Features

* add AP-15 SQL vs Python oracle verification scripts ([36efe46](https://github.com/terrylica/opendeviationbar-patterns/commit/36efe4635e1d7a1f24c9410008e4d839d0591113))
* add backtesting-py-oracle skill for SQL/Python alignment ([053c00c](https://github.com/terrylica/opendeviationbar-patterns/commit/053c00ca90058003f7148311084815fe95824ddc))
* Gen600 oracle validation — SQL vs backtesting.py trade-by-trade match ([a535502](https://github.com/terrylica/opendeviationbar-patterns/commit/a535502abd33e4d51d4749139130cc5050868d37))
* Gen600 sweep results — 300K configs, 1.3M lines, 13K Bonferroni survivors ([2fc2d21](https://github.com/terrylica/opendeviationbar-patterns/commit/2fc2d2155f70d3653a2c0bc7d4e22de7fce33a65))

# [1.4.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.3.0...v1.4.0) (2026-02-12)


### Features

* add AP-14 self-join forward arrays anti-pattern (11x speedup discovery) ([44c81e7](https://github.com/terrylica/opendeviationbar-patterns/commit/44c81e76465b892ba3b4e8021ddf2cf365457316))


### Performance Improvements

* apply AP-14 window-based forward arrays to all 22 Gen600 templates ([5c99f63](https://github.com/terrylica/opendeviationbar-patterns/commit/5c99f631918568cd2369f0fc7064e20a7d849427))

# [1.3.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.2.0...v1.3.0) (2026-02-11)


### Features

* Gen600 hybrid feature sweep — 22 SQL templates (11 LONG + 11 SHORT) ([db29a5e](https://github.com/terrylica/opendeviationbar-patterns/commit/db29a5eafaa65fc214b583e09e9ba18331bd2fcb)), closes [#14](https://github.com/terrylica/opendeviationbar-patterns/issues/14)
* Gen600 infrastructure — generate/submit/collect pipeline for 301K configs ([0d075e0](https://github.com/terrylica/opendeviationbar-patterns/commit/0d075e0139100e53be282737b18769ac9d112785)), closes [#14](https://github.com/terrylica/opendeviationbar-patterns/issues/14)

# [1.2.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.1.0...v1.2.0) (2026-02-11)


### Features

* add sweep-methodology skill — invariant-based guidelines for brute-force pattern discovery ([d20e6a7](https://github.com/terrylica/opendeviationbar-patterns/commit/d20e6a7331ae9ad1963e1588e1e296fe9c46bd08))

# [1.1.0](https://github.com/terrylica/opendeviationbar-patterns/compare/v1.0.0...v1.1.0) (2026-02-11)


### Features

* atomic trade reconstruction — bar-by-bar inspection of ClickHouse configs ([#13](https://github.com/terrylica/opendeviationbar-patterns/issues/13)) ([be87872](https://github.com/terrylica/opendeviationbar-patterns/commit/be87872ece0860c2672ec948adb4ab63f90bad43)), closes [hi#performing](https://github.com/hi/issues/performing)

# 1.0.0 (2026-02-08)


### Bug Fixes

* add repo root to sys.path in backtesting tests ([1f3fda6](https://github.com/terrylica/opendeviationbar-patterns/commit/1f3fda62ea6c645217e5083ddbff4bfb8dc5eb2d))
* correct DSR var_sr bug (unit variance) + NaN Kelly correlation filter ([f4d4c22](https://github.com/terrylica/opendeviationbar-patterns/commit/f4d4c22c931340dc6667d9ab5ff1df4297bced4b)), closes [#12](https://github.com/terrylica/opendeviationbar-patterns/issues/12)
* **gen300:** rolling 1000-bar window, barrier grid, AP-10 rewrite ([b6d84af](https://github.com/terrylica/opendeviationbar-patterns/commit/b6d84af0883ac32c733c18dcaa17b18a86189661)), closes [#10](https://github.com/terrylica/opendeviationbar-patterns/issues/10)


### Features

* add ClickHouse anti-pattern skill (13 SQL + 3 infra constraints) ([609c3be](https://github.com/terrylica/opendeviationbar-patterns/commit/609c3beaefd8e72652e5d4e64fd7ad32d4395e08)), closes [#8](https://github.com/terrylica/opendeviationbar-patterns/issues/8)
* atomic validation + backtesting.py barrier alignment ([c85d2c3](https://github.com/terrylica/opendeviationbar-patterns/commit/c85d2c311aa10088b7723a922bc7bc4a8aa78c8e)), closes [#6](https://github.com/terrylica/opendeviationbar-patterns/issues/6) [#7](https://github.com/terrylica/opendeviationbar-patterns/issues/7)
* beyond-Kelly 9-agent POC — 6-metric stack recommendation ([cd6ecc0](https://github.com/terrylica/opendeviationbar-patterns/commit/cd6ecc0a09a9c85c0d62b9d32f98a5d920500d09)), closes [#12](https://github.com/terrylica/opendeviationbar-patterns/issues/12)
* collect Gen500-520 overnight sweep results (15,300 configs) ([d73254b](https://github.com/terrylica/opendeviationbar-patterns/commit/d73254b72c006bd808e190a803b897b60380fadf))
* Gen200-202 triple barrier + trailing stop SQL framework ([d7979f9](https://github.com/terrylica/opendeviationbar-patterns/commit/d7979f99a6dad4c2920779d6851d21fdf37c8704)), closes [#3](https://github.com/terrylica/opendeviationbar-patterns/issues/3) [#4](https://github.com/terrylica/opendeviationbar-patterns/issues/4) [#5](https://github.com/terrylica/opendeviationbar-patterns/issues/5)
* Gen300 feature filter sweep — 4 positive-Kelly configs found ([64370c0](https://github.com/terrylica/opendeviationbar-patterns/commit/64370c00e1416fe72a8d519a27f1ee1a18b612fb))
* Gen300+400 telemetry archive with brotli auto-compression hook ([6b844ed](https://github.com/terrylica/opendeviationbar-patterns/commit/6b844edf7fad926d809233639e1a942fc1fde8b7))
* Gen400 multi-feature sweep templates + archive scaffolding ([bc23123](https://github.com/terrylica/opendeviationbar-patterns/commit/bc2312363c4de665fe1c56c0de45132a26c0d839))
* Gen500-520 overnight sweep pipeline (cross-asset + barrier grid + multi-threshold) ([745740e](https://github.com/terrylica/opendeviationbar-patterns/commit/745740ef0229e7365e8a8d7a55bbcfdbc6097766))
* initial opendeviationbar-patterns repository ([813689f](https://github.com/terrylica/opendeviationbar-patterns/commit/813689f52ef2d15d47e76787eda87c7365d9db53))
* lenient 5-metric screening (3 tiers) for forensic re-evaluation ([4f2c975](https://github.com/terrylica/opendeviationbar-patterns/commit/4f2c975c38a4bbf2096a04317d4850a108b938ea))
* local ClickHouse + SSH tunnel + rolling 1000-bar p95 ([9079e0e](https://github.com/terrylica/opendeviationbar-patterns/commit/9079e0ea1e79c5a31a2f5a6a7cf9d736f5743197))
* relocate eval framework to permanent package + centralize research params in mise ([7d6a3e0](https://github.com/terrylica/opendeviationbar-patterns/commit/7d6a3e03d5de74dc5adf2b8c714162c9509a6186)), closes [#12](https://github.com/terrylica/opendeviationbar-patterns/issues/12)
* sanitize repo for public visibility — remove hardcoded hostnames and secrets ([81e3fce](https://github.com/terrylica/opendeviationbar-patterns/commit/81e3fce00063edf2f84bbc02940824bc3da4811a))

# Changelog

All notable changes to this project will be documented in this file.
