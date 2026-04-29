import numpy as np
import pandas as pd

def detect_seasons(df):

    df = df.copy()

    # -----------------------------
    # Monthly aggregation
    # -----------------------------
    monthly = df.groupby([df.index.year, df.index.month]).mean(numeric_only=True)
    monthly = monthly.groupby(level=1).mean()

    months_all = list(range(1, 13))

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
    winter = set(winter)
    monsoon = set(monsoon)

    # Monsoon priority
    winter = winter - monsoon

    # -----------------------------
    # LABEL ARRAY (1–12)
    # -----------------------------
    labels = {m: None for m in months_all}

    for m in winter:
        labels[m] = "Winter"

    for m in monsoon:
        labels[m] = "Monsoon"

    # -----------------------------
    # FILL GAPS SEQUENTIALLY
    # -----------------------------
    current_mode = None

    for m in months_all:

        if labels[m] is not None:
            current_mode = labels[m]
            continue

        # Decide based on upcoming known season
        future = [labels[x] for x in months_all[m:] if labels[x] is not None]

        next_known = future[0] if future else None

        if next_known == "Monsoon":
            labels[m] = "Pre-Monsoon"
        elif next_known == "Winter":
            labels[m] = "Post-Monsoon"
        else:
            # fallback
            labels[m] = "Post-Monsoon"

    # -----------------------------
    # GROUP INTO SEASONS
    # -----------------------------
    seasons = {
        "Winter": [],
        "Monsoon": [],
        "Pre-Monsoon": [],
        "Post-Monsoon": []
    }

    for m, s in labels.items():
        seasons[s].append(m)

    # -----------------------------
    # HANDLE SMALL SEASONS (<1 month)
    # -----------------------------
    def merge_if_small(season_name):
        if len(seasons[season_name]) < 1:
            return

        if season_name == "Pre-Monsoon":
            target = "Monsoon"
        elif season_name == "Post-Monsoon":
            target = "Winter"
        else:
            return

        # size-based override
        if len(seasons["Winter"]) < len(seasons["Monsoon"]):
            target = "Winter"
        elif len(seasons["Monsoon"]) < len(seasons["Winter"]):
            target = "Monsoon"

        # tie → later season preference
        elif season_name == "Post-Monsoon":
            target = "Winter"
        else:
            target = "Monsoon"

        seasons[target].extend(seasons[season_name])
        seasons[season_name] = []

    merge_if_small("Pre-Monsoon")
    merge_if_small("Post-Monsoon")

    # -----------------------------
    # FINAL CLEAN
    # -----------------------------
    for k in seasons:
        seasons[k] = sorted(set(seasons[k]))

    return seasons, monthly
