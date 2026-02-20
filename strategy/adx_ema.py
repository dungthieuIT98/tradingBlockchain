"""
ADX + EMA Ribbon Signal — Python list version
Input : OHLCV as plain Python lists + list of EMA series (pre-computed)
Output: SignalResult (NamedTuple) with buy_signal, sell_signal, warn_weak, warn_down
"""

from typing import NamedTuple


# ══════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════
ADX_LEN = 14
ADX_SMOOTH = 14
ADX_THRESHOLD = 35
DI_MIN_SEP = 5.0


# ══════════════════════════════════════════════
#  NAMEDTUPLE OUTPUT
# ══════════════════════════════════════════════
class SignalResult(NamedTuple):
    buy_signal: list
    sell_signal: list
    warn_weak: list
    warn_down: list
    adx: list
    di_plus: list
    di_minus: list


# ══════════════════════════════════════════════
#  INTERNAL HELPERS
# ══════════════════════════════════════════════


def _wilder_smooth(values: list, period: int) -> list:
    """Wilder RMA smoothing — khớp với TradingView ta.rma()"""
    n = len(values)
    result = [float("nan")] * n
    alpha = 1.0 / period

    start = period - 1
    while start < n and values[start] != values[start]:  # skip nan
        start += 1
    if start >= n:
        return result

    window = [v for v in values[max(0, start - period + 1) : start + 1] if v == v]
    if not window:
        return result
    result[start] = sum(window) / len(window)

    for i in range(start + 1, n):
        v = values[i]
        if v != v:
            result[i] = result[i - 1]
        else:
            result[i] = result[i - 1] * (1 - alpha) + v * alpha
    return result


def _compute_dmi(high, low, close, di_len=ADX_LEN, adx_smooth=ADX_SMOOTH):
    """Tính (di_plus, di_minus, adx) từ OHLC lists — Wilder smoothing."""
    n = len(close)
    nan = float("nan")

    tr_list = [nan] * n
    dmp_list = [nan] * n
    dmm_list = [nan] * n

    for i in range(1, n):
        h, l, pc = high[i], low[i], close[i - 1]
        tr_list[i] = max(h - l, abs(h - pc), abs(l - pc))
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        dmp_list[i] = up if (up > down and up > 0) else 0.0
        dmm_list[i] = down if (down > up and down > 0) else 0.0

    atr_s = _wilder_smooth(tr_list, di_len)
    dmp_s = _wilder_smooth(dmp_list, di_len)
    dmm_s = _wilder_smooth(dmm_list, di_len)

    di_plus = [nan] * n
    di_minus = [nan] * n
    dx_list = [nan] * n

    for i in range(n):
        a = atr_s[i]
        if a != a or a == 0:
            continue
        dip = dmp_s[i] / a * 100
        dim = dmm_s[i] / a * 100
        di_plus[i] = dip
        di_minus[i] = dim
        denom = dip + dim
        dx_list[i] = abs(dip - dim) / denom * 100 if denom != 0 else 0.0

    adx = _wilder_smooth(dx_list, adx_smooth)
    return di_plus, di_minus, adx


# ══════════════════════════════════════════════
#  MAIN FUNCTION
# ══════════════════════════════════════════════


