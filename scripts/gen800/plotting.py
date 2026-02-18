"""Gen800 Bokeh plot customization for range bar equity curves.

Extracts _plot_tall() from gen800_reconstruct.py to keep file under 500 lines.
AP-20: Uses integer RangeIndex + CustomJSTickFormatter for time labels.

Refs #40, #42
"""

from __future__ import annotations


def plot_tall(bt, filename: str, timestamps=None, panel_height: int = 200):
    """Generate backtesting.py plot with equal-height panels, gray HLC bars.

    Customizations over default backtesting.py plot:
    1. All sub-figures set to equal height (panel_height px each)
    2. OHLC candlestick bodies hidden, replaced with gray HLC tick bars
    3. Trade markers keep original red/green coloring
    4. X-axis shows real timestamps at regular bar intervals
    """
    import backtesting._plotting as _bp
    from bokeh.models import Segment, VBar

    GRAY = "#999999"

    # Force ALL figures to the same height by patching _figure
    orig_figure = _bp._figure

    def equal_height_figure(*args, **kwargs):
        kwargs["height"] = panel_height
        return orig_figure(*args, **kwargs)

    orig_indicator_height = _bp._INDICATOR_HEIGHT
    _bp._INDICATOR_HEIGHT = panel_height
    _bp._figure = equal_height_figure

    try:
        fig = bt.plot(
            filename=filename,
            open_browser=False,
            plot_drawdown=True,
            plot_volume=True,
        )
    finally:
        _bp._INDICATOR_HEIGHT = orig_indicator_height
        _bp._figure = orig_figure

    if fig is None:
        return

    # Collect all sub-figures from the gridplot
    children = []
    if hasattr(fig, "children"):
        for row in fig.children:
            if hasattr(row, "__iter__"):
                for child in row:
                    if child is not None:
                        children.append(child)
            elif row is not None:
                children.append(row)

    # Find the OHLC figure (the one with VBar renderers = candlesticks)
    fig_ohlc = None
    for child in children:
        for renderer in getattr(child, "renderers", []):
            if isinstance(getattr(renderer, "glyph", None), VBar):
                fig_ohlc = child
                break
        if fig_ohlc:
            break

    if fig_ohlc is None:
        return

    # Replace candlestick vbars with gray HLC tick bars
    source = None
    for renderer in list(fig_ohlc.renderers):
        glyph = getattr(renderer, "glyph", None)
        if isinstance(glyph, VBar):
            source = renderer.data_source
            renderer.visible = False  # Hide candlestick body

    if source is not None:
        tick_w = 0.35
        source.data["open_x0"] = [x - tick_w for x in source.data["index"]]
        source.data["open_x1"] = list(source.data["index"])
        source.data["close_x0"] = list(source.data["index"])
        source.data["close_x1"] = [x + tick_w for x in source.data["index"]]

        # Open tick (left horizontal)
        fig_ohlc.segment(
            x0="open_x0", y0="Open", x1="open_x1", y1="Open",
            source=source, color=GRAY, line_width=1.0,
        )
        # Close tick (right horizontal)
        fig_ohlc.segment(
            x0="close_x0", y0="Close", x1="close_x1", y1="Close",
            source=source, color=GRAY, line_width=1.0,
        )

    # Gray out only the HL vertical segment (first Segment renderer = OHLC HL line)
    # Trade position lines are MultiLine, not Segment, so this is safe
    for renderer in fig_ohlc.renderers:
        glyph = getattr(renderer, "glyph", None)
        if isinstance(glyph, Segment) and hasattr(glyph, "line_color"):
            # Only gray the original HL segment (color="black"), not our new ticks
            if glyph.line_color == "black":
                glyph.line_color = GRAY

    # Set log scale on Equity/Return panels, cube-root transform on Volume
    import numpy as np
    from bokeh.models import LogScale

    for child in children:
        label = getattr(child, "yaxis", [None])[0]
        if label is None:
            continue
        axis_label = getattr(label, "axis_label", "")
        if axis_label in ("Equity", "Return"):
            child.yaxis[0].axis_label = f"{axis_label} (log)"
            child.y_scale = LogScale()
        elif axis_label == "Volume":
            # Cube-root transform: handles 7-9 order-of-magnitude dynamic range
            # better than log (which over-corrects to left-skewed) and gracefully
            # handles near-zero values (cbrt(0)=0, no NaN/inf issues).
            # Analysis: cbrt gives skew=0.22, kurtosis=3.00 (near-Gaussian)
            #           vs log10 skew=-1.45 (over-corrected)
            for renderer in child.renderers:
                glyph = getattr(renderer, "glyph", None)
                if isinstance(glyph, VBar):
                    src = renderer.data_source
                    if "Volume" in src.data:
                        raw = np.asarray(src.data["Volume"], dtype=float)
                        src.data["Volume"] = np.cbrt(raw).tolist()
            child.yaxis[0].axis_label = "Volume (cube root scaled)"

    # Add timestamp labels to x-axis if timestamps provided
    if timestamps is not None:
        from bokeh.models import CustomJSTickFormatter, FixedTicker

        n_bars = len(timestamps)
        # ~20 evenly spaced ticks across the full range
        step = max(1, n_bars // 20)
        tick_positions = list(range(0, n_bars, step))

        # Build JS lookup: bar_index → "YYYY-MM-DD HH:MM"
        ts_map = {}
        for pos in tick_positions:
            if pos < n_bars:
                ts_map[pos] = str(timestamps[pos])[:16]  # "YYYY-MM-DD HH:MM"

        js_map = "var m = {" + ",".join(f"{k}:'{v}'" for k, v in ts_map.items()) + "};"
        js_code = js_map + " return m[tick] || '';"

        formatter = CustomJSTickFormatter(code=js_code)
        ticker = FixedTicker(ticks=tick_positions)

        for child in children:
            if hasattr(child, "xaxis"):
                child.xaxis[0].ticker = ticker
                child.xaxis[0].formatter = formatter
                child.xaxis[0].major_label_orientation = 0.7  # ~40 degrees

    # Re-save with modifications
    from bokeh.io import output_file as bokeh_output_file
    from bokeh.io import save as bokeh_save

    bokeh_output_file(filename)
    bokeh_save(fig)
