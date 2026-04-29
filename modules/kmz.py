import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import zipfile

import geopandas as gpd
import contextily as ctx


def run_kmz_generation(df, kmz_requests, lat, lon):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    if 'WD (degree)' not in df.columns or 'WS (m/s)' not in df.columns:
        return results

    # -----------------------------
    # 🌍 Prepare map base (ONCE)
    # -----------------------------
    gdf = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([lon], [lat]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    buffer_m = 5000  # 5 km buffer

    # -----------------------------
    # 🎨 Frame generator (MAP BASED)
    # -----------------------------
    def generate_frame(row, pollutant, ts):

        wd = row['WD (degree)']
        ws = row['WS (m/s)']
        val = row[pollutant]

        if pd.isna(wd) or pd.isna(ws) or pd.isna(val):
            return None

        fig, ax = plt.subplots(figsize=(6,6))

        # Map extent
        x, y = gdf.geometry.x.iloc[0], gdf.geometry.y.iloc[0]

        ax.set_xlim(x - buffer_m, x + buffer_m)
        ax.set_ylim(y - buffer_m, y + buffer_m)

        # Add basemap
        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
        except:
            pass  # prevents crash if tiles fail

        # Wind vector
        dx = ws * np.cos(np.deg2rad(wd)) * 200
        dy = ws * np.sin(np.deg2rad(wd)) * 200

        ax.arrow(
            x, y, dx, dy,
            head_width=300,
            head_length=500,
            fc='blue',
            ec='blue',
            linewidth=1 + ws/2
        )

        # Pollutant circle
        color = 'green' if val < 60 else 'red'
        circle = plt.Circle(
            (x, y),
            val * 10,
            color=color,
            alpha=0.3
        )
        ax.add_patch(circle)

        # Title + annotation
        ax.set_title(f"{pollutant}\n{ts.strftime('%Y-%m-%d %H:%M')}")
        ax.text(
            0.5, -0.1,
            f"{pollutant}: {val:.1f} | WS: {ws:.1f} m/s",
            transform=ax.transAxes,
            ha='center'
        )

        ax.set_axis_off()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
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
                # 🔁 Frames + SINGLE timeline
                # -----------------------------
                for j, (ts, row) in enumerate(sub.iterrows()):

                    frame = generate_frame(row, pol, ts)
                    if frame is None:
                        continue

                    img_name = f"images/frame_{j:05d}.png"
                    kmz.writestr(img_name, frame)

                    timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S")

                    kml += [
                        '<GroundOverlay>',
                        f'<name>{ts}</name>',
                        f'<TimeStamp><when>{timestamp}</when></TimeStamp>',  # ✅ FIXED
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

            fname = f"kmz/request_{i+1}/{pol.replace(' ','_')}.kmz"
            results[fname] = kmz_buffer.getvalue()

    return results
