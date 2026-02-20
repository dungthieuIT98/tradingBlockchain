import numpy as np


def add_zscore_predictive_zones(
    result, length=144, smooth=20, history_depth=25, z_thresh=1.5
):
    """
    Modify result in-place.
    Each element must contain:
        open, high, low, close, volume
    """

    if len(result) < length + smooth:
        return result

    closes = np.array([x["close"] for x in result], dtype=float)
    highs = np.array([x["high"] for x in result], dtype=float)
    lows = np.array([x["low"] for x in result], dtype=float)
    vols = np.array([x["volume"] for x in result], dtype=float)

    n = len(result)

    # -----------------------
    # Helpers
    # -----------------------

    def rolling_mean(arr, period):
        out = np.full(n, np.nan)
        for i in range(period - 1, n):
            out[i] = np.mean(arr[i - period + 1 : i + 1])
        return out

    def rolling_std(arr, period):
        out = np.full(n, np.nan)
        for i in range(period - 1, n):
            out[i] = np.std(arr[i - period + 1 : i + 1])
        return out

    def vwma(values, volume, period):
        out = np.full(n, np.nan)
        for i in range(period - 1, n):
            v = volume[i - period + 1 : i + 1]
            val = values[i - period + 1 : i + 1]
            out[i] = np.sum(val * v) / np.sum(v)
        return out

    def pivot_high(arr):
        out = np.full(n, np.nan)
        for i in range(1, n - 1):
            if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
                out[i] = arr[i]
        return out

    def pivot_low(arr):
        out = np.full(n, np.nan)
        for i in range(1, n - 1):
            if arr[i] < arr[i - 1] and arr[i] < arr[i + 1]:
                out[i] = arr[i]
        return out

    # -----------------------
    # 1. Z-score
    # -----------------------

    mean = rolling_mean(closes, length)
    std_dev = rolling_std(closes, length)

    raw_z = (closes - mean) / std_dev
    z_score = vwma(raw_z, vols, smooth)

    # -----------------------
    # 2. Reversal Detection
    # -----------------------

    ph = pivot_high(z_score)
    pl = pivot_low(z_score)

    top_reversals = []
    bot_reversals = []

    avg_top_level = np.full(n, np.nan)
    avg_bot_level = np.full(n, np.nan)

    for i in range(n):

        if not np.isnan(ph[i]) and ph[i] > z_thresh:
            top_reversals.insert(0, ph[i])
            if len(top_reversals) > history_depth:
                top_reversals.pop()

        if not np.isnan(pl[i]) and pl[i] < -z_thresh:
            bot_reversals.insert(0, pl[i])
            if len(bot_reversals) > history_depth:
                bot_reversals.pop()

        avg_top_level[i] = np.mean(top_reversals) if top_reversals else 2.0
        avg_bot_level[i] = np.mean(bot_reversals) if bot_reversals else -2.0

    # -----------------------
    # 3. Price Bands
    # -----------------------

    res_band_low = mean + avg_top_level * std_dev
    res_band_high = mean + (avg_top_level + 0.5) * std_dev

    sup_band_high = mean + avg_bot_level * std_dev
    sup_band_low = mean + (avg_bot_level - 0.5) * std_dev

    # -----------------------
    # 4. Signals
    # -----------------------

    long_signal = np.full(n, False)
    short_signal = np.full(n, False)

    for i in range(1, n):

        long_signal[i] = (
            not np.isnan(sup_band_high[i])
            and lows[i] < sup_band_high[i]
            and not (lows[i - 1] < sup_band_high[i - 1])
        )

        short_signal[i] = (
            not np.isnan(res_band_low[i])
            and highs[i] > res_band_low[i]
            and not (highs[i - 1] > res_band_low[i - 1])
        )

    # -----------------------
    # 5. Attach to result
    # -----------------------

    for i in range(n):

        result[i]["z_score"] = float(z_score[i]) if not np.isnan(z_score[i]) else None
        result[i]["avg_top_level"] = float(avg_top_level[i])
        result[i]["avg_bot_level"] = float(avg_bot_level[i])

        result[i]["res_band_low"] = (
            float(res_band_low[i]) if not np.isnan(res_band_low[i]) else None
        )
        result[i]["res_band_high"] = (
            float(res_band_high[i]) if not np.isnan(res_band_high[i]) else None
        )

        result[i]["sup_band_low"] = (
            float(sup_band_low[i]) if not np.isnan(sup_band_low[i]) else None
        )
        result[i]["sup_band_high"] = (
            float(sup_band_high[i]) if not np.isnan(sup_band_high[i]) else None
        )

        result[i]["signal_zscore"] = (
            "long signal"
            if long_signal[i]
            else ("short signal" if short_signal[i] else None)
        )

    return result
