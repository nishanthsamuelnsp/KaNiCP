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

if "valid_columns" not in st.session_state:
    st.session_state.valid_columns = []

# -----------------------------
# PAGE CONFIG
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
# SAMPLE FILE
# -----------------------------
with open("sample_air_pollution_data.csv", "rb") as file:
    st.download_button("📥 Download Sample Dataset", file, "sample.csv")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("📤 Upload your dataset", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)
    st.subheader("📊 Preview")
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
        st.error("❌ Invalid From Date format")
        st.stop()

    df = df.set_index('From Date')
    df = df.sort_index()

    # -----------------------------
    # 🧪 DATA QUALITY (MOVED UP)
    # -----------------------------
    st.header("🧪 Data Quality Check")

    from modules.data_quality import check_data_quality

    conv_summary, valid_columns, dropped_columns = check_data_quality(df)

    st.dataframe(conv_summary)

    if dropped_columns:
        st.warning(f"⚠️ Dropped (>30% missing): {', '.join(dropped_columns)}")
    else:
        st.success("✅ No columns dropped")

    st.session_state.valid_columns = valid_columns

    # -----------------------------
    # 🌍 KMZ CONFIG
    # -----------------------------
    st.header("🌍 KMZ Configuration (Optional)")

    st.caption(f"📅 Data range: {df.index.min().date()} → {df.index.max().date()}")

    latitude = st.number_input("Latitude", value=20.345)
    longitude = st.number_input("Longitude", value=85.811)

    valid_columns = st.session_state.get("valid_columns", [])

    pollutant_options = [
        col for col in valid_columns
        if col not in ['WS (m/s)', 'WD (degree)', 'AT (C)', 'RH (%)', 'SR (W/mt2)']
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

    skip_kmz = st.checkbox("⏭️ Skip KMZ generation")

    # -----------------------------
    # 🚀 RUN ANALYSIS
    # -----------------------------
    if st.button("🚀 Run Analysis"):
        st.write("inside analysis section")
        st.session_state.results = {}
        results = st.session_state.results

        progress = st.progress(0)

        valid_columns = st.session_state.get("valid_columns", [])

        # -------------------------
        # DIURNAL (UNCHANGED)
        # -------------------------
        from modules.diurnal import run_diurnal_analysis
        results.update(run_diurnal_analysis(df, valid_columns))
        progress.progress(25)

        # -------------------------
        # SEASON DETECTION
        # -------------------------
        try:
            from modules.season_detection import detect_seasons
            seasons, _ = detect_seasons(df)
        except Exception as e:
            st.error(f"❌ Season detection failed: {e}")
            st.stop()

        progress.progress(40)

        # -------------------------
        # SEASONAL
        # -------------------------
        st.write("starting seasonal analysis")
        from modules.seasonal import run_seasonal_analysis
        results.update(run_seasonal_analysis(df, valid_columns, seasons))
        st.subheader("🌦️ Seasonal Split Used for Analysis")

        if seasons:
            for season, months in seasons.items():
                if months:
                    month_names = [
                        "Jan","Feb","Mar","Apr","May","Jun",
                        "Jul","Aug","Sep","Oct","Nov","Dec"
                    ]
                    readable = [month_names[m-1] for m in months]
        
                    st.write(f"**{season}**: {', '.join(readable)}")
                else:
                    st.write(f"**{season}**: (No months detected)")
        else:
            st.warning("⚠️ No seasonal classification available")
        progress.progress(60)

        # -------------------------
        # CORRELATION
        # -------------------------
        st.write("Starting correlation")
        from modules.met_correlation import run_correlation_analysis
        results.update(run_correlation_analysis(df, valid_columns))
        progress.progress(75)

        # -------------------------
        # ROSES
        # -------------------------
        st.write("starting roses")
        #from modules.roses import run_roses_analysis
        #results.update(run_roses_analysis(df, valid_columns))
        progress.progress(85)

        # -------------------------
        # AQI
        # -------------------------
        from modules.aqi import run_aqi_analysis
        st.write("starting aqi")
        #results.update(run_aqi_analysis(df))
        progress.progress(95)

        # -------------------------
        # KMZ
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
        st.success("✅ Analysis Complete")

# -----------------------------
# 📊 RESULTS + DOWNLOAD
# -----------------------------
if st.session_state.analysis_done:

    st.header("📊 Results")

    results = st.session_state.results

    if not results:
        st.warning("⚠️ No results generated")
    

    from modules.utils import create_zip

    zip_buffer = create_zip(results)

    st.download_button(
        "⬇️ Download Results ZIP",
        zip_buffer,
        file_name="air_pollution_results.zip",
        mime="application/zip"
    )
