import io
import zipfile
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import re


def run_kmz_generation(df, kmz_requests, lat, lon):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    # =========================================================
    # 🎨 FRAME GENERATOR (JPEG, NO TRANSPARENCY)
    # =========================================================
    def generate_frame(row, pollutant):

        wd = row['WD (degree)']
        ws = row['WS (m/s)']
        val = row[pollutant]

        if pd.isna(wd) or pd.isna(ws) or pd.isna(val):
            return None

        fig, ax = plt.subplots(figsize=(5, 5))

        ax.set_facecolor("white")
        fig.patch.set_facecolor("white")

        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_axis_off()

        # wind vector
        dx = ws * np.cos(np.deg2rad(wd))
        dy = ws * np.sin(np.deg2rad(wd))
        ax.arrow(0, 0, dx, dy, head_width=0.3, color="blue")

        # pollutant circle
        color = "green" if val < 60 else "red"
        circle = plt.Circle((0, 0), val * 0.02, color=color, alpha=0.4)
        ax.add_patch(circle)

        ax.text(
            0, -4,
            f"{pollutant}: {val:.1f}",
            ha="center"
        )

        buf = io.BytesIO()
        plt.savefig(buf, format="jpg", dpi=120, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

    # =========================================================
    # 🚀 MAIN LOOP
    # =========================================================
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

            # =====================================================
            # ✅ SAFE FILE NAME (FIX YOU REQUESTED)
            # =====================================================
            safe_pol = re.sub(r'[^A-Za-z0-9_]+', '_', pol)

            frames = []

            # =====================================================
            # 🎞 GENERATE FRAMES
            # =====================================================
            for _, row in sub.iterrows():
                frame = generate_frame(row, pol)
                if frame:
                    frames.append(frame)

            if not frames:
                continue

            # =====================================================
            # 🌍 BUILD KMZ
            # =====================================================
            kmz_buffer = io.BytesIO()

            kml = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<kml xmlns="http://www.opengis.net/kml/2.2">',
                '<Document>',
                f'<name>{pol} Timelapse</name>'
            ]

            north, south = lat + 0.05, lat - 0.05
            east, west = lon + 0.05, lon - 0.05

            # -----------------------------
            # BASEMAP
            # -----------------------------
            kml += [
                '<GroundOverlay>',
                '<name>Basemap</name>',
                '<Icon>',
                '<href>http://maps.google.com/mapfiles/kml/tile.jpg</href>',
                '</Icon>',
                '<LatLonBox>',
                f'<north>{north}</north>',
                f'<south>{south}</south>',
                f'<east>{east}</east>',
                f'<west>{west}</west>',
                '</LatLonBox>',
                '</GroundOverlay>'
            ]

            # -----------------------------
            # ZIP + FRAMES
            # -----------------------------
            with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as kmz:

                for j, (ts, frame) in enumerate(zip(sub.index, frames)):

                    img_name = f"images/frame_{j:04d}.jpg"
                    kmz.writestr(img_name, frame)

                    timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S")

                    kml += [
                        '<GroundOverlay>',
                        f'<name>{timestamp}</name>',
                        f'<TimeStamp><when>{timestamp}</when></TimeStamp>',
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
