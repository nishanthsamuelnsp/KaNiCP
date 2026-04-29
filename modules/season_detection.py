import numpy as np
import pandas as pd

def detect_seasons(df):

    df = df.copy()

    # -----------------------------
    # Monthly aggregation (multi-year safe)
    # -----------------------------
    monthly = df.groupby([df.index.year, df.index.month]).mean(numeric_only=True)
    monthly = monthly.groupby(level=1).mean()  # avg across years

    all_months = set(range(1, 13))

    # -----------------------------
    # Identify columns
    # -----------------------------
    temp_col = next((c for c in df.columns if "AT" in c), None)
    rh_col   = next((c for c in df.columns if "RH" in c), None)

    # -----------------------------
    # WINTER (lowest temp)
    # -----------------------------
    winter_months = []
    if temp_col and temp_col in monthly.columns:
        temp_series = monthly[temp_col].dropna()

        threshold = temp_series.quantile(0.25)
        winter_months = temp_series[temp_series <= threshold].index.tolist()

    # -----------------------------
    # MONSOON (high RH)
    # -----------------------------
    if rh_col and rh_col in monthly.columns:
        rh_series = monthly[rh_col].dropna()
        threshold = rh_series.quantile(0.75)
        monsoon_months = rh_series[rh_series >= threshold].index.tolist()
    else:
        # fallback India
        monsoon_months = [6, 7, 8, 9]

    # -----------------------------
    # CLEAN + SORT
    # -----------------------------
    winter_months = sorted(set(winter_months))
    monsoon_months = sorted(set(monsoon_months))

    # -----------------------------
    # PRE / POST MONSOON (CIRCULAR LOGIC)
    # -----------------------------
    pre_monsoon = []
    post_monsoon = []

    if winter_months and monsoon_months:

        w_end = max(winter_months)
        m_start = min(monsoon_months)
        m_end = max(monsoon_months)
        w_start = min(winter_months)

        # helper for circular range
        def circular_range(start, end):
            months = []
            m = start
            while m != end:
                months.append(m)
                m = m + 1 if m < 12 else 1
            return months

        # Pre: winter end → monsoon start
        pre_monsoon = circular_range(w_end + 1 if w_end < 12 else 1, m_start)

        # Post: monsoon end → winter start
        post_monsoon = circular_range(m_end + 1 if m_end < 12 else 1, w_start)

    # -----------------------------
    # INITIAL ASSIGNMENT
    # -----------------------------
    assigned = set(winter_months + monsoon_months + pre_monsoon + post_monsoon)

    # -----------------------------
    # FILL MISSING MONTHS (CRITICAL FIX)
    # -----------------------------
    missing = sorted(all_months - assigned)

    for m in missing:
        # assign based on proximity
        if winter_months:
            dist_w = min(abs(m - wm) for wm in winter_months)
        else:
            dist_w = np.inf

        if monsoon_months:
            dist_m = min(abs(m - mm) for mm in monsoon_months)
        else:
            dist_m = np.inf

        if dist_w < dist_m:
            winter_months.append(m)
        else:
            monsoon_months.append(m)

    # -----------------------------
    # FINAL SORT + UNIQUE
    # -----------------------------
    seasons = {
        "Winter": sorted(set(winter_months)),
        "Monsoon": sorted(set(monsoon_months)),
        "Pre-Monsoon": sorted(set(pre_monsoon)),
        "Post-Monsoon": sorted(set(post_monsoon)),
    }

    return seasons, monthly
