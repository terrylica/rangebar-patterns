# Gen800 Cross-Asset Rolling 90-Day Return/Drawdown Ranking

Window: 90 calendar days, sliding by 1 day
Min trades per window: 5
Ratio cap: 50.0

## Asset Rankings (TOPSIS: 35% median + 30% p10 + 20% frac>2 + 15% frac<1)

| Rank | Asset | TOPSIS | Median | P10 | P90 | %>2 | %<1 | %Neg | Windows |
|------|-------|--------|--------|-----|-----|-----|-----|------|---------|
| 1 | XRPUSDT_750 | 0.999 | 2.03 | -0.36 | 8.00 | 50.6% | 36.7% | 18.2% | 1958 |
| 2 | ETHUSDT_750 | 0.841 | 1.81 | -0.52 | 11.64 | 44.6% | 36.4% | 19.5% | 1382 |
| 3 | SOLUSDT_750 | 0.789 | 1.57 | -0.39 | 16.28 | 47.7% | 43.4% | 18.4% | 1879 |
| 4 | BTCUSDT_750 | 0.661 | 1.44 | -0.65 | 10.12 | 45.1% | 38.2% | 21.6% | 1128 |
| 5 | DOGEUSDT_750 | 0.518 | 0.98 | -0.48 | 9.49 | 39.4% | 50.6% | 21.3% | 2069 |
| 6 | LINKUSDT_750 | 0.513 | 0.94 | -0.41 | 5.68 | 34.9% | 51.2% | 20.6% | 2088 |
| 7 | BNBUSDT_750 | 0.462 | 1.15 | -0.95 | 6.82 | 41.8% | 49.4% | 32.0% | 1830 |
| 8 | DOTUSDT_750 | 0.399 | 0.77 | -0.58 | 6.12 | 33.5% | 51.8% | 32.1% | 1868 |
| 9 | NEARUSDT_750 | 0.384 | 0.78 | -0.61 | 4.84 | 30.9% | 54.4% | 28.1% | 1812 |
| 10 | ADAUSDT_750 | 0.214 | 0.34 | -0.68 | 10.61 | 26.3% | 63.8% | 38.9% | 2086 |
| 11 | ATOMUSDT_750 | 0.181 | 0.18 | -0.66 | 3.48 | 13.6% | 71.8% | 37.1% | 2071 |
| 12 | LTCUSDT_750 | 0.162 | 0.27 | -0.80 | 6.31 | 29.3% | 62.6% | 44.0% | 2087 |
| 13 | AVAXUSDT_750 | 0.139 | 0.25 | -0.76 | 3.22 | 19.4% | 67.3% | 42.7% | 1825 |

## Per-Asset Detail

### #1 XRPUSDT_750

- **Trades**: 129734 across 1958 windows
- **Ratio distribution**: min=-1.24, p10=-0.36, median=2.03, p90=8.00, max=50.00
- **Consistency**: CV=1.9692
- **Best window**: 2020-08-02 (ratio=50.00)
- **Worst window**: 2022-11-14 (ratio=-1.24)

### #2 ETHUSDT_750

- **Trades**: 48814 across 1382 windows
- **Ratio distribution**: min=-1.20, p10=-0.52, median=1.81, p90=11.64, max=50.00
- **Consistency**: CV=2.0292
- **Best window**: 2023-02-06 (ratio=50.00)
- **Worst window**: 2022-05-13 (ratio=-1.20)

### #3 SOLUSDT_750

- **Trades**: 154007 across 1879 windows
- **Ratio distribution**: min=-1.02, p10=-0.39, median=1.57, p90=16.28, max=50.00
- **Consistency**: CV=2.0472
- **Best window**: 2025-04-05 (ratio=50.00)
- **Worst window**: 2022-03-30 (ratio=-1.02)

### #4 BTCUSDT_750

- **Trades**: 35093 across 1128 windows
- **Ratio distribution**: min=-1.12, p10=-0.65, median=1.44, p90=10.12, max=50.00
- **Consistency**: CV=1.8189
- **Best window**: 2020-07-26 (ratio=50.00)
- **Worst window**: 2021-05-26 (ratio=-1.12)

### #5 DOGEUSDT_750

- **Trades**: 569732 across 2069 windows
- **Ratio distribution**: min=-1.13, p10=-0.48, median=0.98, p90=9.49, max=49.41
- **Consistency**: CV=2.317
- **Best window**: 2020-11-28 (ratio=49.41)
- **Worst window**: 2022-02-08 (ratio=-1.13)

### #6 LINKUSDT_750

- **Trades**: 119573 across 2088 windows
- **Ratio distribution**: min=-1.33, p10=-0.41, median=0.94, p90=5.68, max=11.28
- **Consistency**: CV=1.2968
- **Best window**: 2022-06-23 (ratio=11.28)
- **Worst window**: 2023-06-13 (ratio=-1.33)

### #7 BNBUSDT_750

- **Trades**: 66672 across 1830 windows
- **Ratio distribution**: min=-1.75, p10=-0.95, median=1.15, p90=6.82, max=50.00
- **Consistency**: CV=2.5177
- **Best window**: 2023-01-22 (ratio=50.00)
- **Worst window**: 2020-06-06 (ratio=-1.75)

### #8 DOTUSDT_750

- **Trades**: 124341 across 1868 windows
- **Ratio distribution**: min=-1.46, p10=-0.58, median=0.77, p90=6.12, max=12.27
- **Consistency**: CV=1.516
- **Best window**: 2023-06-23 (ratio=12.27)
- **Worst window**: 2023-03-14 (ratio=-1.46)

### #9 NEARUSDT_750

- **Trades**: 162346 across 1812 windows
- **Ratio distribution**: min=-1.40, p10=-0.61, median=0.78, p90=4.84, max=12.63
- **Consistency**: CV=1.4423
- **Best window**: 2021-02-20 (ratio=12.63)
- **Worst window**: 2024-04-20 (ratio=-1.40)

### #10 ADAUSDT_750

- **Trades**: 127709 across 2086 windows
- **Ratio distribution**: min=-1.32, p10=-0.68, median=0.34, p90=10.61, max=31.95
- **Consistency**: CV=2.2809
- **Best window**: 2021-02-28 (ratio=31.95)
- **Worst window**: 2022-06-14 (ratio=-1.32)

### #11 ATOMUSDT_750

- **Trades**: 166169 across 2071 windows
- **Ratio distribution**: min=-1.61, p10=-0.66, median=0.18, p90=3.48, max=10.47
- **Consistency**: CV=2.3631
- **Best window**: 2021-02-21 (ratio=10.47)
- **Worst window**: 2023-06-10 (ratio=-1.61)

### #12 LTCUSDT_750

- **Trades**: 79209 across 2087 windows
- **Ratio distribution**: min=-1.84, p10=-0.80, median=0.27, p90=6.31, max=50.00
- **Consistency**: CV=2.8944
- **Best window**: 2025-04-28 (ratio=50.00)
- **Worst window**: 2025-04-08 (ratio=-1.84)

### #13 AVAXUSDT_750

- **Trades**: 170230 across 1825 windows
- **Ratio distribution**: min=-1.29, p10=-0.76, median=0.25, p90=3.22, max=18.88
- **Consistency**: CV=2.2846
- **Best window**: 2021-03-04 (ratio=18.88)
- **Worst window**: 2024-05-03 (ratio=-1.29)
