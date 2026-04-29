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

        ax.arrow(cx, cy, dx, dy, head_width=0.3,
                 head_length=0.4, fc='blue', ec='blue')

        color = 'green' if val < 60 else 'red'
        ax.add_patch(plt.Circle((cx, cy), val * 0.02, color=color, alpha=0.4))

        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_axis_off()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=90, transparent=True, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

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

                kml = [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<kml xmlns="http://www.opengis.net/kml/2.2" '
                    'xmlns:gx="http://www.google.com/kml/ext/2.2">',
                    '<Document>',
                    f'<name>{pol} Animation</name>'
                ]

                north, south = lat + 0.01, lat - 0.01
                east, west = lon + 0.01, lon - 0.01

                frame_ids = []

                # -----------------------
                # CREATE ALL FRAMES (hidden)
                # -----------------------
                for j, (ts, row) in enumerate(sub.iterrows()):

                    frame = generate_frame(row, pol)
                    if frame is None:
                        continue

                    img_name = f"images/frame_{j:05d}.png"
                    kmz.writestr(img_name, frame)

                    frame_id = f"frame_{j}"
                    frame_ids.append(frame_id)

                    kml += [
                        f'<GroundOverlay id="{frame_id}">',
                        '<visibility>0</visibility>',
                        '<Icon>',
                        f'<href>{img_name}</href>',
                        '</Icon>',
                        '<LatLonBox>',
                        f'<north>{north}</north>',
                        f'<south>{south}</south>',
                        f'<east>{east}</east>',
                        f'<west>{west}</west>',
                        '</LatLonBox>',
                        '</GroundOverlay>',
                    ]

                # -----------------------
                # TOUR (VISIBILITY SWITCH)
                # -----------------------
                kml += [
                    '<gx:Tour>',
                    '<name>play</name>',
                    '<gx:Playlist>'
                ]

                for j in range(len(frame_ids)):

                    kml += [
                        '<gx:AnimatedUpdate>',
                        '<gx:duration>0.2</gx:duration>',
                        '<Update>'
                    ]

                    # turn ALL off
                    for fid in frame_ids:
                        kml += [
                            '<Change>',
                            f'<GroundOverlay targetId="{fid}">',
                            '<visibility>0</visibility>',
                            '</GroundOverlay>',
                            '</Change>'
                        ]

                    # turn current ON
                    kml += [
                        '<Change>',
                        f'<GroundOverlay targetId="{frame_ids[j]}">',
                        '<visibility>1</visibility>',
                        '</GroundOverlay>',
                        '</Change>',
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
