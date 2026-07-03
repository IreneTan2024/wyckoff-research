"""技术指标计算。"""

def calc_macd(df, close_col="Close", fast=12, slow=26, signal=9):
    """计算并添加 DIF、DEA 和 MACD 柱三列。

    参数:
        df: 包含收盘价的 DataFrame。
        close_col: 收盘价列名，默认使用 "Close"。
        fast: 快速 EMA 周期，默认 12。
        slow: 慢速 EMA 周期，默认 26。
        signal: DEA 平滑周期，默认 9。

    返回:
        增加 DIF、DEA、MACD 三列后的 DataFrame。
    """
    data = df.copy()
    ema_fast = data[close_col].ewm(span=fast, adjust=False).mean()
    ema_slow = data[close_col].ewm(span=slow, adjust=False).mean()

    data["DIF"] = ema_fast - ema_slow
    data["DEA"] = data["DIF"].ewm(span=signal, adjust=False).mean()
    data["MACD"] = 2 * (data["DIF"] - data["DEA"])
    return data
