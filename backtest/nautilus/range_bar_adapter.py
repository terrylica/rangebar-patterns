"""Adapter: ClickHouse range bars -> NautilusTrader Bar objects.

Converts range bar DataFrame from ClickHouse into NautilusTrader-compatible
Bar objects for backtesting engine consumption.

Reference: KMeansTransformer/backtest/nautilus_strategy_fast.py

TODO: Implement when ready for live trading validation.
"""

# Adapter skeleton - converts ClickHouse range bars to NautilusTrader Bar objects
# Full implementation follows nautilus_strategy_fast.py patterns
#
# Key considerations:
# - Range bars have variable duration (not fixed-interval)
# - Need custom BarSpecification for range bar type
# - Microstructure features (trade_intensity, kyle_lambda_proxy) as custom data
# - Timestamp mapping from milliseconds to NautilusTrader UnixNanos
