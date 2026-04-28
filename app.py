import streamlit as st
import pandas as pd
import numpy as np
st.write("🔁 Script reran")
if "results" not in st.session_state:
    st.session_state.results = {}

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
    
st.set_page_config(page_title="Air Pollution Analysis App", layout="wide")

st.title("🌍 Air Pollution Analysis Tool")

# --- Instructions ---
st.header("📌 Instructions")
st.markdown("""
- Upload **hourly air quality data**
- File format: CSV
- Required columns:
    - Datetime
    - PM2.5, PM10, NO2, SO2, CO, O3
- Datetime format: YYYY-MM-DD HH:MM
""")

# --- Download sample file ---
with open("sample_air_pollution_data.csv", "rb") as file:
    st.download_button(
        label="📥 Download Sample Dataset",
        data=file,
        file_name="sample_air_pollution_data.csv",
        mime="text/csv"
    )

# --- File upload ---
uploaded_file = st.file_uploader("📤 Upload your dataset", type=["csv"],
    accept_multiple_files=False)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("📊 Preview of Uploaded Data")
    st.write(df.head())

    # --- Validation ---
    required_columns = ["From Date","To Date", "PM2.5 (ug/m3)", "PM10 (ug/m3)","NO (ug/m3)", "NO2 (ug/m3)","NOx (ppb)", "SO2 (ug/m3)", "CO (mg/m3)", "Ozone (ug/m3)","WS (m/s)","WD (degree)","AT (C)"]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if all(col in df.columns for col in required_columns):
        st.success("✅ Data format is correct!")
       # df['From Date'] = pd.to_datetime(df['From Date'], format='%d/%m/%Y %H:%M:%S')
        #df['To Date'] = pd.to_datetime(df['To Date'], format='%d/%m/%Y %H:%M:%S')
       
        # Convert datetime
        df['From Date'] = pd.to_datetime(df['From Date'], format='mixed', dayfirst=True, errors='coerce')
        df['To Date']   = pd.to_datetime(df['To Date'],   format='mixed', dayfirst=True, errors='coerce')


        if df["From Date"].isnull().any():
            st.error("❌ Invalid From Date format detected.")
        else:
            st.success("⏱ From Date format is valid!")


        if df["To Date"].isnull().any():
            st.error("❌ Invalid To Date format detected.")
        else:
            st.success("⏱ To Date format is valid!")
        
        
            # --- Run your analysis ---
            if st.button("🚀 Run Analysis"):
                st.write("✅ Button clicked")
                # ✅ reset results properly
                st.session_state.results = {}
                results = st.session_state.results
            
                # ✅ prepare df ONCE
                df = df.copy()
                df = df.set_index('From Date')
                progress = st.progress(0)
                status = st.empty()
                status.write("Step 1: Checking data quality...")
                progress.progress(10)
                status.write("Step 1: Checking data quality...")
                from modules.data_quality import check_data_quality
                
                
                conv_summary, valid_columns, dropped_columns = check_data_quality(df)
                
                st.subheader("📊 Data Quality Summary")
                st.dataframe(conv_summary)
                
                if dropped_columns:
                    st.warning(f"⚠️ Dropped columns (>30% missing): {', '.join(dropped_columns)}")
                else:
                    st.success("✅ No columns dropped")
                progress.progress(10)
                status.write("Step 2: Running Diurnal Analysis...")
                
                from modules.diurnal import run_diurnal_analysis
                diurnal_results = run_diurnal_analysis(df, valid_columns)
                
                progress.progress(30)
                status.write("Step 3: Detecting Seasons...")
                from modules.season_detection import detect_seasons
                
                seasons, monthly = detect_seasons(df)
                
                st.subheader("🌦️ Detected Seasons")
                n_years = df.index.year.nunique()
                st.info(f"📅 Data spans {n_years} year(s); monthly averages computed across years.")
                for season, months in seasons.items():
                    st.write(f"**{season}**: {months}")
                
                progress.progress(50)
                status.write("Step 4: Running Seasonal Analysis...")
                from modules.seasonal import run_seasonal_analysis
                
                seasonal_results = run_seasonal_analysis(df, valid_columns, seasons)
                
                progress.progress(70)
                status.write("Step 5: Running Correlation Analysis...")
                
                from modules.met_correlation import run_correlation_analysis
                corr_results = run_correlation_analysis(df, valid_columns)
                
                if corr_results:
                    st.success("✅ Correlation analysis completed")
                
                    # 👇 Show the image in Streamlit
                    for fname, img_bytes in corr_results.items():
                        st.image(img_bytes, caption=fname)
                
                    # 👇 Add to ZIP bundle
                    results.update(corr_results)
                
                else:
                    st.warning("⚠️ Correlation analysis skipped (insufficient data)")
                progress.progress(80)
                status.write("Step 6: Generating Wind & Pollution Roses...")
                from modules.roses import run_roses_analysis
                
                roses_results = run_roses_analysis(df, valid_columns)
                
                if roses_results:
                    st.success("✅ Roses generated")
                
                    for fname, img_bytes in roses_results.items():
                        st.image(img_bytes, caption=fname)
                
                    results.update(roses_results)
                else:
                    st.warning("⚠️ Roses could not be generated (missing data)")
                progress.progress(85)
                
                status.write("Step 7: Running AQI & Compliance Analysis...")
                from modules.aqi import run_aqi_analysis
                aqi_results = run_aqi_analysis(df)
                
                if aqi_results:
                    st.success("✅ AQI analysis completed")
                
                    for fname, file in aqi_results.items():
                        if fname.endswith(".png"):
                            st.image(file, caption=fname)
                
                    results.update(aqi_results)
                else:
                    st.warning("⚠️ AQI analysis skipped")
                progress.progress(90)
                # ----------------------------------------
                # 🌍 Dynamic Pollution Rose - User Input
                # ----------------------------------------
                
                st.subheader("📍 Dynamic Pollution Rose (KMZ Generator)")
                
                st.info("Select up to 3 time periods (within available dataset). Each request will generate a separate KMZ.")
                
                # -------------------------
                # 📅 Dataset coverage
                # -------------------------
                df.index = pd.to_datetime(df.index)
                
                st.caption(
                    f"📅 Data available from {df.index.min().date()} to {df.index.max().date()}"
                )
                
                # Available years + months
                available_years = sorted(df.index.year.unique())
                
                year_month_map = {
                    year: sorted(df[df.index.year == year].index.month.unique())
                    for year in available_years
                }
                
                # -------------------------
                # 📍 Location input
                # -------------------------
                col1, col2 = st.columns(2)
                
                with col1:
                    latitude = st.number_input("Latitude", value=20.345, format="%.6f")
                
                with col2:
                    longitude = st.number_input("Longitude", value=85.811, format="%.6f")
                
                
                # -------------------------
                # 🧪 Pollutant filtering base
                # -------------------------
                pollutant_options = [
                    col for col in valid_columns
                    if col not in ['WS (m/s)', 'WD (degree)', 'AT (C)', 'RH (%)', 'SR (W/mt2)']
                ]
                
                # -------------------------
                # 📦 KMZ Requests
                # -------------------------
                kmz_requests = []
                
                for i in range(3):
                
                    st.markdown(f"---")
                    st.markdown(f"### 📦 KMZ Request {i+1}")
                
                    use_request = st.checkbox(f"Enable Request {i+1}", key=f"use_{i}")
                
                    if not use_request:
                        continue
                
                    # -------------------------
                    # Year + Month
                    # -------------------------
                    col1, col2 = st.columns(2)
                
                    with col1:
                        year = st.selectbox(
                            "Select Year",
                            options=available_years,
                            key=f"year_{i}"
                        )
                
                    with col2:
                        months_available = year_month_map[year]
                
                        month = st.selectbox(
                            "Select Month",
                            options=months_available,
                            format_func=lambda x: [
                                "Jan","Feb","Mar","Apr","May","Jun",
                                "Jul","Aug","Sep","Oct","Nov","Dec"
                            ][x-1],
                            key=f"month_{i}"
                        )
                
                    # -------------------------
                    # Mode
                    # -------------------------
                    mode = st.radio(
                        "Select Mode",
                        ["Full Month", "Custom Range"],
                        key=f"mode_{i}"
                    )
                
                    # -------------------------
                    # Day selection
                    # -------------------------
                    if mode == "Custom Range":
                
                        col3, col4 = st.columns(2)
                
                        with col3:
                            start_day = st.number_input(
                                "Start Day",
                                min_value=1,
                                max_value=31,
                                value=1,
                                key=f"start_{i}"
                            )
                
                        with col4:
                            end_day = st.number_input(
                                "End Day",
                                min_value=1,
                                max_value=31,
                                value=7,
                                key=f"end_{i}"
                            )
                
                    else:
                        start_day = 1
                        end_day = 31
                
                    # -------------------------
                    # 🧪 Pollutants (PER REQUEST)
                    # -------------------------
                    selected_pollutants = st.multiselect(
                        "Select pollutants for this KMZ",
                        options=pollutant_options,
                        key=f"pollutants_{i}"
                    )
                
                    if not selected_pollutants:
                        st.warning(f"⚠️ Select at least one pollutant for Request {i+1}")
                
                    # -------------------------
                    # Store request
                    # -------------------------
                    kmz_requests.append({
                        "year": year,
                        "month": month,
                        "start_day": start_day,
                        "end_day": end_day,
                        "pollutants": selected_pollutants
                    })
                
                
                # -------------------------
                # 🚀 Generate Button
                # -------------------------
                generate_kmz = st.button("🌍 Generate KMZ Files")
                
                # -------------------------
                # ⚠️ Validation
                # -------------------------
                if generate_kmz:
                
                    if not kmz_requests:
                        st.warning("⚠️ Please enable at least one KMZ request.")
                
                    elif any(len(req["pollutants"]) == 0 for req in kmz_requests):
                        st.warning("⚠️ Each enabled request must have at least one pollutant selected.")
                
                    else:
                        st.success("✅ Ready for KMZ generation")
                        from modules.kmz import run_kmz_generation
                    
                        kmz_results = run_kmz_generation(
                            df,
                            kmz_requests,
                            latitude,
                            longitude
                        )
                    
                        results.update(kmz_results)
                    
                        st.success("✅ KMZ files generated successfully")
                from modules.utils import create_zip

                skip_kmz = st.button("⏭️ Skip KMZ & Download Results")
                                                        
                if skip_kmz:
                    if not results:
                        st.warning("⚠️ No results available yet.")
                    else:
                        zip_buffer = create_zip(results)
                
                        st.success("✅ Results packaged successfully")
                
                        st.download_button(
                            label="⬇️ Download Results ZIP",
                            data=zip_buffer,
                            file_name="air_pollution_results.zip",
                            mime="application/zip"
                        )                                        

                # CALL YOUR EXISTING CODE HERE
                # results = your_function(df)
                results = st.session_state.get("results", {})

                if st.session_state.get("analysis_done", False):
                
                    if not results:
                        st.warning("⚠️ No results available yet.")
                
                    else:
                        zip_buffer = create_zip(results)
                
                        st.success("✅ Results packaged successfully")
                
                        st.download_button(
                            label="⬇️ Download Results ZIP",
                            data=zip_buffer,
                            file_name="air_pollution_results.zip",
                            mime="application/zip"
                        )
                # st.write(results)

    else:
        st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
        st.stop()
