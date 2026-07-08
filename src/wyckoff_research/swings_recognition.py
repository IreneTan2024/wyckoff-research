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


def build_current_structure_lines(points_df, df, state_df=None, cutoff_date=None, close_col="Close", merge_pct=0.01, max_horizontal_lines=5):
    """生成某个截止日期下的当前趋势线和水平线。

    参数:
        points_df: 波段端点表。
        df: 行情数据。
        state_df: 可选的趋势/盘整状态表。
        cutoff_date: 截止日期，默认使用今天。
        close_col: 收盘价列名。
        merge_pct: 水平线合并阈值。
        max_horizontal_lines: 最多保留的水平线数量。

    返回:
        lines_df: 当前趋势线和水平线的合并表。
    """
    data = get_data_until(df, cutoff_date)
    if data.empty:
        return pd.DataFrame()

    extend_to = data.index[-1]
    trend_lines = build_current_trend_lines(
        points_df,
        state_df=state_df,
        cutoff_date=cutoff_date,
        extend_to=extend_to,
    )
    horizontal_lines = build_current_horizontal_lines(
        points_df,
        data,
        cutoff_date=extend_to,
        close_col=close_col,
        merge_pct=merge_pct,
        max_lines=max_horizontal_lines,
    )

    lines = [item for item in [trend_lines, horizontal_lines] if not item.empty]
    if not lines:
        return pd.DataFrame()

    return pd.concat(lines, ignore_index=True)


def build_current_horizontal_lines(points_df, df, cutoff_date=None, close_col="Close", merge_pct=0.01, max_lines=5):
    """生成某个截止日期下的当前水平支撑/阻力线。

    参数:
        points_df: 波段端点表。
        df: 行情数据。
        cutoff_date: 截止日期，默认使用今天。
        close_col: 收盘价列名。
        merge_pct: 水平线合并阈值，默认 1% 以内视为同一价位。
        max_lines: 最多保留的水平线数量。

    返回:
        当前截面的水平线表。
    """
    data = get_data_until(df, cutoff_date)
    points = get_points_until(points_df, cutoff_date)
    if data.empty or points.empty:
        return pd.DataFrame()

    candidates = []
    recent_points = points.tail(4)
    for _, row in recent_points.iterrows():
        candidates.append(
            {
                "date": row["date"],
                "price": row["price"],
                "direction": row["direction"],
                "source": "confirmed",
            }
        )

    floating_point = get_floating_extreme_point(points, data, close_col=close_col)
    if floating_point is not None:
        candidates.append(floating_point)

    current_close = data[close_col].iloc[-1]
    merged_levels = merge_level_candidates(candidates, merge_pct=merge_pct)

    lines = []
    for item in merged_levels:
        level_price = item["level_price"]
        if abs(level_price / current_close - 1) < 1e-6:
            continue

        score = calc_horizontal_line_score(data, level_price, close_col=close_col)
        line_type = "支撑线" if level_price < current_close else "阻力线"

        lines.append(
            {
                "line_kind": "horizontal",
                "line_type": line_type,
                "state": np.nan,
                "start_date": data.index[0],
                "start_price": level_price,
                "end_date": data.index[-1],
                "end_price": level_price,
                "slope": 0,
                "score": score,
                "level_price": level_price,
                "source_count": item["source_count"],
                "source_dates": item["source_dates"],
                "source_types": item["source_types"],
            }
        )

    lines_df = pd.DataFrame(lines)
    if lines_df.empty:
        return lines_df

    lines_df = lines_df.sort_values("score", ascending=False).head(max_lines)
    return lines_df.sort_values("level_price", ascending=False).reset_index(drop=True)


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


def get_points_until(points_df, cutoff_date=None):
    """按截止日期截取波段端点。"""
    points = points_df.copy()
    if points.empty:
        return points

    points["date"] = pd.to_datetime(points["date"])
    points = points.sort_values("date").reset_index(drop=True)

    if cutoff_date is None:
        cutoff = pd.Timestamp.today().normalize()
    else:
        cutoff = pd.Timestamp(cutoff_date)

    return points[points["date"] <= cutoff].copy().reset_index(drop=True)


def merge_level_candidates(candidates, merge_pct=0.01):
    """合并价格接近的候选水平线。"""
    if not candidates:
        return []

    candidates = sorted(candidates, key=lambda item: item["price"])
    groups = []

    for item in candidates:
        if not groups:
            groups.append([item])
            continue

        group_prices = [member["price"] for member in groups[-1]]
        group_price = sum(group_prices) / len(group_prices)
        if abs(item["price"] / group_price - 1) <= merge_pct:
            groups[-1].append(item)
        else:
            groups.append([item])

    merged = []
    for group in groups:
        level_price = sum(item["price"] for item in group) / len(group)
        merged.append(
            {
                "level_price": level_price,
                "source_count": len(group),
                "source_dates": [item["date"] for item in group],
                "source_types": [item["source"] for item in group],
            }
        )

    return merged


