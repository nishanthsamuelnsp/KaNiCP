import numpy as np
import pandas as pd

def detect_seasons(df):

    df = df.copy()

    # -----------------------------
    # Monthly aggregation
    # -----------------------------
    monthly = df.groupby([df.index.year, df.index.month]).mean(numeric_only=True)
    monthly = monthly.groupby(level=1).mean()

    all_months = set(range(1, 13))

    # -----------------------------
    # Identify columns
    # -----------------------------
    temp_col = next((c for c in df.columns if "AT" in c), None)
    rh_col   = next((c for c in df.columns if "RH" in c), None)

    # -----------------------------
    # WINTER
    # -----------------------------
    winter = []
    if temp_col and temp_col in monthly.columns:
        temp_series = monthly[temp_col].dropna()
        threshold = temp_series.quantile(0.25)
        winter = temp_series[temp_series <= threshold].index.tolist()

    # -----------------------------
    # MONSOON
    # -----------------------------
    if rh_col and rh_col in monthly.columns:
        rh_series = monthly[rh_col].dropna()
        threshold = rh_series.quantile(0.75)
        monsoon = rh_series[rh_series >= threshold].index.tolist()
    else:
        monsoon = [6,7,8,9]

    # -----------------------------
    # CLEAN + PRIORITY
    # -----------------------------
    winter = sorted(set(winter))
    monsoon = sorted(set(monsoon))

    # remove overlap (monsoon priority)
    winter = [m for m in winter if m not in monsoon]

    # -----------------------------
    # BASIC VALIDATION
    # -----------------------------
    if not winter or not monsoon:
        return default_seasons(), monthly

    pre = []
    post = []

    w_min = min(winter)
    w_max = max(winter)
    m_min = min(monsoon)

    # -----------------------------
    # CASE 1
    # (you wrote >12, assuming wrap case → interpret as winter wraps year end)
    # -----------------------------
    if 12 in winter and 1 in winter:  # wrap condition (rare but safe)

        val = w_min + 1
        while val != m_min:
            if val > 12:
                val = 1
            pre.append(val)
            val += 1

    # -----------------------------
    # CASE 2
    # winter touches December
    # -----------------------------
    elif w_min < 12 and w_max == 12:

        val = 1
        while val < m_min:
            pre.append(val)
            val += 1

    # -----------------------------
    # CASE 3
    # winter entirely before Dec
    # -----------------------------
    elif w_min < 12 and w_max < 12:

        val = w_max + 1

        # go till 12
        while val <= 12:
            pre.append(val)
            val += 1

        # wrap to 1
        val = 1
        while val < m_min:
            pre.append(val)
            val += 1

    # -----------------------------
    # FALLBACK
    # -----------------------------
    else:
        return default_seasons(), monthly

    # -----------------------------
    # POST = everything else
    # -----------------------------
    assigned = set(winter + monsoon + pre)
    post = list(all_months - assigned)

    # -----------------------------
    # HANDLE SINGLE MONTH EDGE
    # -----------------------------
    def merge_single(season):
        if len(season) == 1:
            if len(winter) < len(monsoon):
                winter.extend(season)
            else:
                monsoon.extend(season)
            return []
        return season

    pre = merge_single(pre)
    post = merge_single(post)

    # -----------------------------
    # FINAL CLEAN
    # -----------------------------
    seasons = {
        "Winter": sorted(set(winter)),
        "Monsoon": sorted(set(monsoon)),
        "Pre-Monsoon": sorted(set(pre)),
        "Post-Monsoon": sorted(set(post)),
    }

    return seasons, monthly


# -----------------------------
# DEFAULT FALLBACK
# -----------------------------
def default_seasons():
    return {
        "Winter": [12,1,2],
        "Pre-Monsoon": [3,4,5],
        "Monsoon": [6,7,8,9],
        "Post-Monsoon": [10,11]
    }
