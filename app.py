import streamlit as st
import pandas as pd
import numpy as np

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
            if st.button("Run Analysis"):
                st.session_state.run_analysis = True
                if st.session_state.get("run_analysis"):
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
                    
                    progress.progress(30)

                # CALL YOUR EXISTING CODE HERE
                # results = your_function(df)

                st.success("✅ Analysis complete!")
                # st.write(results)

    else:
        st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
        st.stop()
