import matplotlib.pyplot as plt
import io
from windrose import WindroseAxes
import matplotlib.cm as cm

def run_roses_analysis(df, valid_columns):

    results = {}

    df = df.copy()

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

    # ------------------------
    # 🌬️ Wind Rose
    # ------------------------
    if 'WD (degree)' in df.columns and 'WS (m/s)' in df.columns:

        wind_df = df[['WD (degree)', 'WS (m/s)']].dropna()

        if not wind_df.empty:

            fig = plt.figure(figsize=(6,6))
            ax = WindroseAxes(fig, [0.1,0.1,0.8,0.8])
            fig.add_axes(ax)

            ax.bar(
                wind_df['WD (degree)'],
                wind_df['WS (m/s)'],
                normed=True,
                opening=0.8,
                edgecolor='white',
                cmap=cm.viridis
            )

            ax.set_legend(title="Wind Speed (m/s)")
            plt.title("Wind Rose")

            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            img_buffer.seek(0)

            results["roses/wind_rose.png"] = img_buffer.getvalue()

            plt.close(fig)

    # ------------------------
    # 🌫️ Pollution Roses
    # ------------------------
    selected = {k: v for k, v in pollutant_map.items() if k in valid_columns}

    for full_name, short_name in selected.items():

        if full_name not in df.columns:
            continue

        if 'WD (degree)' not in df.columns:
            continue

        rose_df = df[['WD (degree)', full_name]].dropna()

        if rose_df.empty:
            continue

        fig = plt.figure(figsize=(6,6))
        ax = WindroseAxes(fig, [0.1,0.1,0.8,0.8])
        fig.add_axes(ax)

        ax.bar(
            rose_df['WD (degree)'],
            rose_df[full_name],
            normed=True,
            opening=0.8,
            edgecolor='white',
            cmap=cm.viridis
        )

        ax.set_legend(title=full_name)
        ax.patch.set_alpha(0.0)
        plt.title(f"Pollution Rose: {full_name}")

        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)

        results[f"roses/pollution_rose_{short_name}.png"] = img_buffer.getvalue()

        plt.close(fig)

    return results
