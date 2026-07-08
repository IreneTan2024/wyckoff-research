"""K 线、成交量、MACD 柱和波段线绘图工具。"""

import mplfinance as mpf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .data import OHLCV_COLUMNS
from .swings_recognition import swings_to_alines

plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "PingFang SC", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False


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


def plot_kline_with_swings2(df, swings=None, state_df=None, title="MACD swing detection", show_volume=True, show_macd=True):
    """绘制 K 线图，并可选叠加成交量、MACD 柱、波段线和趋势/盘整标记。

    参数:
        df: 包含 Open、High、Low、Close、Volume 的行情 DataFrame，index 应为日期。
        swings: 可选的波段表；传入后会在 K 线图上画蓝色波段线。
        state_df: 可选的趋势/盘整判断结果表；需要包含 date、state 两列。
        title: 图表标题。
        show_volume: 是否显示成交量子图。
        show_macd: 是否显示 MACD 柱子图。

    返回:
        fig, axes: matplotlib 的图和坐标轴对象。
    """
    plot_df = df.copy()
    plot_df.index = pd.to_datetime(plot_df.index)

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
        add_plots.extend(make_macd_addplots(plot_df, panel=macd_panel))
        kwargs["addplot"] = add_plots
        kwargs["panel_ratios"] = (4, 1.2, 1.2) if show_volume else (4, 1.2)

    fig, axes = mpf.plot(
        plot_df[OHLCV_COLUMNS],
        type="candle",
        volume=show_volume,
        style=style,
        figsize=(10, 6),
        title=title,
        ylabel="Price",
        ylabel_lower="Volume" if show_volume else None,
        returnfig=True,
        **kwargs,
    )

    price_ax = axes[0]

    if state_df is not None and not state_df.empty:
        # label_map = {
        #     "上涨趋势": "涨",
        #     "下跌趋势": "跌",
        #     "收缩盘整": "盘",
        #     "扩张盘整": "盘",
        #     "无法判断": "",
        # }

        label_map = {
            "上涨趋势": "U",
            "下跌趋势": "D",
            "收缩盘整": "SR",
            "扩张盘整": "KR",
            "无法判断": "",
        }

        state_data = state_df.copy()
        state_data["date"] = pd.to_datetime(state_data["date"])

        for _, row in state_data.iterrows():
            date = row["date"]
            state = row["state"]
            label = label_map.get(state, "")

            if not label:
                continue

            if date not in plot_df.index:
                continue

            x = plot_df.index.get_loc(date)
            price = plot_df.loc[date, "Close"]

            if label == "跌":
                xytext = (0, -32)
                va = "top"
            else:
                xytext = (0, 28)
                va = "bottom"

            price_ax.annotate(
                label,
                xy=(x, price),
                xytext=xytext,
                textcoords="offset points",
                ha="center",
                va=va,
                fontsize=12,
                fontweight="bold",
                color="black",
                arrowprops={
                    "arrowstyle": "->",
                    "color": "black",
                    "linewidth": 1,
                },
                zorder=10,
            )

    plt.show()

    return fig, axes


def draw_structure_lines(price_ax, df, structure_lines):
    """在主图上绘制趋势线和水平线。

    参数:
        price_ax: K 线主图坐标轴。
        df: 行情数据，index 为日期。
        structure_lines: 趋势线和水平线表。
    """
    if structure_lines is None or structure_lines.empty:
        return

    plot_df = df.copy()
    plot_df.index = pd.to_datetime(plot_df.index)

    color_map = {
        "需求线": "#d62728",
        "超买线": "#ff7f0e",
        "供给线": "#2ca02c",
        "超卖线": "#17becf",
        "支撑线": "#555555",
        "阻力线": "#555555",
    }

    for _, row in structure_lines.iterrows():
        x1 = get_plot_x(plot_df, row["start_date"])
        x2 = get_plot_x(plot_df, row["end_date"])
        y1 = row["start_price"]
        y2 = row["end_price"]
        line_type = row["line_type"]
        line_kind = row["line_kind"]

        linestyle = "--" if line_kind == "horizontal" else "-"
        linewidth = 1.1 if line_kind == "horizontal" else 1.4
        color = color_map.get(line_type, "#555555")

        price_ax.plot(
            [x1, x2],
            [y1, y2],
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
            alpha=0.9,
            zorder=4,
        )

        if line_kind == "horizontal":
            label = f'{row["score"]:.1f}'
        else:
            label = line_type

        price_ax.text(
            x2,
            y2,
            label,
            fontsize=8,
            color=color,
            ha="left",
            va="center",
        )


def get_plot_x(df, date):
    """将日期转换为 mplfinance 主图中的横轴位置。"""
    date = pd.Timestamp(date)
    if date in df.index:
        return df.index.get_loc(date)

    position = df.index.searchsorted(date)
    if position <= 0:
        return 0
    if position >= len(df):
        return len(df) - 1
    return position


def plot_kline_with_swings3(df, swings=None, structure_lines=None, title="MACD swing detection", show_volume=True, show_macd=True, figsize=(10, 6)):
    """绘制 K 线图，并可选叠加成交量、MACD 柱、波段线和结构线。

    参数:
        df: 包含 Open、High、Low、Close、Volume 的行情 DataFrame。
        swings: 可选的波段表；传入后会在 K 线图上画蓝色波段线。
        structure_lines: 可选的趋势线和水平线表。
        title: 图表标题。
        show_volume: 是否显示成交量子图。
        show_macd: 是否显示 MACD 柱子图。
        figsize: 图表尺寸。

    返回:
        fig, axes: matplotlib 图对象和坐标轴对象。
    """
    plot_df = df.copy()
    plot_df.index = pd.to_datetime(plot_df.index)

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
        add_plots.extend(make_macd_addplots(plot_df, panel=macd_panel))
        kwargs["addplot"] = add_plots
        kwargs["panel_ratios"] = (4, 1.2, 1.2) if show_volume else (4, 1.2)

    fig, axes = mpf.plot(
        plot_df[OHLCV_COLUMNS],
        type="candle",
        volume=show_volume,
        style=style,
        figsize=figsize,
        title=title,
        ylabel="Price",
        ylabel_lower="Volume" if show_volume else None,
        returnfig=True,
        **kwargs,
    )

    draw_structure_lines(axes[0], plot_df, structure_lines)
    plt.show()

    return fig, axes


def get_data_until(df, cutoff_date=None):
    """按截止日期截取行情数据。

    参数:
        df: 行情 DataFrame，index 应为日期。
        cutoff_date: 截止日期，默认使用今天；如果行情数据没有今天，则取今天以前的全部数据。

    返回:
        截止日期以前的行情数据。
    """
    data = df.copy()
    data.index = pd.to_datetime(data.index)
    data = data.sort_index()

    if cutoff_date is None:
        cutoff = pd.Timestamp.today().normalize()
    else:
        cutoff = pd.Timestamp(cutoff_date)

    return data[data.index <= cutoff].copy()
