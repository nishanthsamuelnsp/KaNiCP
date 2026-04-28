import pandas as pd
import streamlit as st


REQUIRED_COLUMNS = [
    "From Date",
    "To Date",
    "PM2.5 (ug/m3)",
    "PM10 (ug/m3)",
    "NO (ug/m3)",
    "NO2 (ug/m3)",
    "NOx (ppb)",
    "SO2 (ug/m3)",
    "CO (mg/m3)",
    "Ozone (ug/m3)",
    "WS (m/s)",
    "WD (degree)",
    "AT (C)",
]

NON_POLLUTANT_COLUMNS = ["WS (m/s)", "WD (degree)", "AT (C)", "RH (%)", "SR (W/mt2)"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def initialize_session_state():
    if "results" not in st.session_state:
        st.session_state.results = {}

    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False


def configure_page():
    st.set_page_config(page_title="Air Pollution Analysis App", layout="wide")
    st.title("Air Pollution Analysis Tool")


def render_instructions():
    st.header("Instructions")
    st.markdown(
        """
- Upload **hourly air quality data**
- File format: CSV
- Required columns:
    - Datetime
    - PM2.5, PM10, NO2, SO2, CO, O3
- Datetime format: YYYY-MM-DD HH:MM
"""
    )


def render_sample_download():
    with open("sample_air_pollution_data.csv", "rb") as file:
        st.download_button(
            label="Download Sample Dataset",
            data=file,
            file_name="sample_air_pollution_data.csv",
            mime="text/csv",
        )


def load_uploaded_dataframe():
    uploaded_file = st.file_uploader("Upload your dataset", type=["csv"], accept_multiple_files=False)
    if uploaded_file is None:
        return None

    df = pd.read_csv(uploaded_file)
    st.subheader("Preview of Uploaded Data")
    st.write(df.head())
    return df


def validate_columns(df):
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        st.error(f"Missing required columns: {', '.join(missing_columns)}")
        st.stop()

    st.success("Data format is correct!")


def convert_datetime_columns(df):
    converted_df = df.copy()
    converted_df["From Date"] = pd.to_datetime(
        converted_df["From Date"],
        format="mixed",
        dayfirst=True,
        errors="coerce",
    )
    converted_df["To Date"] = pd.to_datetime(
        converted_df["To Date"],
        format="mixed",
        dayfirst=True,
        errors="coerce",
    )

    if converted_df["From Date"].isnull().any():
        st.error("Invalid From Date format detected.")
    else:
        st.success("From Date format is valid!")

    if converted_df["To Date"].isnull().any():
        st.error("Invalid To Date format detected.")
        to_date_valid = False
    else:
        st.success("To Date format is valid!")
        to_date_valid = True

    return converted_df, to_date_valid


def prepare_analysis_dataframe(df):
    prepared_df = df.copy()
    prepared_df = prepared_df.set_index("From Date")
    prepared_df.index = pd.to_datetime(prepared_df.index)
    return prepared_df


def render_data_quality_summary(conv_summary, dropped_columns):
    st.subheader("Data Quality Summary")
    st.dataframe(conv_summary)

    if dropped_columns:
        st.warning(f"Dropped columns (>30% missing): {', '.join(dropped_columns)}")
    else:
        st.success("No columns dropped")


def render_correlation_results(corr_results, results):
    if corr_results:
        st.success("Correlation analysis completed")
        for filename, image_bytes in corr_results.items():
            st.image(image_bytes, caption=filename)
        results.update(corr_results)
    else:
        st.warning("Correlation analysis skipped (insufficient data)")


def render_rose_results(roses_results, results):
    if roses_results:
        st.success("Roses generated")
        for filename, image_bytes in roses_results.items():
            st.image(image_bytes, caption=filename)
        results.update(roses_results)
    else:
        st.warning("Roses could not be generated (missing data)")


def render_aqi_results(aqi_results, results):
    if aqi_results:
        st.success("AQI analysis completed")
        for filename, file_data in aqi_results.items():
            if filename.endswith(".png"):
                st.image(file_data, caption=filename)
        results.update(aqi_results)
    else:
        st.warning("AQI analysis skipped")


def render_season_summary(df, seasons):
    st.subheader("Detected Seasons")
    n_years = df.index.year.nunique()
    st.info(f"Data spans {n_years} year(s); monthly averages computed across years.")
    for season, months in seasons.items():
        st.write(f"**{season}**: {months}")


def run_analysis(df):
    from modules.aqi import run_aqi_analysis
    from modules.data_quality import check_data_quality
    from modules.diurnal import run_diurnal_analysis
    from modules.met_correlation import run_correlation_analysis
    from modules.roses import run_roses_analysis
    from modules.season_detection import detect_seasons
    from modules.seasonal import run_seasonal_analysis

    st.session_state.results = {}
    results = st.session_state.results

    analysis_df = prepare_analysis_dataframe(df)
    progress = st.progress(0)
    status = st.empty()

    status.write("Step 1: Checking data quality...")
    progress.progress(10)
    conv_summary, valid_columns, dropped_columns = check_data_quality(analysis_df)
    render_data_quality_summary(conv_summary, dropped_columns)

    status.write("Step 2: Running Diurnal Analysis...")
    progress.progress(10)
    run_diurnal_analysis(analysis_df, valid_columns)

    status.write("Step 3: Detecting Seasons...")
    progress.progress(30)
    seasons, monthly = detect_seasons(analysis_df)
    render_season_summary(analysis_df, seasons)

    status.write("Step 4: Running Seasonal Analysis...")
    progress.progress(50)
    run_seasonal_analysis(analysis_df, valid_columns, seasons)

    status.write("Step 5: Running Correlation Analysis...")
    progress.progress(70)
    corr_results = run_correlation_analysis(analysis_df, valid_columns)
    render_correlation_results(corr_results, results)

    status.write("Step 6: Generating Wind & Pollution Roses...")
    progress.progress(80)
    roses_results = run_roses_analysis(analysis_df, valid_columns)
    render_rose_results(roses_results, results)

    status.write("Step 7: Running AQI & Compliance Analysis...")
    progress.progress(85)
    aqi_results = run_aqi_analysis(analysis_df)
    render_aqi_results(aqi_results, results)

    progress.progress(90)
    return analysis_df, valid_columns, monthly


def build_year_month_map(df):
    available_years = sorted(df.index.year.unique())
    year_month_map = {
        year: sorted(df[df.index.year == year].index.month.unique())
        for year in available_years
    }
    return available_years, year_month_map


def render_kmz_request(index, available_years, year_month_map, pollutant_options):
    st.markdown("---")
    st.markdown(f"### KMZ Request {index + 1}")

    use_request = st.checkbox(f"Enable Request {index + 1}", key=f"use_{index}")
    if not use_request:
        return None

    col1, col2 = st.columns(2)

    with col1:
        year = st.selectbox("Select Year", options=available_years, key=f"year_{index}")

    with col2:
        months_available = year_month_map[year]
        month = st.selectbox(
            "Select Month",
            options=months_available,
            format_func=lambda value: MONTH_NAMES[value - 1],
            key=f"month_{index}",
        )

    mode = st.radio("Select Mode", ["Full Month", "Custom Range"], key=f"mode_{index}")

    if mode == "Custom Range":
        col3, col4 = st.columns(2)

        with col3:
            start_day = st.number_input(
                "Start Day",
                min_value=1,
                max_value=31,
                value=1,
                key=f"start_{index}",
            )

        with col4:
            end_day = st.number_input(
                "End Day",
                min_value=1,
                max_value=31,
                value=7,
                key=f"end_{index}",
            )
    else:
        start_day = 1
        end_day = 31

    selected_pollutants = st.multiselect(
        "Select pollutants for this KMZ",
        options=pollutant_options,
        key=f"pollutants_{index}",
    )

    if not selected_pollutants:
        st.warning(f"Select at least one pollutant for Request {index + 1}")

    return {
        "year": year,
        "month": month,
        "start_day": start_day,
        "end_day": end_day,
        "pollutants": selected_pollutants,
    }


def render_kmz_section(df, valid_columns, results):
    from modules.kmz import run_kmz_generation

    st.subheader("Dynamic Pollution Rose (KMZ Generator)")
    st.info("Select up to 3 time periods (within available dataset). Each request will generate a separate KMZ.")
    st.caption(f"Data available from {df.index.min().date()} to {df.index.max().date()}")

    available_years, year_month_map = build_year_month_map(df)

    col1, col2 = st.columns(2)
    with col1:
        latitude = st.number_input("Latitude", value=20.345, format="%.6f")
    with col2:
        longitude = st.number_input("Longitude", value=85.811, format="%.6f")

    pollutant_options = [column for column in valid_columns if column not in NON_POLLUTANT_COLUMNS]
    kmz_requests = []

    for index in range(3):
        request = render_kmz_request(index, available_years, year_month_map, pollutant_options)
        if request is not None:
            kmz_requests.append(request)

    generate_kmz = st.button("Generate KMZ Files")
    if generate_kmz:
        if not kmz_requests:
            st.warning("Please enable at least one KMZ request.")
        elif any(len(request["pollutants"]) == 0 for request in kmz_requests):
            st.warning("Each enabled request must have at least one pollutant selected.")
        else:
            st.success("Ready for KMZ generation")
            kmz_results = run_kmz_generation(df, kmz_requests, latitude, longitude)
            results.update(kmz_results)
            st.success("KMZ files generated successfully")


def render_download_section():
    from modules.utils import create_zip

    skip_kmz = st.button("Skip KMZ & Download Results")
    if skip_kmz:
        if not st.session_state.results:
            st.warning("No results available yet.")
        else:
            zip_buffer = create_zip(st.session_state.results)
            st.success("Results packaged successfully")
            st.download_button(
                label="Download Results ZIP",
                data=zip_buffer,
                file_name="air_pollution_results.zip",
                mime="application/zip",
            )

    results = st.session_state.get("results", {})
    if st.session_state.get("analysis_done", False):
        if not results:
            st.warning("No results available yet.")
        else:
            zip_buffer = create_zip(results)
            st.success("Results packaged successfully")
            st.download_button(
                label="Download Results ZIP",
                data=zip_buffer,
                file_name="air_pollution_results.zip",
                mime="application/zip",
            )


def main():
    initialize_session_state()
    configure_page()
    render_instructions()
    render_sample_download()

    df = load_uploaded_dataframe()
    if df is None:
        return

    validate_columns(df)
    converted_df, to_date_valid = convert_datetime_columns(df)

    if to_date_valid and st.button("Run Analysis"):
        analysis_df, valid_columns, monthly = run_analysis(converted_df)
        render_kmz_section(analysis_df, valid_columns, st.session_state.results)
        render_download_section()


if __name__ == "__main__":
    main()
