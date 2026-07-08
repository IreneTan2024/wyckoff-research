"""技术指标计算。"""

import pandas as pd

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


def update_state_with_latest_price(points_df, df, close_col="Close"):
    """用最新收盘价对趋势/盘整状态做实时修正。

    参数:
        points_df: 已确认的波段端点表。
        df: 行情数据，index 为日期，包含收盘价列。
        close_col: 收盘价列名，默认使用 "Close"。

    返回:
        latest_state: 根据确认端点和最新价格修正后的状态。
    """
    state_df = classify_market_state(points_df)

    if state_df.empty:
        return "无法判断"

    latest_state = state_df.iloc[-1]["state"]
    latest_close = df[close_col].iloc[-1]

    points = points_df.copy().sort_values("date").reset_index(drop=True)

    tops = points[points["direction"] == "up"].tail(2)
    bottoms = points[points["direction"] == "down"].tail(2)

    if len(tops) < 2 or len(bottoms) < 2:
        return latest_state

    last_top_price = tops.iloc[-1]["price"]
    last_bottom_price = bottoms.iloc[-1]["price"]

    # 最新价格突破最近顶端点，说明上方关键价位被突破
    if latest_close > last_top_price:
        return "上涨趋势"

    # 最新价格跌破最近底端点，说明下方关键价位被突破
    if latest_close < last_bottom_price:
        return "下跌趋势"

    # 没突破关键价位，就延续之前状态
    return latest_state


def compare_price_level(price_prev, price_curr, tolerance_pct=0.005):
    """比较两个价位的关系：up、down、flat。

    参数:
        price_prev: 前一个端点价格。
        price_curr: 后一个端点价格。
        tolerance_pct: 容忍阈值，默认 0.5%。

    返回:
        "up"、"down" 或 "flat"。
    """
    change_pct = price_curr / price_prev - 1

    if change_pct > tolerance_pct:
        return "up"
    elif change_pct < -tolerance_pct:
        return "down"
    else:
        return "flat"


def classify_market_state(points_df, tolerance_pct=0.005):
    """根据最近 4 个波段端点判断趋势或盘整状态。

    参数:
        points_df: 波段端点表，至少包含 date、price、direction 三列。
                   direction 为 "up" 的点视为顶端点，
                   direction 为 "down" 的点视为底端点。

                   顶/底变化小于 0.5%：视为 flat
                   但最终仍然只输出：
                   上涨趋势、下跌趋势、收缩盘整、扩张盘整

    返回:
        state_df: 每个可判断位置对应的市场状态表。
    """
    points = points_df.copy().sort_values("date").reset_index(drop=True)

    states = []

    for i in range(len(points)):
        current_points = points.iloc[: i + 1]

        tops = current_points[current_points["direction"] == "up"].tail(2)
        bottoms = current_points[current_points["direction"] == "down"].tail(2)

        # 至少需要最近两个顶和两个底，才能判断状态
        if len(tops) < 2 or len(bottoms) < 2:
            continue

        top_prev = tops.iloc[0]
        top_curr = tops.iloc[1]
        bottom_prev = bottoms.iloc[0]
        bottom_curr = bottoms.iloc[1]

        top_relation = compare_price_level(
            top_prev["price"],
            top_curr["price"],
            tolerance_pct=tolerance_pct,
        )

        bottom_relation = compare_price_level(
            bottom_prev["price"],
            bottom_curr["price"],
            tolerance_pct=tolerance_pct,
        )

        if top_relation in ["up", "flat"] and bottom_relation == "up":
            state = "上涨趋势"
        elif top_relation in ["down", "flat"] and bottom_relation == "down":
            state = "下跌趋势"
        elif top_relation == "down" and bottom_relation in ["up", "flat"]:
            state = "收缩盘整"
        elif top_relation == "up" and bottom_relation in ["down", "flat"]:
            state = "扩张盘整"
        else:
            state = "无法判断"

        states.append(
            {
                "date": current_points.iloc[-1]["date"],
                "state": state,
                "top_prev_date": top_prev["date"],
                "top_prev_price": top_prev["price"],
                "top_curr_date": top_curr["date"],
                "top_curr_price": top_curr["price"],
                "bottom_prev_date": bottom_prev["date"],
                "bottom_prev_price": bottom_prev["price"],
                "bottom_curr_date": bottom_curr["date"],
                "bottom_curr_price": bottom_curr["price"],
            }
        )

    return pd.DataFrame(states)