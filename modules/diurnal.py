import matplotlib.pyplot as plt
import io

def run_diurnal_analysis(df, valid_columns):

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

    # Select only valid pollutants
    selected_items = {
        k: v for k, v in pollutant_map.items() if k in valid_columns
    }

    results = {}

    df = df.copy()
    df['hour'] = df.index.hour

    for full_name, short_name in selected_items.items():

        diurnal = df.groupby('hour')[full_name]
        mean = diurnal.mean().loc[5:19]
        std = diurnal.std().loc[5:19]

        fig, ax = plt.subplots(figsize=(6,4))
        ax.errorbar(mean.index, mean.values, yerr=std.values, fmt='-o', capsize=4)
        ax.set_title(f"Diurnal Variation of {full_name} (mean ± std)")
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel(f"{full_name} concentration")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_xticks(range(5, 20))

        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)

        filename = f"diurnal_analysis/diurnal_{short_name}.png"
        results[filename] = img_buffer.getvalue()

        plt.close(fig)

    return results
