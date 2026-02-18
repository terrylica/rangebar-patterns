# Gen800 Cross-Asset Rolling 120-Day Return/Drawdown Ranking

Window: 120 calendar days, sliding by 1 day
Min trades per window: 5
Ratio cap: 50.0

## Asset Rankings (TOPSIS: 35% median + 30% p10 + 20% frac>2 + 15% frac<1)

| Rank | Asset | TOPSIS | Median | P10 | P90 | %>2 | %<1 | %Neg | Windows |
|------|-------|--------|--------|-----|-----|-----|-----|------|---------|
| 1 | XRPUSDT_750 | 0.992 | 2.15 | -0.25 | 9.53 | 52.3% | 29.5% | 14.4% | 1998 |
| 2 | SOLUSDT_750 | 0.792 | 1.67 | -0.32 | 15.33 | 47.3% | 40.1% | 15.2% | 1849 |
| 3 | ETHUSDT_750 | 0.780 | 1.87 | -0.50 | 8.46 | 48.4% | 36.1% | 21.2% | 1632 |
| 4 | BTCUSDT_750 | 0.669 | 1.44 | -0.44 | 8.36 | 43.3% | 40.1% | 21.4% | 1334 |
| 5 | LINKUSDT_750 | 0.633 | 1.21 | -0.24 | 6.21 | 37.2% | 46.8% | 14.6% | 2058 |
| 6 | DOGEUSDT_750 | 0.627 | 1.18 | -0.27 | 9.76 | 42.8% | 48.6% | 17.4% | 2039 |
| 7 | NEARUSDT_750 | 0.463 | 1.02 | -0.57 | 5.87 | 33.2% | 49.8% | 27.7% | 1782 |
| 8 | DOTUSDT_750 | 0.417 | 0.81 | -0.55 | 7.60 | 37.6% | 52.6% | 29.5% | 1838 |
| 9 | BNBUSDT_750 | 0.399 | 1.15 | -0.96 | 6.80 | 42.2% | 47.9% | 30.5% | 1911 |
| 10 | ADAUSDT_750 | 0.220 | 0.38 | -0.69 | 12.91 | 26.9% | 61.5% | 35.5% | 2057 |
| 11 | AVAXUSDT_750 | 0.197 | 0.37 | -0.70 | 3.00 | 19.5% | 67.3% | 37.7% | 1795 |
| 12 | ATOMUSDT_750 | 0.174 | 0.21 | -0.69 | 3.13 | 15.1% | 76.4% | 37.0% | 2067 |
| 13 | LTCUSDT_750 | 0.170 | 0.27 | -0.78 | 6.77 | 30.3% | 61.5% | 42.6% | 2067 |

## Per-Asset Detail

### #1 XRPUSDT_750

- **Trades**: 168005 across 1998 windows
- **Ratio distribution**: min=-1.24, p10=-0.25, median=2.15, p90=9.53, max=27.18
- **Consistency**: CV=1.4676
- **Best window**: 2021-04-09 (ratio=27.18)
- **Worst window**: 2022-11-14 (ratio=-1.24)

### #2 SOLUSDT_750

- **Trades**: 199421 across 1849 windows
- **Ratio distribution**: min=-0.93, p10=-0.32, median=1.67, p90=15.33, max=50.00
- **Consistency**: CV=1.8927
- **Best window**: 2025-04-05 (ratio=50.00)
- **Worst window**: 2022-02-28 (ratio=-0.93)

### #3 ETHUSDT_750

- **Trades**: 60806 across 1632 windows
- **Ratio distribution**: min=-1.87, p10=-0.50, median=1.87, p90=8.46, max=50.00
- **Consistency**: CV=2.127
- **Best window**: 2023-02-06 (ratio=50.00)
- **Worst window**: 2025-02-06 (ratio=-1.87)

### #4 BTCUSDT_750

- **Trades**: 43954 across 1334 windows
- **Ratio distribution**: min=-2.36, p10=-0.44, median=1.44, p90=8.36, max=50.00
- **Consistency**: CV=1.7051
- **Best window**: 2020-07-26 (ratio=50.00)
- **Worst window**: 2022-06-07 (ratio=-2.36)

### #5 LINKUSDT_750

- **Trades**: 147763 across 2058 windows
- **Ratio distribution**: min=-1.26, p10=-0.24, median=1.21, p90=6.21, max=10.46
- **Consistency**: CV=1.1928
- **Best window**: 2021-01-19 (ratio=10.46)
- **Worst window**: 2023-06-23 (ratio=-1.26)

### #6 DOGEUSDT_750

- **Trades**: 750793 across 2039 windows
- **Ratio distribution**: min=-1.34, p10=-0.27, median=1.18, p90=9.76, max=50.00
- **Consistency**: CV=2.1503
- **Best window**: 2020-10-28 (ratio=50.00)
- **Worst window**: 2025-04-16 (ratio=-1.34)

### #7 NEARUSDT_750

- **Trades**: 209222 across 1782 windows
- **Ratio distribution**: min=-1.21, p10=-0.57, median=1.02, p90=5.87, max=8.75
- **Consistency**: CV=1.3641
- **Best window**: 2021-05-13 (ratio=8.75)
- **Worst window**: 2024-03-24 (ratio=-1.21)

### #8 DOTUSDT_750

- **Trades**: 153188 across 1838 windows
- **Ratio distribution**: min=-1.43, p10=-0.55, median=0.81, p90=7.60, max=11.03
- **Consistency**: CV=1.4149
- **Best window**: 2023-11-06 (ratio=11.03)
- **Worst window**: 2023-03-14 (ratio=-1.43)

### #9 BNBUSDT_750

- **Trades**: 83045 across 1911 windows
- **Ratio distribution**: min=-1.21, p10=-0.96, median=1.15, p90=6.80, max=50.00
- **Consistency**: CV=2.4618
- **Best window**: 2023-01-22 (ratio=50.00)
- **Worst window**: 2024-05-20 (ratio=-1.21)

### #10 ADAUSDT_750

- **Trades**: 160415 across 2057 windows
- **Ratio distribution**: min=-1.17, p10=-0.69, median=0.38, p90=12.91, max=34.68
- **Consistency**: CV=2.3267
- **Best window**: 2021-02-07 (ratio=34.68)
- **Worst window**: 2022-06-14 (ratio=-1.17)

### #11 AVAXUSDT_750

- **Trades**: 218345 across 1795 windows
- **Ratio distribution**: min=-1.30, p10=-0.70, median=0.37, p90=3.00, max=8.77
- **Consistency**: CV=1.9856
- **Best window**: 2021-03-08 (ratio=8.77)
- **Worst window**: 2023-01-30 (ratio=-1.30)

### #12 ATOMUSDT_750

- **Trades**: 207293 across 2067 windows
- **Ratio distribution**: min=-1.25, p10=-0.69, median=0.21, p90=3.13, max=10.27
- **Consistency**: CV=2.4851
- **Best window**: 2021-02-13 (ratio=10.27)
- **Worst window**: 2023-06-10 (ratio=-1.25)

### #13 LTCUSDT_750

- **Trades**: 100465 across 2067 windows
- **Ratio distribution**: min=-1.46, p10=-0.78, median=0.27, p90=6.77, max=50.00
- **Consistency**: CV=2.8188
- **Best window**: 2025-04-23 (ratio=50.00)
- **Worst window**: 2023-04-15 (ratio=-1.46)
