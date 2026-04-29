import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import zipfile


def run_kmz_generation(df, kmz_requests, lat, lon):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df.sort_index()

    required_cols = ['WD (degree)', 'WS (m/s)']
    for col in required_cols:
        if col not in df.columns:
            return results

    # -----------------------------
    # Frame generator (UNCHANGED VISUAL STYLE)
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

        ax.arrow(
            0, 0, dx, dy,
            head_width=0.3,
            head_length=0.4,
            fc='blue',
            ec='blue',
            linewidth=1 + ws/2
        )

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
    # KMZ LOOP
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

        # 👉 IMPORTANT: sort time (prevents timeline bugs)
        sub = sub.sort_index()

        for pol in pollutants:

            if pol not in sub.columns:
                continue

            kmz_buffer = io.BytesIO()

            with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as kmz:

                # -----------------------------
                # KML HEADER (FIXED)
                # -----------------------------
                kml = [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<kml xmlns="http://www.opengis.net/kml/2.2">',
                    '<Document>',
                    f'<name>{pol} Dynamic Rose</name>',
                    '<open>1</open>'
                ]

                north, south = lat + 0.05, lat - 0.05
                east, west = lon + 0.05, lon - 0.05

                frame_count = 0

                # -----------------------------
                # FRAME LOOP
                # -----------------------------
                for j, (ts, row) in enumerate(sub.iterrows()):

                    frame = generate_frame(row, pol)
                    if frame is None:
                        continue

                    img_name = f"images/frame_{frame_count:05d}.png"

                    kmz.writestr(img_name, frame)

                    # ✅ STRICT ISO FORMAT (CRITICAL FIX)
                    start = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
                    end = (ts + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

                    # ✅ CLEAN XML BLOCK (prevents broken timeline)
                    kml.append(f"""
                    <GroundOverlay>
                        <name>{ts}</name>
                        <TimeSpan>
                            <begin>{start}</begin>
                            <end>{end}</end>
                        </TimeSpan>
                        <Icon>
                            <href>{img_name}</href>
                        </Icon>
                        <LatLonBox>
                            <north>{north}</north>
                            <south>{south}</south>
                            <east>{east}</east>
                            <west>{west}</west>
                        </LatLonBox>
                    </GroundOverlay>
                    """)

                    frame_count += 1

                # -----------------------------
                # CLOSE KML
                # -----------------------------
                kml.append('</Document>')
                kml.append('</kml>')

                kmz.writestr("doc.kml", "\n".join(kml))

            kmz_buffer.seek(0)

            fname = f"kmz/request_{i+1}/{pol.replace(' ','_')}.kmz"
            results[fname] = kmz_buffer.getvalue()

    return results
