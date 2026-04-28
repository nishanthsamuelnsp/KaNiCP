import streamlit as st
import pandas as pd
import numpy as np
import traceback

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if "results" not in st.session_state:
    st.session_state.results = {}

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "valid_columns" not in st.session_state:
    st.session_state.valid_columns = []

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Air Pollution Analysis App", layout="wide")
st.title("🌍 Air Pollution Analysis Tool")

# -----------------------------
# LOGGER (UI DEBUG)
# -----------------------------
log_box = st.empty()

def log(msg):
    log_box.write(f"🔹 {msg}")

# -----------------------------
# SAFE EXECUTOR
# -----------------------------
def safe_run(step_name, func, *args):
    try:
        log(f"{step_name} started")

        output = func(*args)

        if output is None:
            st.warning(f"⚠️ {step_name} returned None")
            return {}

        if not isinstance(output, dict):
            st.error(f"❌ {step_name} must return dict")
            st.stop()

        log(f"{step_name} completed")
        return output

    except Exception:
        st.error(f"❌ {step_name} crashed")
        st.text(traceback.format_exc())
        st.stop()

# -----------------------------
# INSTRUCTIONS
# -----------------------------
st.header("📌 Instructions")
st.markdown("- Upload hourly air pollution CSV")

# -----------------------------
# SAMPLE FILE
# -----------------------------
with open("sample_air_pollution_data.csv", "rb") as file:
    st.download_button("📥 Download Sample Dataset", file, "sample.csv")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("📤 Upload dataset", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file)
    st.write(df.head())

    # -----------------------------
    # VALIDATION
    # -----------------------------
    required_columns = [
        "From Date","To Date","PM2.5 (ug/m3)","PM10 (ug/m3)",
        "NO (ug/m3)","NO2 (ug/m3)","NOx (ppb)","SO2 (ug/m3)",
        "CO (mg/m3)","Ozone (ug/m3)","WS (m/s)","WD (degree)","AT (C)"
    ]

    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        st.error(f"❌ Missing columns: {missing}")
        st.stop()

    # -----------------------------
    # DATETIME
    # -----------------------------
    df['From Date'] = pd.to_datetime(df['From Date'], format='mixed', dayfirst=True, errors='coerce')
    df['To Date']   = pd.to_datetime(df['To Date'],   format='mixed', dayfirst=True, errors='coerce')

    if df['From Date'].isnull().any():
        st.error("❌ Invalid From Date")
        st.stop()

    df = df.set_index('From Date').sort_index()

    # -----------------------------
    # DATA QUALITY (UPFRONT)
    # -----------------------------
    st.header("🧪 Data Quality")

    from modules.data_quality import check_data_quality

    conv_summary, valid_columns, dropped = check_data_quality(df)

    st.dataframe(conv_summary)

    if dropped:
        st.warning(f"Dropped: {dropped}")

    st.session_state.valid_columns = valid_columns

    # -----------------------------
    # KMZ CONFIG
    # -----------------------------
    st.header("🌍 KMZ Configuration")

    st.caption(f"Range: {df.index.min()} → {df.index.max()}")

    latitude = st.number_input("Latitude", value=20.345)
    longitude = st.number_input("Longitude", value=85.811)

    pollutant_options = [
        col for col in valid_columns
        if col not in ['WS (m/s)','WD (degree)','AT (C)','RH (%)','SR (W/mt2)']
    ]

    kmz_requests = []

    for i in range(3):

        st.subheader(f"Request {i+1}")
        use = st.checkbox("Enable", key=f"use_{i}")

        if not use:
            continue

        year = st.selectbox("Year", sorted(df.index.year.unique()), key=f"y_{i}")
        month = st.selectbox(
            "Month",
            sorted(df[df.index.year == year].index.month.unique()),
            key=f"m_{i}"
        )

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

    skip_kmz = st.checkbox("⏭️ Skip KMZ")

    # -----------------------------
    # RUN ANALYSIS
    # -----------------------------
    if st.button("🚀 Run Analysis"):

        st.session_state.results = {}
        results = st.session_state.results

        valid_columns = st.session_state.valid_columns

        # -------------------------
        # DIURNAL
        # -------------------------
        from modules.diurnal import run_diurnal_analysis
        results.update(safe_run("Diurnal", run_diurnal_analysis, df, valid_columns))

        # -------------------------
        # SEASON DETECTION
        # -------------------------
        from modules.season_detection import detect_seasons

        try:
            log("Season detection started")
            seasons, _ = detect_seasons(df)
            log("Season detection done")
        except Exception:
            st.error("❌ Season detection failed")
            st.text(traceback.format_exc())
            st.stop()

        # -------------------------
        # SEASONAL
        # -------------------------
        from modules.seasonal import run_seasonal_analysis
        results.update(safe_run("Seasonal", run_seasonal_analysis, df, valid_columns, seasons))

        # -------------------------
        # CORRELATION
        # -------------------------
        from modules.met_correlation import run_correlation_analysis
        results.update(safe_run("Correlation", run_correlation_analysis, df, valid_columns))

        # -------------------------
        # ROSES
        # -------------------------
        from modules.roses import run_roses_analysis
        results.update(safe_run("Roses", run_roses_analysis, df, valid_columns))

        # -------------------------
        # AQI
        # -------------------------
        from modules.aqi import run_aqi_analysis
        results.update(safe_run("AQI", run_aqi_analysis, df))

        # -------------------------
        # KMZ
        # -------------------------
        if not skip_kmz and kmz_requests:
            from modules.kmz import run_kmz_generation
            results.update(safe_run("KMZ", run_kmz_generation, df, kmz_requests, latitude, longitude))

        st.session_state.analysis_done = True
        st.success("✅ Analysis Complete")

# -----------------------------
# RESULTS + DOWNLOAD
# -----------------------------
if st.session_state.analysis_done:

    st.header("📊 Results")

    results = st.session_state.results

    if not results:
        st.warning("No results available")
    else:
        for name, file in results.items():
            if name.endswith(".png"):
                st.image(file, caption=name)

    from modules.utils import create_zip

    zip_buffer = create_zip(results)

    st.download_button(
        "⬇️ Download Results ZIP",
        zip_buffer,
        file_name="results.zip",
        mime="application/zip"
    )
