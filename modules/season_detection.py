import numpy as np
import pandas as pd

def detect_seasons(df):

    df = df.copy()

    # -----------------------------
    # Monthly aggregation
    # -----------------------------
    monthly = df.groupby([df.index.year, df.index.month]).mean(numeric_only=True)
    monthly = monthly.groupby(level=1).mean()

    all_months = list(range(1, 13))

    # -----------------------------
    # Identify columns
    # -----------------------------
    temp_col = next((c for c in df.columns if "AT" in c), None)
    rh_col   = next((c for c in df.columns if "RH" in c), None)

    # -----------------------------
    # WINTER (lowest temp)
    # -----------------------------
    winter = []
    if temp_col and temp_col in monthly.columns:
        temp_series = monthly[temp_col].dropna()
        threshold = temp_series.quantile(0.25)
        winter = temp_series[temp_series <= threshold].index.tolist()

    # -----------------------------
    # MONSOON (high RH)
    # -----------------------------
    if rh_col and rh_col in monthly.columns:
        rh_series = monthly[rh_col].dropna()
        threshold = rh_series.quantile(0.75)
        monsoon = rh_series[rh_series >= threshold].index.tolist()
    else:
        monsoon = [6, 7, 8, 9]

    # -----------------------------
    # CLEAN
    # -----------------------------
    winter = sorted(set(winter))
    monsoon = sorted(set(monsoon))

    # -----------------------------
    # REMOVE OVERLAP (priority: monsoon > winter)
    # -----------------------------
    winter = [m for m in winter if m not in monsoon]

    # -----------------------------
    # REMAINING MONTHS
    # -----------------------------
    assigned = set(winter + monsoon)
    remaining = sorted(set(all_months) - assigned)

    # -----------------------------
    # SPLIT REMAINING INTO 2 BLOCKS
    # -----------------------------
    # First block = Pre-Monsoon (before monsoon start)
    # Second block = Post-Monsoon (after monsoon end)

    if monsoon:
        m_start = min(monsoon)
        m_end   = max(monsoon)
    else:
        m_start, m_end = 6, 9

    pre = [m for m in remaining if m < m_start]
    post = [m for m in remaining if m > m_end]

    # -----------------------------
    # HANDLE SMALL SEASONS (<1 month)
    # -----------------------------
    def merge_small(season, name):
        if len(season) < 1:
            return

        # Decide nearest: winter or monsoon
        # based on count (smaller gets priority)
        if len(winter) < len(monsoon):
            target = "winter"
        elif len(monsoon) < len(winter):
            target = "monsoon"
        else:
            # tie breaker → later season preference
            if name == "post":
                target = "winter"
            else:
                target = "monsoon"

        if target == "winter":
            winter.extend(season)
        else:
            monsoon.extend(season)

        season.clear()

    merge_small(pre, "pre")
    merge_small(post, "post")

    # -----------------------------
    # FINAL SORT + UNIQUE
    # -----------------------------
    seasons = {
        "Winter": sorted(set(winter)),
        "Monsoon": sorted(set(monsoon)),
        "Pre-Monsoon": sorted(set(pre)),
        "Post-Monsoon": sorted(set(post)),
    }

    return seasons, monthly
