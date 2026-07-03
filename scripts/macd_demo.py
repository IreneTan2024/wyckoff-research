"""从命令行运行 MACD 波段划分示例。

获取数据前，请先设置 token:

    export TUSHARE_TOKEN="..."
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wyckoff_research.data import fetch_daily_data
from wyckoff_research.indicators import calc_macd
from wyckoff_research.plotting import plot_kline_with_swings
from wyckoff_research.swings_recognition import detect_macd_swings_by_histogram_group


def main():
    df = fetch_daily_data(
        ts_code="603993.SH",
        start_date="20260408",
        end_date="20260630",
    )
    df = calc_macd(df)
    points, swings, _ = detect_macd_swings_by_histogram_group(df)
    print(swings)

    # 绘制包含趋势线和macd柱的股价图
    plot_kline_with_swings(df, swings, title="MACD 波段划分")


if __name__ == "__main__":
    main()
