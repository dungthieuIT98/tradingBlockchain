def add_laguerre_ppo_percent_rank(
    data,
    short_g=0.4,
    long_g=0.8,
    lkb_t=200,
    lkb_b=200,
    pctile=90,
    wrn_pctile=70,
    show_threshold_top=60,
    show_threshold_bot=-60,
    ema1_len=20,
    ema5_len=55,
    min_gap_pct=0.3,
):
    n = len(data)

    # ── Laguerre filter ──────────────────────────────────────────
    def calc_laguerre(g, prices):
        L0 = [0.0] * n
        L1 = [0.0] * n
        L2 = [0.0] * n
        L3 = [0.0] * n
        result = [0.0] * n
        for i in range(n):
            p = prices[i]
            L0[i] = (1 - g) * p + g * (L0[i - 1] if i > 0 else p)
            L1[i] = (
                -g * L0[i]
                + (L0[i - 1] if i > 0 else p)
                + g * (L1[i - 1] if i > 0 else 0)
            )
            L2[i] = (
                -g * L1[i]
                + (L1[i - 1] if i > 0 else 0)
                + g * (L2[i - 1] if i > 0 else 0)
            )
            L3[i] = (
                -g * L2[i]
                + (L2[i - 1] if i > 0 else 0)
                + g * (L3[i - 1] if i > 0 else 0)
            )
            result[i] = (L0[i] + 2 * L1[i] + 2 * L2[i] + L3[i]) / 6
        return result

    # ── hl2 prices ───────────────────────────────────────────────
    hl2 = [(float(d["high"]) + float(d["low"])) / 2 for d in data]
    close = [float(d["close"]) for d in data]

    lmas = calc_laguerre(short_g, hl2)
    lmal = calc_laguerre(long_g, hl2)

    # ── PPO ──────────────────────────────────────────────────────
    ppo_t = [
        (lmas[i] - lmal[i]) / lmal[i] * 100 if lmal[i] != 0 else 0 for i in range(n)
    ]
    ppo_b = [
        (lmal[i] - lmas[i]) / lmal[i] * 100 if lmal[i] != 0 else 0 for i in range(n)
    ]

    # ── Percentile Rank ──────────────────────────────────────────
    def percentrank(series, i, length):
        if i < length:
            window = series[: i + 1]
        else:
            window = series[i - length + 1 : i + 1]
        current = series[i]
        count = sum(1 for v in window if v < current)
        return count / len(window) * 100

    # ── EMA ──────────────────────────────────────────────────────
    def calc_ema(prices, length):
        ema = [0.0] * n
        k = 2 / (length + 1)
        ema[0] = prices[0]
        for i in range(1, n):
            ema[i] = prices[i] * k + ema[i - 1] * (1 - k)
        return ema

    ema_fast = calc_ema(close, ema1_len)
    ema_slow = calc_ema(close, ema5_len)

    # ── Gán kết quả + Signal ─────────────────────────────────────
    prev_col_t = None
    prev_col_b = None

    for i in range(n):
        pct_rank_t = percentrank(ppo_t, i, lkb_t)
        pct_rank_b = percentrank(ppo_b, i, lkb_b) * -1

        gap_pct = (
            abs(ema_fast[i] - ema_slow[i]) / ema_slow[i] * 100
            if ema_slow[i] != 0
            else 0
        )
        up_trend = ema_fast[i] > ema_slow[i] and gap_pct >= min_gap_pct
        down_trend = ema_fast[i] < ema_slow[i] and gap_pct >= min_gap_pct

        # ── Màu TOP (uptrend) ────────────────────────────────────
        if not up_trend:
            col_t = "hidden"
        elif pct_rank_t < show_threshold_top:
            col_t = "gray"
        elif pct_rank_t >= pctile:
            col_t = "red"
        elif pct_rank_t >= wrn_pctile:
            col_t = "orange"
        else:
            col_t = "gray"

        # ── Màu BOTTOM (downtrend) ───────────────────────────────
        pctile_b = pctile * -1
        wrn_pctile_b = wrn_pctile * -1

        if not down_trend:
            col_b = "hidden"
        elif pct_rank_b > show_threshold_bot:
            col_b = "gray"
        elif pct_rank_b <= pctile_b:
            col_b = "lime"
        elif pct_rank_b <= wrn_pctile_b:
            col_b = "green"
        else:
            col_b = "gray"

        # # ── PPO Pro Signal ───────────────────────────────────────
        # signal = None

        # # BUY: top histogram xám → cam (uptrend bắt đầu warning)
        # if prev_col_t == "gray" and col_t == "orange":
        #     signal = "buy"
        # # STOP BUY: cam → xám
        # elif prev_col_t == "orange" and col_t == "gray":
        #     signal = "stop_buy"
        # # SELL: bottom histogram xám → xanh lá
        # elif prev_col_b == "gray" and col_b == "green":
        #     signal = "sell"
        # # STOP SELL: xanh lá → xám
        # elif prev_col_b == "green" and col_b == "gray":
        #     signal = "stop_sell"

        data[i]["pct_rank_t"] = round(pct_rank_t, 2)
        data[i]["pct_rank_b"] = round(pct_rank_b, 2)
        data[i]["col_t"] = col_t
        data[i]["col_b"] = col_b
        data[i]["up_trend"] = up_trend
        data[i]["down_trend"] = down_trend
        data[i]["ppo_pro_signal"] = (
            "buy" if up_trend else "sell" if down_trend else None
        )
        # data[i]["ppo_pro_signal"] = signal

        prev_col_t = col_t if col_t != "hidden" else prev_col_t
        prev_col_b = col_b if col_b != "hidden" else prev_col_b

    return data
