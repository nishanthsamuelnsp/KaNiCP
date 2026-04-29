import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io

def run_aqi_analysis(df):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df.sort_index()

    # -----------------------------
    # CPCB breakpoints (only needed ones)
    # -----------------------------
    breakpoints = {
        'PM2.5 (ug/m3)': [(0,30,0,50),(31,60,51,100),(61,90,101,200),(91,120,201,300),(121,250,301,400),(251,500,401,500)],
        'PM10 (ug/m3)': [(0,50,0,50),(51,100,51,100),(101,250,101,200),(251,350,201,300),(351,430,301,400),(431,500,401,500)],
        'NO2 (ug/m3)': [(0,40,0,50),(41,80,51,100),(81,180,101,200),(181,280,201,300),(281,400,301,400),(401,500,401,500)],
        'SO2 (ug/m3)': [(0,40,0,50),(41,80,51,100),(81,380,101,200),(381,800,201,300),(801,1600,301,400),(1601,2000,401,500)],
        'CO (mg/m3)': [(0,1,0,50),(1.1,2,51,100),(2.1,10,101,200),(10.1,17,201,300),(17.1,34,301,400),(34.1,50,401,500)],
        'Ozone (ug/m3)': [(0,50,0,50),(51,100,51,100),(101,168,101,200),(169,208,201,300),(209,748,301,400),(749,1000,401,500)]
    }

    pollutant_cols = [col for col in breakpoints.keys() if col in df.columns]

    if not pollutant_cols:
        return results  # nothing to compute

    # -----------------------------
    # Convert to numeric
    # -----------------------------
    for col in pollutant_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # -----------------------------
    # AQI calculation
    # -----------------------------
    def compute_subindex(conc, pollutant):
        if pd.isna(conc):
            return np.nan
        for Clow, Chigh, Ilow, Ihigh in breakpoints[pollutant]:
            if Clow <= conc <= Chigh:
                return ((Ihigh-Ilow)/(Chigh-Clow))*(conc-Clow)+Ilow
        return np.nan

    def compute_aqi(row):
        vals = []
        for pol in pollutant_cols:
            val = compute_subindex(row[pol], pol)
            if not np.isnan(val):
                vals.append(val)
        return max(vals) if vals else np.nan

    df['AQI'] = df.apply(compute_aqi, axis=1)

    # -----------------------------
    # Daily AQI
    # -----------------------------
    daily_aqi = df['AQI'].resample('D').mean()

    if daily_aqi.dropna().empty:
        return results

    # -----------------------------
    # Heatmap data
    # -----------------------------
    heatmap_data = daily_aqi.groupby([
        daily_aqi.index.month,
        daily_aqi.index.day
    ]).mean().unstack(level=0)

    heatmap_data = heatmap_data.reindex(range(1,32))
    heatmap_data = heatmap_data.reindex(columns=range(1,13))

    if heatmap_data.dropna(how='all').empty:
        return results

    # -----------------------------
    # Plot heatmap
    # -----------------------------
    fig, ax = plt.subplots(figsize=(8,12))

    sns.heatmap(
        heatmap_data,
        cmap="RdYlGn_r",
        linewidths=0.5,
        linecolor='white',
        cbar_kws={'label':'AQI'},
        ax=ax
    )

    ax.set_title("Daily AQI Heatmap")
    ax.set_xlabel("Month")
    ax.set_ylabel("Day")

    # -----------------------------
    # Save image to memory
    # -----------------------------
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)

    results["aqi_heatmap.png"] = img_buffer.getvalue()

    plt.close(fig)

    return results
