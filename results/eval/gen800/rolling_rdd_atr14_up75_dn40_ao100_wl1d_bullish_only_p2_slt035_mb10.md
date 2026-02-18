# Gen800 Cross-Asset Rolling 90-Day Return/Drawdown Ranking

Window: 90 calendar days, sliding by 1 day
Min trades per window: 5
Ratio cap: 50.0

## Asset Rankings (TOPSIS: 35% median + 30% p10 + 20% frac>2 + 15% frac<1)

| Rank | Asset | TOPSIS | Median | P10 | P90 | %>2 | %<1 | %Neg | Windows |
|------|-------|--------|--------|-----|-----|-----|-----|------|---------|
| 1 | SOLUSDT_750 | 0.945 | 1.96 | -0.51 | 12.12 | 49.5% | 38.0% | 24.7% | 1865 |
| 2 | LINKUSDT_750 | 0.712 | 1.36 | -0.42 | 4.90 | 39.7% | 43.8% | 17.9% | 2084 |
| 3 | BTCUSDT_750 | 0.549 | 1.06 | -0.60 | 10.43 | 42.3% | 47.5% | 25.1% | 1211 |
| 4 | BNBUSDT_750 | 0.432 | 0.94 | -0.83 | 8.42 | 41.4% | 51.2% | 31.3% | 1845 |
| 5 | ADAUSDT_750 | 0.372 | 0.60 | -0.57 | 5.72 | 28.3% | 57.4% | 25.9% | 2095 |
| 6 | DOGEUSDT_750 | 0.317 | 0.47 | -0.62 | 5.91 | 29.9% | 60.4% | 34.9% | 2096 |
| 7 | ETHUSDT_750 | 0.069 | 0.17 | -1.12 | 7.10 | 37.6% | 59.1% | 30.6% | 372 |

## Per-Asset Detail

### #1 SOLUSDT_750

- **Trades**: 170066 across 1865 windows
- **Ratio distribution**: min=-1.03, p10=-0.51, median=1.96, p90=12.12, max=50.00
- **Consistency**: CV=2.019
- **Best window**: 2025-04-05 (ratio=50.00)
- **Worst window**: 2023-06-30 (ratio=-1.03)

### #2 LINKUSDT_750

- **Trades**: 130080 across 2084 windows
- **Ratio distribution**: min=-1.29, p10=-0.42, median=1.36, p90=4.90, max=13.11
- **Consistency**: CV=1.2021
- **Best window**: 2025-05-11 (ratio=13.11)
- **Worst window**: 2024-08-14 (ratio=-1.29)

### #3 BTCUSDT_750

- **Trades**: 36197 across 1211 windows
- **Ratio distribution**: min=-3.22, p10=-0.60, median=1.06, p90=10.43, max=50.00
- **Consistency**: CV=2.1732
- **Best window**: 2023-11-14 (ratio=50.00)
- **Worst window**: 2022-06-24 (ratio=-3.22)

### #4 BNBUSDT_750

- **Trades**: 70717 across 1845 windows
- **Ratio distribution**: min=-1.63, p10=-0.83, median=0.94, p90=8.42, max=50.00
- **Consistency**: CV=2.4967
- **Best window**: 2023-05-04 (ratio=50.00)
- **Worst window**: 2020-06-03 (ratio=-1.63)

### #5 ADAUSDT_750

- **Trades**: 137165 across 2095 windows
- **Ratio distribution**: min=-1.35, p10=-0.57, median=0.60, p90=5.72, max=19.92
- **Consistency**: CV=1.956
- **Best window**: 2021-04-04 (ratio=19.92)
- **Worst window**: 2022-09-13 (ratio=-1.35)

### #6 DOGEUSDT_750

- **Trades**: 605871 across 2096 windows
- **Ratio distribution**: min=-1.15, p10=-0.62, median=0.47, p90=5.91, max=44.78
- **Consistency**: CV=2.7239
- **Best window**: 2020-12-02 (ratio=44.78)
- **Worst window**: 2022-12-05 (ratio=-1.15)

### #7 ETHUSDT_750

- **Trades**: 17762 across 372 windows
- **Ratio distribution**: min=-1.15, p10=-1.12, median=0.17, p90=7.10, max=7.77
- **Consistency**: CV=1.5235
- **Best window**: 2020-01-16 (ratio=7.77)
- **Worst window**: 2020-09-14 (ratio=-1.15)
