import pandas as pd

def check_data_quality(df):
    cols_to_check = [
        'PM2.5 (ug/m3)','PM10 (ug/m3)','NO (ug/m3)','NO2 (ug/m3)',
        'NOx (ppb)','SO2 (ug/m3)','CO (mg/m3)','Ozone (ug/m3)',
        'Benzene (ug/m3)','Toluene (ug/m3)','Eth-Benzene (ug/m3)',
        'MP-Xylene (ug/m3)','O-Xylene (ug/m3)','RH (%)','WS (m/s)',
        'WD (degree)','SR (W/mt2)',"AT (C)"
    ]

    # Ensure numeric coercion
    existing_cols = [col for col in cols_to_check if col in df.columns]
    df[existing_cols] = df[existing_cols].apply(pd.to_numeric, errors='coerce')

    summary = {}
    valid_columns = []
    dropped_columns = []

    for col in existing_cols:
        if col in df.columns:
            total = len(df[col])
            nan_count = df[col].isna().sum()
            percent = (nan_count / total) * 100

            summary[col] = percent

            if percent > 30:
                dropped_columns.append(col)
            else:
                valid_columns.append(col)

    conv_summary = pd.DataFrame.from_dict(
        summary, orient='index', columns=['% Missing']
    ).sort_values('% Missing', ascending=False)

    return conv_summary, valid_columns, dropped_columns
