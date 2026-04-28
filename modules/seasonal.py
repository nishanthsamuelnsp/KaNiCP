import matplotlib.pyplot as plt
import io
import pandas as pd

def run_seasonal_analysis(df, valid_columns, seasons):

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

    # Reverse mapping: month → season (from detected seasons)
    month_to_season = {}
    for season, months in seasons.items():
        for m in months:
            month_to_season[m] = season

    df = df.copy()
    df['Season'] = df.index.month.map(month_to_season)

    # Remove rows where season couldn't be assigned
    df = df.dropna(subset=['Season'])

    season_order = ['Winter','Pre-Monsoon','Monsoon','Post-Monsoon']
    df['Season'] = pd.Categorical(df['Season'], categories=season_order, ordered=True)

    # Select valid pollutants
    selected_items = {
        k: v for k, v in pollutant_map.items() if k in valid_columns
    }

    results = {}

    for full_name, short_name in selected_items.items():

        mean = df.groupby('Season')[full_name].mean()
        std = df.groupby('Season')[full_name].std()


        # Remove NaN seasons
        mean = mean.dropna()
        std = std.loc[mean.index]

        fig, ax = plt.subplots(figsize=(6,4))
        ax.bar(mean.index.astype(str), mean.values, yerr=std.values, capsize=4)

        ax.set_title(f"Seasonal Variation of {full_name}")
        ax.set_xlabel("Season")
        ax.set_ylabel(full_name)
        ax.grid(axis='y', linestyle='--', alpha=0.6)

        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)

        filename = f"seasonal_analysis/seasonal_{short_name}.png"
        results[filename] = img_buffer.getvalue()

        plt.close(fig)

    return results
