"""K 线、成交量、MACD 柱和波段线绘图工具。"""

import mplfinance as mpf

from .data import OHLCV_COLUMNS
from .swings_recognition import swings_to_alines


def make_cn_market_style():
    """返回 A 股常用风格：红色上涨、绿色下跌。

    返回:
        mplfinance 可使用的 style 对象。
    """
    market_colors = mpf.make_marketcolors(
        up="red",
        down="green",
        edge={"up": "red", "down": "green"},
        wick={"up": "red", "down": "green"},
        volume={"up": "red", "down": "green"},
    )
    return mpf.make_mpf_style(
        base_mpf_style="classic",
        marketcolors=market_colors,
        gridcolor="#d9d9d9",
        gridstyle="-",
        facecolor="white",
        figcolor="white",
    )


def make_macd_addplots(df, panel=2):
    """构建 MACD 正负柱的附加图层。

    参数:
        df: 已经包含 MACD 列的行情 DataFrame。
        panel: MACD 子图所在面板编号。主图为 0，成交量通常为 1。

    返回:
        mplfinance 的 addplot 列表。
    """
    macd_red = df["MACD"].where(df["MACD"] >= 0, 0)
    macd_green = df["MACD"].where(df["MACD"] < 0, 0)

    return [
        mpf.make_addplot(macd_red, type="bar", panel=panel, color="red", ylabel="MACD"),
        mpf.make_addplot(macd_green, type="bar", panel=panel, color="green"),
    ]


def plot_kline_with_swings(df, swings=None, title="MACD swing detection", show_volume=True, show_macd=True):
    """绘制 K 线图，并可选叠加成交量、MACD 柱和波段线。

    参数:
        df: 包含 Open、High、Low、Close、Volume 的行情 DataFrame。
        swings: 可选的波段表；传入后会在 K 线图上画蓝色波段线。
        title: 图表标题。
        show_volume: 是否显示成交量子图。
        show_macd: 是否显示 MACD 柱子图。
        figsize: 图表尺寸。

    返回:
        mplfinance.plot 的返回值。默认情况下该函数直接展示图表。
    """
    style = make_cn_market_style()
    kwargs = {}

    if swings is not None and not swings.empty:
        kwargs["alines"] = {
            "alines": swings_to_alines(swings),
            "colors": "blue",
            "linestyle": "--",
            "linewidths": 1,
        }

    add_plots = []
    if show_macd:
        macd_panel = 2 if show_volume else 1
        add_plots.extend(make_macd_addplots(df, panel=macd_panel))
        kwargs["addplot"] = add_plots
        kwargs["panel_ratios"] = (4, 1.2, 1.2) if show_volume else (4, 1.2)

    return mpf.plot(
        df[OHLCV_COLUMNS],
        type="candle",
        volume=show_volume,
        style=style,
        figsize=(10, 6),
        title=title,
        ylabel="Price",
        ylabel_lower="Volume" if show_volume else None,
        **kwargs,
    )
