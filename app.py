import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------
# 🔐 SESSION STATE INIT
# -----------------------------
if "df" not in st.session_state:
    st.session_state.df = None

if "results" not in st.session_state:
    st.session_state.results = {}

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# -----------------------------
# 📄 PAGE
# -----------------------------
st.set_page_config(page_title="Air Pollution App", layout="wide")
st.title("🌍 Air Pollution Analysis")

# -----------------------------
# 📤 FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # ✅ store once
    st.session_state.df = df
    st.session_state.analysis_done = False   # reset if new file uploaded

# -----------------------------
# 📊 PREVIEW
# -----------------------------
if st.session_state.df is not None:
    st.subheader("Preview")
    st.dataframe(st.session_state.df.head())

# -----------------------------
# 🚀 RUN ANALYSIS
# -----------------------------
if st.session_state.df is not None:

    if st.button("🚀 Run Analysis", key="run_btn"):

        df = st.session_state.df.copy()

        # -------------------------
        # SAFE DATETIME
        # -------------------------
        df['From Date'] = pd.to_datetime(
            df['From Date'],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )

        if df['From Date'].isnull().any():
            st.error("Invalid datetime format")
            st.stop()

        df = df.set_index('From Date')

        # -------------------------
        # RESET RESULTS
        # -------------------------
        st.session_state.results = {}
        results = st.session_state.results

        progress = st.progress(0)

        # -------------------------
        # MODULE CALLS
        # -------------------------
        from modules.data_quality import check_data_quality
        conv_summary, valid_columns, dropped = check_data_quality(df)

        st.write("Data Quality")
        st.dataframe(conv_summary)

        progress.progress(20)

        from modules.diurnal import run_diurnal_analysis
        results.update(run_diurnal_analysis(df, valid_columns))

        progress.progress(40)

        from modules.season_detection import detect_seasons
        seasons, _ = detect_seasons(df)

        from modules.seasonal import run_seasonal_analysis
        results.update(run_seasonal_analysis(df, valid_columns, seasons))

        progress.progress(60)

        from modules.met_correlation import run_correlation_analysis
        results.update(run_correlation_analysis(df, valid_columns))

        progress.progress(75)

        from modules.roses import run_roses_analysis
        results.update(run_roses_analysis(df, valid_columns))

        progress.progress(85)

        from modules.aqi import run_aqi_analysis
        results.update(run_aqi_analysis(df))

        progress.progress(100)

        # ✅ CRITICAL LINE
        st.session_state.analysis_done = True

        st.success("✅ Analysis Complete")

# -----------------------------
# 📊 RESULTS (ALWAYS OUTSIDE BUTTON)
# -----------------------------
if st.session_state.analysis_done:

    results = st.session_state.results
    df = st.session_state.df.copy()

    st.header("📊 Results")

    if not results:
        st.warning("No results found")
    else:
        for name, file in results.items():
            if name.endswith(".png"):
                st.image(file, caption=name)

    # -----------------------------
    # 🌍 KMZ SECTION
    # -----------------------------
    st.header("🌍 KMZ Generator")

    df['From Date'] = pd.to_datetime(df['From Date'], format='mixed', dayfirst=True)
    df = df.set_index('From Date')

    latitude = st.number_input("Latitude", value=20.345)
    longitude = st.number_input("Longitude", value=85.811)

    pollutant_options = [
        col for col in df.columns
        if col not in ['WS (m/s)', 'WD (degree)', 'AT (C)', 'RH (%)']
    ]

    kmz_requests = []

    for i in range(3):
        st.subheader(f"Request {i+1}")

        use = st.checkbox("Enable", key=f"use_{i}")
        if not use:
            continue

        year = st.selectbox("Year", sorted(df.index.year.unique()), key=f"y_{i}")
        month = st.selectbox("Month", sorted(df[df.index.year == year].index.month.unique()), key=f"m_{i}")

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

    # -----------------------------
    # KMZ BUTTON
    # -----------------------------
    if st.button("🌍 Generate KMZ", key="kmz_btn"):

        if not kmz_requests:
            st.warning("No KMZ selected")
        else:
            from modules.kmz import run_kmz_generation

            kmz_results = run_kmz_generation(
                df,
                kmz_requests,
                latitude,
                longitude
            )

            st.session_state.results.update(kmz_results)
            st.success("KMZ generated")

    # -----------------------------
    # 📦 DOWNLOAD
    # -----------------------------
    from modules.utils import create_zip

    zip_buffer = create_zip(st.session_state.results)

    st.download_button(
        "⬇️ Download Results",
        data=zip_buffer,
        file_name="results.zip",
        mime="application/zip"
    )
