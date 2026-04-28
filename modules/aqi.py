import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io

def run_aqi_analysis(df):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    # -----------------------------
    # CPCB breakpoints
    # -----------------------------
    breakpoints = {
        'PM2.5 (ug/m3)': [(0,30,0,50),(31,60,51,100),(61,90,101,200),(91,120,201,300),(121,250,301,400),(251,500,401,500)],
        'PM10 (ug/m3)': [(0,50,0,50),(51,100,51,100),(101,250,101,200),(251,350,201,300),(351,430,301,400),(431,500,401,500)],
        'NO2 (ug/m3)': [(0,40,0,50),(41,80,51,100),(81,180,101,200),(181,280,201,300),(281,400,301,400),(401,500,401,500)],
        'SO2 (ug/m3)': [(0,40,0,50),(41,80,51,100),(81,380,101,200),(381,800,201,300),(801,1600,301,400),(1601,2000,401,500)],
        'CO (mg/m3)': [(0,1,0,50),(1.1,2,51,100),(2.1,10,101,200),(10.1,17,201,300),(17.1,34,301,400),(34.1,50,401,500)],
        'Ozone (ug/m3)': [(0,50,0,50),(51,100,51,100),(101,168,101,200),(169,208,201,300),(209,748,301,400),(749,1000,401,500)]
    }

    pollutant_cols = list(breakpoints.keys())

    # Convert to numeric safely
    for col in pollutant_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # -----------------------------
    # AQI functions
    # -----------------------------
    def compute_subindex(conc, pollutant):
        for Clow, Chigh, Ilow, Ihigh in breakpoints.get(pollutant, []):
            if Clow <= conc <= Chigh:
                return ((Ihigh-Ilow)/(Chigh-Clow))*(conc-Clow)+Ilow
        return np.nan

    def compute_aqi(row):
        subindices = []
        for pol in pollutant_cols:
            if pol in row and not pd.isna(row[pol]):
                subindices.append(compute_subindex(row[pol], pol))
        return np.nanmax(subindices) if subindices else np.nan

    # -----------------------------
    # AQI calculation
    # -----------------------------
    df['AQI'] = df.apply(compute_aqi, axis=1)

    daily_means = df.resample('D').mean(numeric_only=True)
    daily_aqi = daily_means['AQI']

    # -----------------------------
    # Save AQI Excel (in memory)
    # -----------------------------
    excel_buffer = io.BytesIO()
    daily_aqi.to_frame().to_excel(excel_buffer)
    results["aqi/daily_aqi.xlsx"] = excel_buffer.getvalue()

    # -----------------------------
    # Heatmap
    # -----------------------------
    heatmap_data = daily_aqi.groupby([
        daily_aqi.index.month.astype(int),
        daily_aqi.index.day.astype(int)
    ]).mean().unstack(level=0)

    heatmap_data = heatmap_data.reindex(range(1,32))
    heatmap_data = heatmap_data.reindex(columns=range(1,13))

    fig, ax = plt.subplots(figsize=(8,12))
    sns.heatmap(
        heatmap_data,
        cmap="RdYlGn_r",
        linewidths=0.5,
        linecolor='white',
        cbar_kws={'label':'AQI'},
        square=True,
        ax=ax
    )

    ax.set_title("Daily AQI Heatmap")
    ax.set_xlabel("Month")
    ax.set_ylabel("Day")

    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)

    results["aqi/aqi_heatmap.png"] = img_buffer.getvalue()

    plt.close(fig)

    # -----------------------------
    # Compliance Check
    # -----------------------------
    pollutants = pollutant_cols

    for col in pollutants:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['SO2_24h'] = df['SO2 (ug/m3)'].rolling(24, min_periods=1).mean() if 'SO2 (ug/m3)' in df.columns else np.nan
    df['PM2.5_24h'] = df['PM2.5 (ug/m3)'].rolling(24, min_periods=1).mean() if 'PM2.5 (ug/m3)' in df.columns else np.nan
    df['PM10_24h'] = df['PM10 (ug/m3)'].rolling(24, min_periods=1).mean() if 'PM10 (ug/m3)' in df.columns else np.nan
    df['NO2_24h'] = df['NO2 (ug/m3)'].rolling(24, min_periods=1).mean() if 'NO2 (ug/m3)' in df.columns else np.nan
    df['O3_8h'] = df['Ozone (ug/m3)'].rolling(8, min_periods=1).mean() if 'Ozone (ug/m3)' in df.columns else np.nan
    df['CO_8h'] = df['CO (mg/m3)'].rolling(8, min_periods=1).mean() if 'CO (mg/m3)' in df.columns else np.nan

    annual_means = df.resample('YE').mean(numeric_only=True)

    standards = {
        'SO2_24h': 80, 'SO2_Annual': 50,
        'NO2_24h': 80, 'NO2_Annual': 40,
        'PM2.5_24h': 60, 'PM2.5_Annual': 40,
        'PM10_24h': 100, 'PM10_Annual': 60,
        'O3_8h': 100, 'CO_8h': 2
    }

    def compliance_check(df, annual_means):
        out = {}

        for key, limit in standards.items():

            if "Annual" in key:
                base = key.replace("_Annual","")
                col1 = base + " (ug/m3)"
                col2 = base + " (mg/m3)"

                if col1 in annual_means:
                    series = annual_means[col1].dropna()
                elif col2 in annual_means:
                    series = annual_means[col2].dropna()
                else:
                    continue
            else:
                if key in df:
                    series = df[key].dropna()
                else:
                    continue

            if len(series) == 0:
                continue

            pct_within = (series <= limit).mean() * 100

            out[key] = {
                "Average": series.mean(),
                "% Within Limit": pct_within
            }

        return pd.DataFrame(out).T

    compliance_df = compliance_check(df, annual_means)

    comp_buffer = io.BytesIO()
    compliance_df.to_excel(comp_buffer)

    results["aqi/compliance.xlsx"] = comp_buffer.getvalue()

    return results
