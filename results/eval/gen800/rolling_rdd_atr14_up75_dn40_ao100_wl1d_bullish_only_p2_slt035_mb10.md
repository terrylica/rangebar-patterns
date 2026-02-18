# Gen800 Cross-Asset Rolling 120-Day Return/Drawdown Ranking

Window: 120 calendar days, sliding by 1 day
Min trades per window: 5
Ratio cap: 50.0

## Asset Rankings (TOPSIS: 35% median + 30% p10 + 20% frac>2 + 15% frac<1)

| Rank | Asset | TOPSIS | Median | P10 | P90 | %>2 | %<1 | %Neg | Windows |
|------|-------|--------|--------|-----|-----|-----|-----|------|---------|
| 1 | SOLUSDT_750 | 0.902 | 2.43 | -0.40 | 12.37 | 52.8% | 36.3% | 22.1% | 1849 |
| 2 | LINKUSDT_750 | 0.709 | 1.67 | -0.28 | 5.12 | 42.5% | 31.3% | 13.2% | 2054 |
| 3 | BTCUSDT_750 | 0.425 | 0.95 | -0.42 | 5.28 | 37.9% | 50.1% | 21.8% | 1498 |
| 4 | BNBUSDT_750 | 0.384 | 1.22 | -0.80 | 9.05 | 39.8% | 48.7% | 25.7% | 1894 |
| 5 | ADAUSDT_750 | 0.335 | 0.69 | -0.45 | 7.07 | 29.5% | 55.1% | 23.5% | 2065 |
| 6 | DOGEUSDT_750 | 0.261 | 0.57 | -0.54 | 6.03 | 34.7% | 56.8% | 32.8% | 2066 |
| 7 | ETHUSDT_750 | 0.249 | 0.19 | -0.46 | 6.93 | 32.3% | 57.3% | 25.5% | 372 |

## Per-Asset Detail

### #1 SOLUSDT_750

- **Trades**: 219964 across 1849 windows
- **Ratio distribution**: min=-0.98, p10=-0.40, median=2.43, p90=12.37, max=50.00
- **Consistency**: CV=1.8671
- **Best window**: 2025-04-08 (ratio=50.00)
- **Worst window**: 2022-02-28 (ratio=-0.98)

### #2 LINKUSDT_750

- **Trades**: 161211 across 2054 windows
- **Ratio distribution**: min=-1.03, p10=-0.28, median=1.67, p90=5.12, max=11.72
- **Consistency**: CV=1.0763
- **Best window**: 2025-04-16 (ratio=11.72)
- **Worst window**: 2023-03-20 (ratio=-1.03)

### #3 BTCUSDT_750

- **Trades**: 45878 across 1498 windows
- **Ratio distribution**: min=-3.22, p10=-0.42, median=0.95, p90=5.28, max=50.00
- **Consistency**: CV=2.3493
- **Best window**: 2023-10-13 (ratio=50.00)
- **Worst window**: 2022-06-16 (ratio=-3.22)

### #4 BNBUSDT_750

- **Trades**: 88376 across 1894 windows
- **Ratio distribution**: min=-1.40, p10=-0.80, median=1.22, p90=9.05, max=50.00
- **Consistency**: CV=2.3892
- **Best window**: 2023-05-03 (ratio=50.00)
- **Worst window**: 2024-03-16 (ratio=-1.40)

### #5 ADAUSDT_750

- **Trades**: 172194 across 2065 windows
- **Ratio distribution**: min=-1.26, p10=-0.45, median=0.69, p90=7.07, max=20.19
- **Consistency**: CV=1.8995
- **Best window**: 2021-02-07 (ratio=20.19)
- **Worst window**: 2022-09-01 (ratio=-1.26)

### #6 DOGEUSDT_750

- **Trades**: 796140 across 2066 windows
- **Ratio distribution**: min=-1.06, p10=-0.54, median=0.57, p90=6.03, max=45.94
- **Consistency**: CV=2.541
- **Best window**: 2020-11-04 (ratio=45.94)
- **Worst window**: 2021-09-08 (ratio=-1.06)

### #7 ETHUSDT_750

- **Trades**: 19172 across 372 windows
- **Ratio distribution**: min=-0.99, p10=-0.46, median=0.19, p90=6.93, max=7.35
- **Consistency**: CV=1.4556
- **Best window**: 2020-01-16 (ratio=7.35)
- **Worst window**: 2020-09-14 (ratio=-0.99)
