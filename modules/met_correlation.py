import matplotlib.pyplot as plt
import seaborn as sns
import io

def run_correlation_analysis(df, valid_columns):

    pollutant_map = {
        'PM2.5 (ug/m3)': 'PM2.5',
        'PM10 (ug/m3)': 'PM10',
        'NO (ug/m3)': 'NO',
        'NO2 (ug/m3)': 'NO2',
        'NOx (ppb)': 'NOx',
        'SO2 (ug/m3)': 'SO2',
        'CO (mg/m3)': 'CO',
        'Ozone (ug/m3)': 'Ozone',
        'Benzene (ug/m3)': 'Benzene',
        'Toluene (ug/m3)': 'Toluene',
        'Eth-Benzene (ug/m3)': 'Eth-Benzene',
        'MP-Xylene (ug/m3)': 'MP-Xylene',
        'O-Xylene (ug/m3)': 'O-Xylene'
    }

    # Possible meteorological parameters
    met_params_all = ['WS (m/s)', 'WD (degree)', 'RH (%)', 'AT (C)', 'SR (W/mt2)']

    # ✅ Filter pollutants (already validated)
    pollutants = [col for col in pollutant_map.keys() if col in valid_columns]

    # ✅ Dynamically detect available meteorological parameters
    met_params = [col for col in met_params_all if col in df.columns]

    results = {}

    # ⚠️ Guard condition
    if len(pollutants) == 0 or len(met_params) == 0:
        return results

    # Compute correlation
    corr_matrix = df[pollutants + met_params].corr().loc[pollutants, met_params]

    # Plot
    fig, ax = plt.subplots(figsize=(10,6))
    sns.heatmap(
        corr_matrix,
        annot=True,
        cmap='coolwarm',
        center=0,
        linewidths=0.5,
        cbar_kws={'label':'Correlation'},
        ax=ax
    )

    ax.set_title("Correlation Map: Pollutants vs Meteorological Parameters")
    ax.set_xlabel("Meteorological Parameters")
    ax.set_ylabel("Pollutants")

    # Save to memory
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)

    # ✅ No folder (as you requested)
    results["correlation_heatmap.png"] = img_buffer.getvalue()

    plt.close(fig)

    return results
