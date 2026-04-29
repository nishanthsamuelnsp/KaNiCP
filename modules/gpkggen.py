import os
import io
import zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

import geopandas as gpd
from shapely.geometry import Point


def run_kmz_generation(df, kmz_requests, lat, lon):

    results = {}

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    # =========================================================
    # 🟢 STEP 1 — GPKG EXPORT (once per full dataset)
    # =========================================================
    def export_gpkg(df):
        gdf = gpd.GeoDataFrame(
            df.reset_index(),
            geometry=[Point(lon, lat)] * len(df),
            crs="EPSG:4326"
        )

        buf = io.BytesIO()
        gdf.to_file("temp.gpkg", layer="pollution", driver="GPKG")

        with open("temp.gpkg", "rb") as f:
            return f.read()

    gpkg_bytes = export_gpkg(df)
    results["pollution.gpkg"] = gpkg_bytes

    # =========================================================
    # 🎨 FRAME GENERATOR
    # =========================================================
    def generate_frame(row, pollutant):

        wd = row['WD (degree)']
        ws = row['WS (m/s)']
        val = row[pollutant]

        if pd.isna(wd) or pd.isna(ws) or pd.isna(val):
            return None

        fig, ax = plt.subplots(figsize=(5, 5))

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
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight", transparent=True)
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

    # =========================================================
    # 🚀 KMZ + GIF PER REQUEST
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

            # -----------------------------
            # 🎞 CREATE FRAMES
            # -----------------------------
            for _, row in sub.iterrows():
                frame = generate_frame(row, pol)
                if frame:
                    frames.append(Image.open(io.BytesIO(frame)).convert("RGBA"))

            if not frames:
                continue

            # -----------------------------
            # 🎞 CREATE GIF
            # -----------------------------
            gif_buf = io.BytesIO()
            frames[0].save(
                gif_buf,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=300,
                loop=0,
                optimize=True
            )
            gif_buf.seek(0)

            gif_name = f"{safe_pol}.gif"

            # -----------------------------
            # 🌍 CREATE KMZ (GIF OVERLAY)
            # -----------------------------
            kmz_buf = io.BytesIO()

            kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>{pol} Animation</name>

    <GroundOverlay>
        <name>{pol}</name>
        <Icon>
            <href>{gif_name}</href>
        </Icon>
        <LatLonBox>
            <north>{lat + 0.05}</north>
            <south>{lat - 0.05}</south>
            <east>{lon + 0.05}</east>
            <west>{lon - 0.05}</west>
        </LatLonBox>
    </GroundOverlay>

</Document>
</kml>
"""

            with zipfile.ZipFile(kmz_buf, "w", zipfile.ZIP_DEFLATED) as kmz:
                kmz.writestr("doc.kml", kml)
                kmz.writestr(gif_name, gif_buf.read())

            kmz_buf.seek(0)

            fname = f"kmz/request_{i+1}/{safe_pol}.kmz"
            results[fname] = kmz_buf.getvalue()

    return results
