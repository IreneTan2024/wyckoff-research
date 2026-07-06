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

        # 每组macd正负方向一致的、相连的日子为一个group。
        # 对macd大于0的group，找到其收盘价最高的一天，并将这个点标记为当前波段的最高点
        # 对macd小于0的group，找到其收盘价最低的一天，并将这个点标记为当前波段的最低点
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

    # 相当于只是按macd的正负划分了组，然后找出每个组的最高和最低点来相连。但是怎么说呢，好像也没毛病……就是视角偏事后了。

    return points_df, pd.DataFrame(swings), data


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
