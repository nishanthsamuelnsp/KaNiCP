import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import zipfile
import re


def run_kmz_generation(df, kmz_requests, lat, lon):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    if 'WD (degree)' not in df.columns or 'WS (m/s)' not in df.columns:
        return results

    # -----------------------------
    # 🎨 Frame generator (TRANSPARENT)
    # -----------------------------
    def generate_frame(row, pollutant, ts):

        wd = row['WD (degree)']
        ws = row['WS (m/s)']
        val = row[pollutant]

        if pd.isna(wd) or pd.isna(ws) or pd.isna(val):
            return None

        fig, ax = plt.subplots(figsize=(4,4))

        # Transparent background
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

        # Center
        cx, cy = 0, 0

        # Wind vector
        dx = ws * np.cos(np.deg2rad(wd))
        dy = ws * np.sin(np.deg2rad(wd))

        ax.arrow(
            cx, cy, dx, dy,
            head_width=0.3,
            head_length=0.4,
            fc='blue',
            ec='blue',
            linewidth=1 + ws/2
        )

        # Pollutant circle
        color = 'green' if val < 60 else 'red'
        circle = plt.Circle((cx, cy), val * 0.02, color=color, alpha=0.3)
        ax.add_patch(circle)

        # Text overlay
        ax.text(
            0.5, -0.15,
            f"{pollutant}\n{val:.1f} µg/m³ | WS: {ws:.1f} m/s",
            transform=ax.transAxes,
            ha='center',
            fontsize=9,
            color='black',
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none')
        )

        # Limits
        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_axis_off()

        buf = io.BytesIO()
        plt.savefig(
            buf,
            format='png',
            dpi=80,
            bbox_inches='tight',
            transparent=True   # 🔥 KEY
        )
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

    # -----------------------------
    # 🚀 KMZ GENERATION
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

        sub = df.loc[mask]

        if sub.empty:
            continue

        # 🔥 Frame reduction safeguard
        if len(sub) > 300:
            sub = sub.iloc[::3]

        for pol in pollutants:

            if pol not in sub.columns:
                continue

            # Safe filename
            safe_pol = re.sub(r'[^A-Za-z0-9_]+', '_', pol)

            kmz_buffer = io.BytesIO()

            with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as kmz:

                kml = [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<kml xmlns="http://www.opengis.net/kml/2.2">',
                    '<Document>',
                    f'<name>{pol} Dynamic Rose</name>'
                ]

                north, south = lat + 0.01, lat - 0.01
                east, west = lon + 0.01, lon - 0.01

                for j, (ts, row) in enumerate(sub.iterrows()):

                    frame = generate_frame(row, pol, ts)
                    if frame is None:
                        continue

                    img_name = f"images/frame_{j:05d}.png"
                    kmz.writestr(img_name, frame)

                    timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S")

                    start = ts.strftime("%Y-%m-%dT%H:%M:%S")
                    end = (ts + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
                    
                    kml += [
                        '<GroundOverlay>',
                        f'<name>{ts}</name>',
                        '<TimeSpan>',
                        f'<begin>{start}</begin>',
                        f'<end>{end}</end>',
                        '</TimeSpan>',
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

            fname = f"kmz/request_{i+1}/{safe_pol}.kmz"
            results[fname] = kmz_buffer.getvalue()

    return results
