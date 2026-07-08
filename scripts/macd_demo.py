"""从命令行运行 MACD 波段划分示例。

获取数据前，请先设置 token:

    export TUSHARE_TOKEN="..."
"""

from pathlib import Path
import sys
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wyckoff_research.data import fetch_daily_data
from wyckoff_research.indicators import calc_macd, classify_market_state
from wyckoff_research.plotting import plot_kline_with_swings, plot_kline_with_swings2, plot_kline_with_swings3
from wyckoff_research.swings_recognition import detect_macd_swings_by_histogram_group, build_current_structure_lines

def main(start_date, end_date, ts_code):
    df = fetch_daily_data(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )
    # 1.1、计算macd
    df = calc_macd(df)

    # 1.2、计算波段并绘制
    # plot_kline_with_swings(df, swings, title="MACD 波段划分")
    points, swings, data = detect_macd_swings_by_histogram_group(df)

    # 2.1、划分趋势和盘整，每个端点由包含其自己在内的最近(向前)四个端点确认
    state_df = classify_market_state(points)

    # 2.2、绘制包含波段、macd柱、趋势和盘整的股价图
    fig, axes = plot_kline_with_swings2(
        df,
        swings=swings,
        state_df=state_df,
        title="MACD 波段划分下趋势与盘整示意图",
        show_volume=True,
        show_macd=True,
    )

    cutoff_date = "2026-06-30"

    # 3、确定趋势和盘整后，确定辅助线
    structure_lines = build_current_structure_lines(
        points,
        df,
        state_df=state_df,
        cutoff_date=cutoff_date,  # 不传则默认今天
    )

    fig, axes = plot_kline_with_swings3(
        df,
        swings=swings,
        structure_lines=structure_lines,
        title="MACD 波段划分下趋势线与水平线",
    )



if __name__ == "__main__":
    main(ts_code="603993.SH", start_date="20250808", end_date="20260630")