def compute_signals(
    open_: list,
    high: list,
    low: list,
    close: list,
    volume: list,
    emas: list,  # list of lists: [[ema20...], [ema25...], ...]
    adx_threshold: int = ADX_THRESHOLD,
    di_min_sep: float = DI_MIN_SEP,
    di_len: int = ADX_LEN,
    adx_smooth: int = ADX_SMOOTH,
) -> SignalResult:
    """
    Parameters
    ----------
    open_, high, low, close, volume : list[float]
        OHLCV cùng độ dài n.

    emas : list[list[float]]
        Các EMA series đã tính sẵn, mỗi phần tử là 1 list độ dài n.
        Ví dụ: [ema20_series, ema25_series, ..., ema55_series]
        (hàm nhận vào nhưng logic signal hiện tại dùng ADX + DI,
         emas giữ sẵn để bạn extend thêm điều kiện alignment nếu cần)

    adx_threshold : int   — ngưỡng ADX trên (default 35)
    di_min_sep    : float — khoảng cách |DI+ - DI-| tối thiểu (default 5.0)

    Returns
    -------
    SignalResult (NamedTuple) — truy cập bằng .field hoặc index
        .buy_signal  : list[bool]
        .sell_signal : list[bool]
        .warn_weak   : list[bool]
        .warn_down   : list[bool]
        .adx         : list[float]
        .di_plus     : list[float]
        .di_minus    : list[float]
    """
    n = len(close)

    # ── 1. Tính ADX / DI ─────────────────────
    di_plus, di_minus, adx = _compute_dmi(high, low, close, di_len, adx_smooth)

    # ── 2. Khởi tạo output ───────────────────
    buy_signal = [False] * n
    sell_signal = [False] * n
    warn_weak = [False] * n
    warn_down_raw = [False] * n

    # ── 3. Loop tính signal ──────────────────
    for i in range(2, n):
        dip = di_plus[i]
        dim = di_minus[i]
        adx_ = adx[i]

        if dip != dip or dim != dim or adx_ != adx_:  # nan guard
            continue

        di_sep = abs(dip - dim)
        bull_candle = close[i] > open_[i]
        bear_candle = close[i] < open_[i]
        bear_candle2 = close[i - 1] < open_[i - 1]
        valid = 15 < adx_ < adx_threshold

        # ── Buy ──────────────────────────────
        if valid and dip > dim and dip > 30 and di_sep >= di_min_sep and bull_candle:
            buy_signal[i] = True

        # ── Sell ─────────────────────────────
        if (
            valid
            and dim > dip
            and dim > 30
            and di_sep >= di_min_sep
            and bear_candle
            and bear_candle2
        ):
            sell_signal[i] = True

        # ── warn_weak: ADX cross xuống threshold ──
        adx_prev = adx[i - 1]
        if adx_prev == adx_prev and adx_ < adx_threshold <= adx_prev:
            warn_weak[i] = True

        # ── warn_down raw ────────────────────
        dim1 = di_minus[i - 1]
        dim2 = di_minus[i - 2]
        hist_down = dim > 30 and dim1 > 30 and dim2 > 30
        if hist_down and adx_ > adx_threshold and dim > dip and not sell_signal[i]:
            warn_down_raw[i] = True

    # ── 4. warn_down cooldown 5 bar ──────────
    warn_down = [False] * n
    last_warn = -999
    for i in range(n):
        if warn_down_raw[i] and (i - last_warn) >= 5:
            warn_down[i] = True
            last_warn = i

    return SignalResult(
        buy_signal=buy_signal,
        sell_signal=sell_signal,
        warn_weak=warn_weak,
        warn_down=warn_down,
        adx=adx,
        di_plus=di_plus,
        di_minus=di_minus,
    )


# ══════════════════════════════════════════════
#  DEMO
# ══════════════════════════════════════════════
if __name__ == "__main__":
    import random

    random.seed(42)

    n = 200
    close = [100.0]
    for _ in range(n - 1):
        close.append(close[-1] + random.gauss(0, 0.5))

    open_ = [c - abs(random.gauss(0, 0.3)) for c in close]
    high = [c + abs(random.gauss(0, 0.5)) for c in close]
    low = [c - abs(random.gauss(0, 0.5)) for c in close]
    volume = [random.uniform(1000, 5000) for _ in range(n)]

    # Giả lập EMA đã tính sẵn
    def make_ema(prices, span):
        result, alpha = [], 2 / (span + 1)
        for i, p in enumerate(prices):
            result.append(p if i == 0 else result[-1] * (1 - alpha) + p * alpha)
        return result

    emas = [make_ema(close, s) for s in [20, 25, 30, 35, 40, 45, 50, 55]]

    # ── Gọi hàm ──────────────────────────────
    result = compute_signals(open_, high, low, close, volume, emas)

    # ── In kết quả ───────────────────────────
    print(f"{'i':>4} {'close':>8} {'adx':>7} {'DI+':>7} {'DI-':>7}  BUY SELL WEAK DOWN")
    print("-" * 65)
    for i in range(180, 200):
        adx_ = result.adx[i]
        print(
            f"{i:>4} {close[i]:>8.3f} {adx_:>7.2f} "
            f"{result.di_plus[i]:>7.2f} {result.di_minus[i]:>7.2f}  "
            f"{'✓' if result.buy_signal[i]  else '·':>3} "
            f"{'✓' if result.sell_signal[i] else '·':>3} "
            f"{'✓' if result.warn_weak[i]   else '·':>3} "
            f"{'✓' if result.warn_down[i]   else '·':>3}"
        )

    print(
        f"\nTotal → Buy:{sum(result.buy_signal)}  Sell:{sum(result.sell_signal)}  "
        f"WarnWeak:{sum(result.warn_weak)}  WarnDown:{sum(result.warn_down)}"
    )

    # Ví dụ truy cập
    print("\n--- Truy cập field ---")
    print(f"result.buy_signal[-1]  = {result.buy_signal[-1]}")
    print(f"result.adx[-1]         = {result.adx[-1]:.4f}")
    print(f"result.di_plus[-1]     = {result.di_plus[-1]:.4f}")

    # Unpack như tuple nếu muốn
    buy, sell, weak, down, adx_arr, dip_arr, dim_arr = result
    print(f"\nUnpack OK — len(buy)={len(buy)}")