def get_floating_extreme_point(points, data, close_col="Close"):
    """取当前未确认波段的浮动极值点。"""
    if points.empty or data.empty:
        return None

    last_point = points.iloc[-1]
    segment = data[data.index >= last_point["date"]]
    if segment.empty:
        return None

    if last_point["direction"] == "down":
        idx = segment[close_col].idxmax()
        direction = "up"
    else:
        idx = segment[close_col].idxmin()
        direction = "down"

    return {
        "date": idx,
        "price": segment.loc[idx, close_col],
        "direction": direction,
        "source": "floating",
    }


def calc_horizontal_line_score(df, level_price, close_col="Close", min_distance=1e-6):
    """计算某条水平线的确认度。

    参数:
        df: 行情数据。
        level_price: 水平线价位。
        close_col: 收盘价列名。
        min_distance: 最小距离，避免收盘价正好等于水平线时除以 0。

    返回:
        水平线确认度。
    """
    distance_pct = (df[close_col] / level_price - 1).abs() * 100
    distance_pct = distance_pct.clip(lower=min_distance)
    return (1 / distance_pct).clip(upper=10).sum()


def build_current_trend_lines(points_df, state_df=None, cutoff_date=None, extend_to=None):
    """生成某个截止日期下的当前趋势线。

    参数:
        points_df: 波段端点表。
        state_df: 可选的趋势/盘整状态表；不传则根据 points_df 重新计算。
        cutoff_date: 截止日期，默认使用今天。
        extend_to: 趋势线向右延伸到的日期，默认等于截止日期或最后一个端点日期。

    返回:
        当前截面的趋势线表。

    上涨趋势下生成需求线和超买线。
    下跌趋势下生成供给线和超卖线。
    盘整状态下暂不生成斜趋势线。
    """
    points = get_points_until(points_df, cutoff_date)
    if points.empty:
        return pd.DataFrame()

    if extend_to is None:
        if cutoff_date is None:
            extend_to = points["date"].max()
        else:
            extend_to = pd.Timestamp(cutoff_date)

    else:
        states = state_df.copy()
        if not states.empty:
            states["date"] = pd.to_datetime(states["date"])
            states = states[states["date"] <= pd.Timestamp(extend_to)]

    if states.empty:
        return pd.DataFrame()

    state = states.sort_values("date").iloc[-1]["state"]
    lines = []

    if state == "上涨趋势":
        bottoms = points[points["direction"] == "down"].tail(2)
        if len(bottoms) < 2:
            return pd.DataFrame()

        bottom1 = bottoms.iloc[0]
        bottom2 = bottoms.iloc[1]
        lines.append(make_sloped_line("需求线", state, bottom1, bottom2, extend_to))

        tops_between = points[
            (points["direction"] == "up")
            & (points["date"] >= bottom1["date"])
            & (points["date"] <= bottom2["date"])
        ]
        if not tops_between.empty:
            top = tops_between.loc[tops_between["price"].idxmax()]
            lines.append(make_sloped_line("超买线", state, bottom1, bottom2, extend_to, top))

    elif state == "下跌趋势":
        tops = points[points["direction"] == "up"].tail(2)
        if len(tops) < 2:
            return pd.DataFrame()

        top1 = tops.iloc[0]
        top2 = tops.iloc[1]
        lines.append(make_sloped_line("供给线", state, top1, top2, extend_to))

        bottoms_between = points[
            (points["direction"] == "down")
            & (points["date"] >= top1["date"])
            & (points["date"] <= top2["date"])
        ]
        if not bottoms_between.empty:
            bottom = bottoms_between.loc[bottoms_between["price"].idxmin()]
            lines.append(make_sloped_line("超卖线", state, top1, top2, extend_to, bottom))

    return pd.DataFrame(lines)


def make_sloped_line(line_type, state, anchor1, anchor2, extend_to, through_point=None):
    """根据两个端点生成趋势线，或生成一条经过指定点的平行线。"""
    date1 = pd.Timestamp(anchor1["date"])
    date2 = pd.Timestamp(anchor2["date"])
    price1 = anchor1["price"]
    price2 = anchor2["price"]
    days = max((date2 - date1).days, 1)
    slope = (price2 - price1) / days

    if through_point is None:
        start_date = date1
        start_price = price1
    else:
        start_date = date1
        through_date = pd.Timestamp(through_point["date"])
        through_price = through_point["price"]
        start_price = through_price - slope * (through_date - start_date).days

    end_date = pd.Timestamp(extend_to)
    end_price = calc_line_price(start_date, start_price, end_date, slope)

    return {
        "line_kind": "trend",
        "line_type": line_type,
        "state": state,
        "start_date": start_date,
        "start_price": start_price,
        "end_date": end_date,
        "end_price": end_price,
        "slope": slope,
        "score": np.nan,
        "level_price": np.nan,
    }


def calc_line_price(start_date, start_price, end_date, slope):
    """根据起点、斜率和目标日期计算趋势线价格。"""
    days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
    return start_price + slope * days
