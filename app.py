import streamlit as st
import pandas as pd

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
uploaded_file = st.file_uploader("📤 Upload your dataset", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("📊 Preview of Uploaded Data")
    st.write(df.head())

    # --- Validation ---
    required_columns = ["FromDate","ToDate", "PM2.5 (ug/m3)", "PM10 (ug/m3)","NO (ug/m3)", "NO2 (ug/m3)","NOx (ppb)", "SO2 (ug/m3)", "CO (mg/m3)", "O3","WS (m/s)","WD (degree)","AT (C)"]

    if all(col in df.columns for col in required_columns):
        st.success("✅ Data format is correct!")

        # Convert datetime
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")

        if df["Datetime"].isnull().any():
            st.error("❌ Invalid datetime format detected.")
        else:
            st.success("⏱ Datetime format is valid!")

            # --- Run your analysis ---
            if st.button("Run Analysis"):
                st.write("🚀 Running analysis...")

                # CALL YOUR EXISTING CODE HERE
                # results = your_function(df)

                st.success("✅ Analysis complete!")
                # st.write(results)

    else:
        st.error("❌ Missing required columns!")
