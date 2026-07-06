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
from wyckoff_research.plotting import plot_kline_with_swings, plot_kline_with_swings2
from wyckoff_research.swings_recognition import detect_macd_swings_by_histogram_group

def main():
    df = fetch_daily_data(
        ts_code="603993.SH",
        start_date="20250808",
        end_date="20260630",
    )
    df = calc_macd(df)

    # 绘制包含趋势线和macd柱的股价图
    # plot_kline_with_swings(df, swings, title="MACD 波段划分")

    points, swings, data = detect_macd_swings_by_histogram_group(df)

    state_df = classify_market_state(points)

    fig, axes = plot_kline_with_swings2(
        df,
        swings=swings,
        state_df=state_df,
        title="MACD 波段划分下趋势与盘整示意图",
        show_volume=True,
        show_macd=True,
    )



if __name__ == "__main__":
    main()
