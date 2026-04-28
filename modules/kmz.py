import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import zipfile


def run_kmz_generation(df, kmz_requests, lat, lon):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    required_cols = ['WD (degree)', 'WS (m/s)']
    for col in required_cols:
        if col not in df.columns:
            return results

    # -----------------------------
    # Frame generator
    # -----------------------------
    def generate_frame(row, pollutant):

        fig, ax = plt.subplots(figsize=(5,5))

        wd = row['WD (degree)']
        ws = row['WS (m/s)']
        val = row[pollutant]

        if pd.isna(wd) or pd.isna(ws) or pd.isna(val):
            plt.close(fig)
            return None

        dx = ws * np.cos(np.deg2rad(wd))
        dy = ws * np.sin(np.deg2rad(wd))

        ax.arrow(0, 0, dx, dy,
                 head_width=0.3,
                 head_length=0.4,
                 fc='blue',
                 ec='blue',
                 linewidth=1 + ws/2)

        color = 'green' if val < 60 else 'red'
        circle = plt.Circle((0, 0), val * 0.02, color=color, alpha=0.4)
        ax.add_patch(circle)

        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
        ax.set_axis_off()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

    # -----------------------------
    # Main KMZ loop
    # -----------------------------
    for i, req in enumerate(kmz_requests):

        year = req["year"]
        month = req["month"]
        start_day = req["start_day"]
        end_day = req["end_day"]
        pollutants = req["pollutants"]

        mask = (
            (df.index.year == year) &
            (df.index.month == month) &
            (df.index.day >= start_day) &
            (df.index.day <= end_day)
        )

        sub = df.loc[mask].copy()

        if sub.empty:
            continue

        for pol in pollutants:

            if pol not in sub.columns:
                continue

            kmz_buffer = io.BytesIO()

            with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as kmz:

                kml = [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<kml xmlns="http://www.opengis.net/kml/2.2">',
                    '<Document>',
                    f'<name>{pol} Dynamic Rose</name>'
                ]

                north, south = lat + 0.05, lat - 0.05
                east, west = lon + 0.05, lon - 0.05

                # -----------------------------
                # Generate frames + KML entries
                # -----------------------------
                for j, (ts, row) in enumerate(sub.iterrows()):

                    frame = generate_frame(row, pol)
                    if frame is None:
                        continue

                    img_name = f"images/frame_{j:05d}.png"

                    # Save image into KMZ
                    kmz.writestr(img_name, frame)

                    start = ts.strftime("%Y-%m-%dT%H:%M:%S")
                    end = (ts + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")

                    kml += [
                        '<GroundOverlay>',
                        f'<name>{ts}</name>',
                        f'<TimeSpan><begin>{start}</begin><end>{end}</end></TimeSpan>',
                        '<Icon>',
                        f'<href>{img_name}</href>',
                        '</Icon>',
                        '<LatLonBox>',
                        f'<north>{north}</north>',
                        f'<south>{south}</south>',
                        f'<east>{east}</east>',
                        f'<west>{west}</west>',
                        '</LatLonBox>',
                        '</GroundOverlay>'
                    ]

                kml += ['</Document>', '</kml>']

                kmz.writestr("doc.kml", "\n".join(kml))

            kmz_buffer.seek(0)

            # store as separate KMZ per pollutant
            fname = f"kmz/request_{i+1}/{pol.replace(' ','_')}.kmz"
            results[fname] = kmz_buffer.getvalue()

    return results
