"""数据获取与字段标准化工具。"""

import os
from typing import Any

import pandas as pd


OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def normalize_daily_data(df):
    """将 Tushare 风格的日线数据整理成 mplfinance 可直接绘图的格式。

    参数:
        df: 原始日线数据，通常包含 trade_date、open、high、low、close、vol。

    返回:
        整理后的 DataFrame，包含 Open、High、Low、Close、Volume，并以日期为索引。

    返回结果会按日期升序排列，并使用 ``DatetimeIndex`` 作为索引。
    """
    rename_map = {
        "trade_date": "date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "vol": "Volume",
    }
    data = df.rename(columns=rename_map).copy()

    if "date" not in data.columns:
        raise ValueError("数据中需要包含 'date' 或 'trade_date' 列。")

    missing = [col for col in OHLCV_COLUMNS if col not in data.columns]
    if missing:
        raise ValueError(f"缺少 OHLCV 字段: {missing}")

    data["date"] = pd.to_datetime(data["date"])
    data = data.set_index("date").sort_index()
    data[OHLCV_COLUMNS] = data[OHLCV_COLUMNS].astype(float)
    return data


def fetch_daily_data(ts_code, start_date, end_date, token_env="TUSHARE_TOKEN"):
    """使用 tinyshare/Tushare 兼容接口获取日线数据。

    参数:
        ts_code: 股票代码，例如 "603993.SH"。
        start_date: 开始日期，格式为 "YYYYMMDD"。
        end_date: 结束日期，格式为 "YYYYMMDD"。
        token_env: 保存 token 的环境变量名，默认读取 TUSHARE_TOKEN。

    返回:
        已标准化的日线 DataFrame，可直接用于后续计算和绘图。

    请先在终端或 PyCharm 运行配置中设置 token:

    ``export TUSHARE_TOKEN="..."``
    """
    token = os.getenv(token_env)
    if not token:
        raise RuntimeError(f"请先设置环境变量 {token_env}，再获取数据。")

    try:
        import tinyshare as ts
    except ImportError as exc:
        raise ImportError("请先安装 tinyshare，或者把这里改成 tushare。") from exc

    # tinyshare 暴露了与 tushare 兼容的运行时接口，PyCharm 静态检查
    # 可能识别不到，所以这里用 getattr 避免误报。
    getattr(ts, "set_token")(token)
    pro: Any = ts.pro_api()
    raw = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

    return normalize_daily_data(raw)
