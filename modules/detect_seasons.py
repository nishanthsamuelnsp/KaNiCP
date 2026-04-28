import numpy as np
import pandas as pd

def detect_seasons(df):

    df = df.copy()

    # Monthly aggregation
    monthly = df.groupby([df.index.year, df.index.month]).mean()
    monthly = monthly.groupby(level=1).mean()
    months = np.arange(1, 13)

    # --- Identify columns safely ---
    temp_col = None
    rh_col = None

    for col in df.columns:
        if "AT" in col:
            temp_col = col
        if "RH" in col:
            rh_col = col

    # --- WINTER detection (lowest temp period) ---
    winter_months = []
    if temp_col:
        temp_series = monthly[temp_col]

        # Find coldest months (bottom 25%)
        threshold = temp_series.quantile(0.25)
        winter_months = temp_series[temp_series <= threshold].index.tolist()

    # --- MONSOON detection ---
    monsoon_months = []

    if rh_col:
        rh_series = monthly[rh_col]

        # High humidity → monsoon
        threshold = rh_series.quantile(0.75)
        monsoon_months = rh_series[rh_series >= threshold].index.tolist()

    else:
        # Fallback (India standard)
        monsoon_months = [6, 7, 8, 9]

    # --- PRE & POST MONSOON ---
    pre_monsoon = []
    post_monsoon = []

    if winter_months and monsoon_months:
        w_end = max(winter_months)
        m_start = min(monsoon_months)
        m_end = max(monsoon_months)

        # Pre-monsoon: between winter end and monsoon start
        pre_monsoon = list(range(w_end + 1, m_start))

        # Post-monsoon: after monsoon until winter
        post_monsoon = list(range(m_end + 1, min(winter_months)))

    # --- Remove very short seasons (<1 month) ---
    if len(pre_monsoon) < 1:
        pre_monsoon = []

    if len(post_monsoon) < 1:
        post_monsoon = []

    # --- Package results ---
    seasons = {
        "Winter": winter_months,
        "Monsoon": monsoon_months,
        "Pre-Monsoon": pre_monsoon,
        "Post-Monsoon": post_monsoon
    }

    return seasons, monthly
