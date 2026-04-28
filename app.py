import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------
# 🔐 Session State Init
# -----------------------------
if "results" not in st.session_state:
    st.session_state.results = {}

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# -----------------------------
# 📄 Page Config
# -----------------------------
st.set_page_config(page_title="Air Pollution Analysis App", layout="wide")
st.title("🌍 Air Pollution Analysis Tool")

# -----------------------------
# 📌 Instructions
# -----------------------------
st.header("📌 Instructions")
st.markdown("""
- Upload **hourly air quality data**
- CSV format required
- Ensure correct column headers
""")

# -----------------------------
# 📤 Upload
# -----------------------------
uploaded_file = st.file_uploader(
    "📤 Upload your dataset",
    type=["csv"],
    accept_multiple_files=False
)

# -----------------------------
# 🚀 RUN ANALYSIS
# -----------------------------
if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)
    st.subheader("📊 Data Preview")
    st.dataframe(df.head())

    required_columns = [
        "From Date","To Date",
        "PM2.5 (ug/m3)","PM10 (ug/m3)",
        "NO (ug/m3)","NO2 (ug/m3)","NOx (ppb)",
        "SO2 (ug/m3)","CO (mg/m3)","Ozone (ug/m3)",
        "WS (m/s)","WD (degree)","AT (C)"
    ]

    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        st.error(f"❌ Missing columns: {', '.join(missing)}")
        st.stop()

    st.success("✅ Data format OK")

    # Datetime conversion
    df['From Date'] = pd.to_datetime(df['From Date'], format='mixed', dayfirst=True, errors='coerce')
    df['To Date']   = pd.to_datetime(df['To Date'],   format='mixed', dayfirst=True, errors='coerce')

    if df['From Date'].isnull().any():
        st.error("❌ Invalid From Date format")
        st.stop()

    # -----------------------------
    # RUN BUTTON
    # -----------------------------
    if st.button("🚀 Run Analysis", key="run_analysis"):

        st.session_state.results = {}
        results = st.session_state.results

        df = df.copy()
        df = df.set_index('From Date')

        progress = st.progress(0)

        # -------------------------
        # Step 1: Data Quality
        # -------------------------
        from modules.data_quality import check_data_quality
        conv_summary, valid_columns, dropped_columns = check_data_quality(df)

        st.subheader("📊 Data Quality")
        st.dataframe(conv_summary)

        progress.progress(20)

        # -------------------------
        # Step 2: Diurnal
        # -------------------------
        from modules.diurnal import run_diurnal_analysis
        results.update(run_diurnal_analysis(df, valid_columns))

        progress.progress(40)

        # -------------------------
        # Step 3: Seasonal
        # -------------------------
        from modules.season_detection import detect_seasons
        seasons, _ = detect_seasons(df)

        from modules.seasonal import run_seasonal_analysis
        results.update(run_seasonal_analysis(df, valid_columns, seasons))

        progress.progress(60)

        # -------------------------
        # Step 4: Correlation
        # -------------------------
        from modules.met_correlation import run_correlation_analysis
        results.update(run_correlation_analysis(df, valid_columns))

        progress.progress(75)

        # -------------------------
        # Step 5: Roses
        # -------------------------
        from modules.roses import run_roses_analysis
        results.update(run_roses_analysis(df, valid_columns))

        progress.progress(85)

        # -------------------------
        # Step 6: AQI
        # -------------------------
        from modules.aqi import run_aqi_analysis
        results.update(run_aqi_analysis(df))

        progress.progress(100)

        st.session_state.analysis_done = True
        st.success("✅ Analysis Complete")

# -----------------------------
# 📊 RESULTS + KMZ + DOWNLOAD
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

    # -----------------------------
    # 🌍 KMZ SECTION
    # -----------------------------
    st.header("🌍 KMZ Generator")

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    available_years = sorted(df.index.year.unique())
    year_month_map = {
        y: sorted(df[df.index.year == y].index.month.unique())
        for y in available_years
    }

    latitude = st.number_input("Latitude", value=20.345)
    longitude = st.number_input("Longitude", value=85.811)

    pollutant_options = [
        col for col in df.columns
        if col not in ['WS (m/s)','WD (degree)','AT (C)','RH (%)']
    ]

    kmz_requests = []

    for i in range(3):
        st.subheader(f"Request {i+1}")

        use = st.checkbox("Enable", key=f"use_{i}")
        if not use:
            continue

        year = st.selectbox("Year", available_years, key=f"year_{i}")
        month = st.selectbox("Month", year_month_map[year], key=f"month_{i}")

        start_day = st.number_input("Start Day", 1, 31, 1, key=f"s_{i}")
        end_day   = st.number_input("End Day", 1, 31, 7, key=f"e_{i}")

        pols = st.multiselect("Pollutants", pollutant_options, key=f"p_{i}")

        kmz_requests.append({
            "year": year,
            "month": month,
            "start_day": start_day,
            "end_day": end_day,
            "pollutants": pols
        })

    # -----------------------------
    # KMZ BUTTON
    # -----------------------------
    if st.button("🌍 Generate KMZ", key="kmz_btn"):

        if not kmz_requests:
            st.warning("No KMZ requests selected")

        else:
            from modules.kmz import run_kmz_generation

            kmz_results = run_kmz_generation(
                df,
                kmz_requests,
                latitude,
                longitude
            )

            st.session_state.results.update(kmz_results)

            st.success("✅ KMZ Generated")

    # -----------------------------
    # 📦 DOWNLOAD
    # -----------------------------
    from modules.utils import create_zip

    if st.session_state.results:
        zip_buffer = create_zip(st.session_state.results)

        st.download_button(
            "⬇️ Download Results",
            data=zip_buffer,
            file_name="results.zip",
            mime="application/zip"
        )
