"""基于 MACD 的波段识别规则。"""

import numpy as np
import pandas as pd


def detect_macd_swings_by_histogram_group(df, close_col="Close", macd_col="MACD"):
    """按 MACD 正负柱分组，并在每组内取价格极值来识别波段。
        这个的趋势效果会比较明显，但划分是否合理？需要再次验证。

    参数:
        df: 已经包含 MACD 列的行情 DataFrame。
        close_col: 收盘价列名，默认使用 "Close"。
        macd_col: MACD 柱列名，默认使用 "MACD"。

    返回:
        points_df: 每个 MACD 正负区间对应的价格极值点。
        swings_df: 相邻极值点连接得到的波段表。
        data: 增加 macd_sign 和 group 辅助列后的中间数据。

    这是更适合画图调试的直观版本：
    MACD 正柱区间取最高收盘价，MACD 负柱区间取最低收盘价。
    """
    data = df.copy().sort_index()
    data = data.dropna(subset=[close_col, macd_col])

    data["macd_sign"] = np.where(
        data[macd_col] > 0,
        1,
        np.where(data[macd_col] < 0, -1, 0),
    )
    data = data[data["macd_sign"] != 0].copy()
    data["group"] = (data["macd_sign"] != data["macd_sign"].shift()).cumsum()

    points = []
    for _, group in data.groupby("group"):
        sign = group["macd_sign"].iloc[0]

        if sign > 0:
            idx = group[close_col].idxmax()
            direction = "up"
        else:
            idx = group[close_col].idxmin()
            direction = "down"

        points.append(
            {
                "date": idx,
                "price": data.loc[idx, close_col],
                "direction": direction,
                "macd_sign": sign,
            }
        )

    points_df = pd.DataFrame(points).sort_values("date").reset_index(drop=True)
    swings = []
    for i in range(1, len(points_df)):
        prev = points_df.iloc[i - 1]
        curr = points_df.iloc[i]
        swings.append(
            {
                "start_date": prev["date"],
                "start_price": prev["price"],
                "end_date": curr["date"],
                "end_price": curr["price"],
                "direction": curr["direction"],
            }
        )

    return points_df, pd.DataFrame(swings), data


def detect_macd_swings_paper_rule(df, close_col="Close", macd_col="MACD"):
    """使用报告文字描述中的更严格规则识别波段。

    参数:
        df: 已经包含 MACD 列的行情 DataFrame。
        close_col: 收盘价列名，默认使用 "Close"。
        macd_col: MACD 柱列名，默认使用 "MACD"。

    返回:
        波段表，包含 start_date、start_price、end_date、end_price、direction。

    当 MACD 为正，且当前收盘价创浮动起点以来新高时，确认新上涨波段。
    当 MACD 为负，且当前收盘价创浮动起点以来新低时，确认新下跌波段。
    """
    data = df.copy().sort_index()
    data = data.dropna(subset=[close_col, macd_col])
    if data.empty:
        return pd.DataFrame(
            columns=["start_date", "start_price", "end_date", "end_price", "direction"]
        )

    swings = []
    start_date = data.index[0]
    start_price = data.iloc[0][close_col]
    last_direction = None

    for idx, row in data.iloc[1:].iterrows():
        close = row[close_col]
        macd = row[macd_col]
        segment = data.loc[start_date:idx]

        if macd > 0 and close >= segment[close_col].max():
            if last_direction != "up":
                swings.append(
                    {
                        "start_date": start_date,
                        "start_price": start_price,
                        "end_date": idx,
                        "end_price": close,
                        "direction": "up",
                    }
                )
                last_direction = "up"
                start_date = idx
                start_price = close

        elif macd < 0 and close <= segment[close_col].min():
            if last_direction != "down":
                swings.append(
                    {
                        "start_date": start_date,
                        "start_price": start_price,
                        "end_date": idx,
                        "end_price": close,
                        "direction": "down",
                    }
                )
                last_direction = "down"
                start_date = idx
                start_price = close

    return pd.DataFrame(swings)


def swings_to_alines(swings):
    """将波段表转换成 mplfinance 的 alines 画线格式。

    参数:
        swings: 波段表，包含 start_date、start_price、end_date、end_price。

    返回:
        mplfinance 可识别的 alines 列表。
    """
    return [
        [(row["start_date"], row["start_price"]), (row["end_date"], row["end_price"])]
        for _, row in swings.iterrows()
    ]
