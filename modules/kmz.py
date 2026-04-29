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
    # 🎨 FRAME GENERATOR
    # -----------------------------
    def generate_frame(row, pollutant):

        wd = row['WD (degree)']
        ws = row['WS (m/s)']
        val = row[pollutant]

        if pd.isna(wd) or pd.isna(ws) or pd.isna(val):
            return None

        fig, ax = plt.subplots(figsize=(4, 4))

        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

        cx, cy = 0, 0

        dx = ws * np.cos(np.deg2rad(wd))
        dy = ws * np.sin(np.deg2rad(wd))

        ax.arrow(
            cx, cy, dx, dy,
            head_width=0.3,
            head_length=0.4,
            fc='blue',
            ec='blue',
            linewidth=1 + ws / 2
        )

        color = 'green' if val < 60 else 'red'
        circle = plt.Circle((cx, cy), val * 0.02, color=color, alpha=0.5)
        ax.add_patch(circle)

        ax.text(
            0.5, -0.15,
            f"{pollutant}\n{val:.1f} µg/m³ | WS: {ws:.1f}",
            transform=ax.transAxes,
            ha='center',
            fontsize=9,
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none')
        )

        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_axis_off()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=90, transparent=True, bbox_inches='tight')
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

        if len(sub) > 300:
            sub = sub.iloc[::3]

        for pol in pollutants:

            if pol not in sub.columns:
                continue

            safe_pol = re.sub(r'[^A-Za-z0-9_]+', '_', pol)

            kmz_buffer = io.BytesIO()

            with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as kmz:

                # -----------------------------
                # STORE FRAMES
                # -----------------------------
                frame_files = []

                for j, (ts, row) in enumerate(sub.iterrows()):

                    frame = generate_frame(row, pol)
                    if frame is None:
                        continue

                    img_name = f"images/frame_{j:05d}.png"
                    kmz.writestr(img_name, frame)

                    frame_files.append((ts, img_name))

                # -----------------------------
                # KML BASE
                # -----------------------------
                kml = [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<kml xmlns="http://www.opengis.net/kml/2.2" '
                    'xmlns:gx="http://www.google.com/kml/ext/2.2">',
                    '<Document>',
                    f'<name>{pol} Animated KMZ</name>'
                ]

                # -----------------------------
                # SINGLE OVERLAY
                # -----------------------------
                first_img = frame_files[0][1]

                kml += [
                    '<GroundOverlay id="overlay">',
                    '<Icon>',
                    f'<href>{first_img}</href>',
                    '</Icon>',
                    '<LatLonBox>',
                    f'<north>{lat + 0.01}</north>',
                    f'<south>{lat - 0.01}</south>',
                    f'<east>{lon + 0.01}</east>',
                    f'<west>{lon - 0.01}</west>',
                    '</LatLonBox>',
                    '</GroundOverlay>',
                ]

                # -----------------------------
                # GX TOUR (THE MAGIC PART)
                # -----------------------------
                kml += [
                    '<gx:Tour>',
                    '<name>animation</name>',
                    '<gx:Playlist>'
                ]

                for ts, img in frame_files:

                    kml += [
                        '<gx:AnimatedUpdate>',
                        '<gx:duration>0.3</gx:duration>',
                        '<Update>',
                        '<IconStyle targetId="overlay">',
                        '<Icon>',
                        f'<href>{img}</href>',
                        '</Icon>',
                        '</IconStyle>',
                        '</Update>',
                        '</gx:AnimatedUpdate>'
                    ]

                kml += [
                    '</gx:Playlist>',
                    '</gx:Tour>',
                    '</Document>',
                    '</kml>'
                ]

                kmz.writestr("doc.kml", "\n".join(kml))

            kmz_buffer.seek(0)

            fname = f"kmz/request_{i+1}/{safe_pol}.kmz"
            results[fname] = kmz_buffer.getvalue()

    return results
