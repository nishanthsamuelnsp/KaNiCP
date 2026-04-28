import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if "results" not in st.session_state:
    st.session_state.results = {}

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "kmz_requests" not in st.session_state:
    st.session_state.kmz_requests = []

if "kmz_skip" not in st.session_state:
    st.session_state.kmz_skip = False

# -----------------------------
# PAGE
# -----------------------------
st.set_page_config(page_title="Air Pollution Analysis App", layout="wide")
st.title("🌍 Air Pollution Analysis Tool")

# -----------------------------
# INSTRUCTIONS
# -----------------------------
st.header("📌 Instructions")
st.markdown("""
- Upload **hourly air quality data**
- CSV format required
""")

# -----------------------------
# SAMPLE DOWNLOAD
# -----------------------------
with open("sample_air_pollution_data.csv", "rb") as file:
    st.download_button("📥 Download Sample Dataset", file, "sample.csv")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("📤 Upload your dataset", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)
    st.write(df.head())

    required_columns = ["From Date","To Date","PM2.5 (ug/m3)","PM10 (ug/m3)",
                        "NO (ug/m3)","NO2 (ug/m3)","NOx (ppb)","SO2 (ug/m3)",
                        "CO (mg/m3)","Ozone (ug/m3)","WS (m/s)","WD (degree)","AT (C)"]

    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

    # -----------------------------
    # DATETIME
    # -----------------------------
    df['From Date'] = pd.to_datetime(df['From Date'], format='mixed', dayfirst=True, errors='coerce')
    df['To Date']   = pd.to_datetime(df['To Date'],   format='mixed', dayfirst=True, errors='coerce')

    if df['From Date'].isnull().any():
        st.error("Invalid From Date")
        st.stop()

    # -----------------------------
    # KMZ INPUT (BEFORE RUN)
    # -----------------------------
    st.header("🌍 KMZ Configuration (Optional)")

    st.caption(f"Data range: {df['From Date'].min()} → {df['From Date'].max()}")

    latitude = st.number_input("Latitude", value=20.345)
    longitude = st.number_input("Longitude", value=85.811)

    pollutant_options = [col for col in df.columns if "(" in col]

    kmz_requests = []

    for i in range(3):

        st.subheader(f"Request {i+1}")

        use = st.checkbox("Enable", key=f"use_{i}")

        if not use:
            continue

        year = st.selectbox("Year", sorted(df['From Date'].dt.year.unique()), key=f"y_{i}")
        month = st.selectbox("Month",
                             sorted(df[df['From Date'].dt.year==year]['From Date'].dt.month.unique()),
                             key=f"m_{i}")

        start = st.number_input("Start Day", 1, 31, 1, key=f"s_{i}")
        end   = st.number_input("End Day", 1, 31, 7, key=f"e_{i}")

        pols = st.multiselect("Pollutants", pollutant_options, key=f"p_{i}")

        kmz_requests.append({
            "year": year,
            "month": month,
            "start_day": start,
            "end_day": end,
            "pollutants": pols
        })

    skip_kmz = st.checkbox("⏭️ Skip KMZ generation")

    # -----------------------------
    # RUN ANALYSIS
    # -----------------------------
    if st.button("🚀 Run Analysis"):

        st.session_state.results = {}
        results = st.session_state.results

        df = df.set_index('From Date')

        progress = st.progress(0)

        # -------------------------
        # DATA QUALITY
        # -------------------------
        from modules.data_quality import check_data_quality
        conv_summary, valid_columns, dropped = check_data_quality(df)

        st.dataframe(conv_summary)
        progress.progress(20)

        # -------------------------
        # DIURNAL
        # -------------------------
        from modules.diurnal import run_diurnal_analysis
        results.update(run_diurnal_analysis(df, valid_columns))
        progress.progress(40)

        # -------------------------
        # SEASON
        # -------------------------
        from modules.season_detection import detect_seasons
        seasons, _ = detect_seasons(df)

        from modules.seasonal import run_seasonal_analysis
        results.update(run_seasonal_analysis(df, valid_columns, seasons))
        progress.progress(60)

        # -------------------------
        # CORRELATION
        # -------------------------
        from modules.met_correlation import run_correlation_analysis
        results.update(run_correlation_analysis(df, valid_columns))
        progress.progress(75)

        # -------------------------
        # ROSES
        # -------------------------
        from modules.roses import run_roses_analysis
        results.update(run_roses_analysis(df, valid_columns))
        progress.progress(85)

        # -------------------------
        # AQI
        # -------------------------
        from modules.aqi import run_aqi_analysis
        results.update(run_aqi_analysis(df))
        progress.progress(95)

        # -------------------------
        # KMZ (OPTIONAL)
        # -------------------------
        if not skip_kmz and kmz_requests:

            from modules.kmz import run_kmz_generation

            kmz_results = run_kmz_generation(
                df,
                kmz_requests,
                latitude,
                longitude
            )

            results.update(kmz_results)

        progress.progress(100)

        st.session_state.analysis_done = True
        st.success("Analysis Complete")

# -----------------------------
# RESULTS + DOWNLOAD (OUTSIDE)
# -----------------------------
if st.session_state.analysis_done:

    results = st.session_state.results

    st.header("📊 Results")

    if not results:
        st.warning("No results generated")
    else:
        for name, file in results.items():
            if name.endswith(".png"):
                st.image(file, caption=name)

    # ZIP
    from modules.utils import create_zip

    zip_buffer = create_zip(results)

    st.download_button(
        "⬇️ Download Results",
        zip_buffer,
        file_name="results.zip",
        mime="application/zip"
    )
