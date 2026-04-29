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
    # 📍 LOCATION LABEL (fallback, no external API)
    # =========================================================
    def get_location_name(lat, lon):
        return f"Station ({lat:.2f}, {lon:.2f})"

    # =========================================================
    # 🎨 FRAME GENERATOR (ENHANCED INFO PANEL)
    # =========================================================
    def generate_frame(row, pollutant, ts):

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

        # =====================================================
        # 🌬 WIND VECTOR
        # =====================================================
        dx = ws * np.cos(np.deg2rad(wd))
        dy = ws * np.sin(np.deg2rad(wd))
        ax.arrow(0, 0, dx, dy, head_width=0.3, color="blue")

        # =====================================================
        # 🔵 POLLUTANT CIRCLE (SAFE SCALE)
        # =====================================================
        radius = np.clip(val / 100.0, 0.1, 2.5)
        color = "green" if val < 60 else "red"
        ax.add_patch(plt.Circle((0, 0), radius, color=color, alpha=0.4))

        # =====================================================
        # ⚖ COMPLIANCE
        # =====================================================
        limit = 60
        status = "SAFE" if val <= limit else "EXCEED"

        # =====================================================
        # 📍 LOCATION NAME
        # =====================================================
        location_name = get_location_name(lat, lon)

        # =====================================================
        # 🧾 FULL INFO PANEL (KEY UPGRADE)
        # =====================================================
        info_text = (
            f"🕒 Time: {ts.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📍 Location: {location_name}\n"
            f"🌍 Coordinates: {lat:.3f}, {lon:.3f}\n"
            f"🌬 Wind Speed: {ws:.1f} m/s | Dir: {wd:.0f}°\n"
            f"🧪 {pollutant}: {val:.1f} µg/m³\n"
            f"⚖ Limit: {limit} µg/m³\n"
            f"🚦 Status: {status}"
        )

        ax.text(
            0.02, 0.98,
            info_text,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8.5,
            bbox=dict(
                facecolor="white",
                alpha=0.85,
                edgecolor="black",
                boxstyle="round,pad=0.4"
            )
        )

        # =====================================================
        # 📦 EXPORT JPEG
        # =====================================================
        buf = io.BytesIO()
        plt.savefig(buf, format="jpg", dpi=120, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

    # =========================================================
    # 🚀 MAIN KMZ LOOP (UNCHANGED STRUCTURE)
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

            safe_pol = re.sub(r'[^A-Za-z0-9_]+', '_', pol)

            frames = []

            # =====================================================
            # 🎞 GENERATE FRAMES
            # =====================================================
            for ts, row in sub.iterrows():

                frame = generate_frame(row, pol, ts)
                if frame:
                    frames.append((ts, frame))

            if not frames:
                continue

            # =====================================================
            # 🌍 KMZ BUILD
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

            with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as kmz:

                for j, (ts, frame) in enumerate(frames):

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
