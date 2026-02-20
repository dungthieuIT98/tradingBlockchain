def add_laguerre_ppo_percent_rank(result, short_g=0.4, long_g=0.8, lkbT=200, lkbB=200):

    highs = [c["high"] for c in result]
    lows = [c["low"] for c in result]

    # hl2 = (high + low) / 2
    hl2 = [(h + l) / 2 for h, l in zip(highs, lows)]

    # --------------------------------
    # Laguerre function (giống Pine)
    # --------------------------------
    def laguerre(g, prices):
        L0 = L1 = L2 = L3 = None
        out = []

        for p in prices:

            if L0 is None:
                L0 = L1 = L2 = L3 = p
            else:
                L0_new = (1 - g) * p + g * L0
                L1_new = -g * L0_new + L0 + g * L1
                L2_new = -g * L1_new + L1 + g * L2
                L3_new = -g * L2_new + L2 + g * L3

                L0, L1, L2, L3 = L0_new, L1_new, L2_new, L3_new

            f = (L0 + 2 * L1 + 2 * L2 + L3) / 6
            out.append(f)

        return out

    lmas = laguerre(short_g, hl2)
    lmal = laguerre(long_g, hl2)

    # --------------------------------
    # PPO
    # --------------------------------
    ppoT = []
    ppoB = []

    for s, l in zip(lmas, lmal):

        if l == 0:
            ppoT.append(None)
            ppoB.append(None)
        else:
            ppoT.append((s - l) / l * 100)
            ppoB.append((l - s) / l * 100)

    # --------------------------------
    # PercentRank (giống TradingView)
    # --------------------------------
    def percent_rank(series, lookback):

        out = [None] * len(series)

        for i in range(len(series)):

            if i < lookback or series[i] is None:
                continue

            window = series[i - lookback : i]

            count = sum(1 for x in window if x is not None and x <= series[i])

            out[i] = count / lookback * 100

        return out

    pctRankT = percent_rank(ppoT, lkbT)
    pctRankB_raw = percent_rank(ppoB, lkbB)

    pctRankB = [-x if x is not None else None for x in pctRankB_raw]

    # --------------------------------
    # Append vào result
    # --------------------------------
    for i in range(len(result)):

        result[i]["lmas"] = lmas[i]
        result[i]["lmal"] = lmal[i]
        result[i]["ppoT"] = ppoT[i]
        result[i]["ppoB"] = ppoB[i]
        result[i]["pctRankT"] = pctRankT[i]
        result[i]["pctRankB"] = pctRankB[i]

    return result
