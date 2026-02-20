def add_ema_to_result(result, periods=[20, 25, 30, 35, 40, 45, 50, 55]):

    closes = [c["close"] for c in result]

    def calculate_ema(prices, period):
        k = 2 / (period + 1)
        ema = [None] * len(prices)

        if len(prices) >= period:
            sma = sum(prices[:period]) / period
            ema[period - 1] = sma

            for i in range(period, len(prices)):
                ema[i] = prices[i] * k + ema[i - 1] * (1 - k)

        return ema

    # Tính và thêm tất cả EMA vào result
    ema_map = {}
    for period in periods:
        ema_values = calculate_ema(closes, period)
        ema_map[period] = ema_values

        for i in range(len(result)):
            result[i][f"ema_{period}"] = ema_values[i]

    # ── Thêm cột trend ────────────────────────────────────────────────────────
    # Logic:
    #   "up"   — tất cả EMA xếp theo thứ tự giảm dần (ema20 > ema25 > ... > ema55)
    #            VÀ close > ema20  →  uptrend rõ ràng
    #   "down" — tất cả EMA xếp theo thứ tự tăng dần (ema20 < ema25 < ... < ema55)
    #            VÀ close < ema20  →  downtrend rõ ràng
    #   "side" — không thỏa điều kiện nào (ribbon đang rối / sideways)
    # ─────────────────────────────────────────────────────────────────────────
    sorted_periods = sorted(periods)  # [20, 25, 30, 35, 40, 45, 50, 55]

    for i in range(len(result)):
        ema_vals = [ema_map[p][i] for p in sorted_periods]

        # Bỏ qua bar chưa đủ dữ liệu (còn None)
        if any(v is None for v in ema_vals):
            result[i]["trend"] = None
            continue

        close = result[i]["close"]

        # Kiểm tra ribbon alignment
        is_up = all(ema_vals[j] > ema_vals[j + 1] for j in range(len(ema_vals) - 1))
        is_down = all(ema_vals[j] < ema_vals[j + 1] for j in range(len(ema_vals) - 1))

        if is_up and close > ema_vals[0]:  # close > ema20
            result[i]["trend"] = "up"
        elif is_down and close < ema_vals[0]:  # close < ema20
            result[i]["trend"] = "down"
        else:
            result[i]["trend"] = None

    return result
