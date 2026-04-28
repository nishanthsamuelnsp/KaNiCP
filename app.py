# app.py — zero module changes required
import streamlit as st
import pandas as pd
import traceback
import io
import os

# ── session state ────────────────────────────────────────────
for k, v in {"results": {}, "valid_columns": [], "analysis_done": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.set_page_config(page_title="Air Pollution Analysis App", layout="wide")
st.title("🌍 Air Pollution Analysis Tool")

# ── result normalizer ─────────────────────────────────────────
def normalize_result(name: str, raw) -> dict:
    """
    Accept whatever a module returns and produce dict[str, bytes].

    Handles:
      - dict[str, bytes]          already correct
      - dict[str, BytesIO/file]   read() each value
      - dict[str, str]            treat as file paths, read from disk
      - BytesIO / file-like       wrap as "<name>.bin"
      - str / Path                read file from disk
      - None / {}                 return {}
    """
    if not raw:
        return {}

    if isinstance(raw, dict):
        out = {}
        for k, v in raw.items():
            if isinstance(v, (bytes, bytearray)):
                out[k] = bytes(v)
            elif hasattr(v, "read"):          # BytesIO, file object
                v.seek(0)
                out[k] = v.read()
            elif isinstance(v, (str, os.PathLike)) and os.path.isfile(v):
                with open(v, "rb") as f:
                    out[k] = f.read()
            elif isinstance(v, (str, os.PathLike)):
                out[k] = str(v).encode()     # plain text result
            else:
                st.warning(f"⚠️ {name}: skipping key '{k}' — unrecognised type {type(v).__name__}")
        return out

    if hasattr(raw, "read"):                  # bare BytesIO
        raw.seek(0)
        return {f"{name}.bin": raw.read()}

    if isinstance(raw, (bytes, bytearray)):
        return {f"{name}.bin": bytes(raw)}

    if isinstance(raw, (str, os.PathLike)) and os.path.isfile(raw):
        with open(raw, "rb") as f:
            return {f"{name}.bin": f.read()}

    st.warning(f"⚠️ {name}: unrecognised return type {type(raw).__name__} — skipped")
    return {}


# ── safe runner ───────────────────────────────────────────────
def safe_run(name: str, func, *args) -> dict:
    """Run func, normalize output, never crash the whole app."""
    try:
        raw = func(*args)
        result = normalize_result(name, raw)
        if result:
            st.success(f"✅ {name}")
        else:
            st.warning(f"⚠️ {name} produced no output")
        return result
    except Exception:
        st.error(f"❌ {name} failed")
        with st.expander("Show traceback"):
            st.code(traceback.format_exc())
        return {}          # keep going — don't st.stop()


# ── sample download ───────────────────────────────────────────
with open("sample_air_pollution_data.csv", "rb") as f:
    st.download_button("📥 Download Sample Dataset", f, "sample.csv")

# ── upload ────────────────────────────────────────────────────
uploaded_file = st.file_uploader("📤 Upload dataset", type=["csv"])
if not uploaded_file:
    st.stop()

df = pd.read_csv(uploaded_file)
st.write(df.head())

# ── validate ──────────────────────────────────────────────────
REQUIRED = [
    "From Date","To Date","PM2.5 (ug/m3)","PM10 (ug/m3)",
    "NO (ug/m3)","NO2 (ug/m3)","NOx (ppb)","SO2 (ug/m3)",
    "CO (mg/m3)","Ozone (ug/m3)","WS (m/s)","WD (degree)","AT (C)",
]
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"❌ Missing columns: {missing}")
    st.stop()

df["From Date"] = pd.to_datetime(df["From Date"], format="mixed", dayfirst=True, errors="coerce")
df["To Date"]   = pd.to_datetime(df["To Date"],   format="mixed", dayfirst=True, errors="coerce")
if df["From Date"].isnull().any():
    st.error("❌ Invalid From Date values found")
    st.stop()

df = df.set_index("From Date").sort_index()

# ── data quality ──────────────────────────────────────────────
st.header("🧪 Data Quality")
from modules.data_quality import check_data_quality
conv_summary, valid_columns, dropped = check_data_quality(df)
st.dataframe(conv_summary)
if dropped:
    st.warning(f"Dropped: {dropped}")
st.session_state.valid_columns = valid_columns

# ── KMZ config (in expander — stops widget re-evaluation on every rerun) ──
MET_COLS = {"WS (m/s)", "WD (degree)", "AT (C)", "RH (%)", "SR (W/mt2)"}
pollutant_options = [c for c in valid_columns if c not in MET_COLS]

with st.expander("🌍 KMZ Configuration", expanded=False):
    st.caption(f"Range: {df.index.min()} → {df.index.max()}")
    latitude  = st.number_input("Latitude",  value=20.345)
    longitude = st.number_input("Longitude", value=85.811)
    skip_kmz  = st.checkbox("⏭️ Skip KMZ", value=True)

    kmz_requests = []
    for i in range(3):
        st.subheader(f"Request {i+1}")
        if not st.checkbox("Enable", key=f"use_{i}"):
            continue
        year  = st.selectbox("Year",  sorted(df.index.year.unique()), key=f"y_{i}")
        month = st.selectbox("Month", sorted(df[df.index.year==year].index.month.unique()), key=f"m_{i}")
        start = st.number_input("Start Day", 1, 31, 1,  key=f"s_{i}")
        end   = st.number_input("End Day",   1, 31, 7,  key=f"e_{i}")
        pols  = st.multiselect("Pollutants", pollutant_options, key=f"p_{i}")
        kmz_requests.append(dict(year=year, month=month, start_day=start, end_day=end, pollutants=pols))

# ── run ───────────────────────────────────────────────────────
if st.button("🚀 Run Analysis"):

    results = {}
    vc = st.session_state.valid_columns

    with st.status("Running analysis…", expanded=True):

        from modules.diurnal import run_diurnal_analysis
        results |= safe_run("Diurnal", run_diurnal_analysis, df, vc)

        # Season detection feeds into seasonal — handle separately so seasonal
        # can still run with an empty seasons dict if detection fails
        try:
            from modules.season_detection import detect_seasons
            seasons, _ = detect_seasons(df)
        except Exception:
            st.error("❌ Season detection failed — seasonal analysis will use empty seasons")
            with st.expander("Show traceback"):
                st.code(traceback.format_exc())
            seasons = {}

        from modules.seasonal import run_seasonal_analysis
        results |= safe_run("Seasonal", run_seasonal_analysis, df, vc, seasons)

        from modules.met_correlation import run_correlation_analysis
        results |= safe_run("Correlation", run_correlation_analysis, df, vc)

        from modules.roses import run_roses_analysis
        results |= safe_run("Roses", run_roses_analysis, df, vc)

        from modules.aqi import run_aqi_analysis
        results |= safe_run("AQI", run_aqi_analysis, df)

        if not skip_kmz and kmz_requests:
            from modules.kmz import run_kmz_generation
            results |= safe_run("KMZ", run_kmz_generation, df, kmz_requests, latitude, longitude)

    st.session_state.results = results
    st.session_state.analysis_done = True
    st.success(f"✅ Analysis complete — {len(results)} file(s) ready")

# ── results ───────────────────────────────────────────────────
if st.session_state.analysis_done:
    st.header("📊 Results")
    results = st.session_state.results

    if not results:
        st.warning("No results available.")
    else:
        for filename, data in results.items():
            if filename.endswith(".png"):
                st.image(data, caption=filename)

        from modules.utils import create_zip
        zip_buf = create_zip(results)

        st.download_button(
            "⬇️ Download Results ZIP",
            zip_buf,
            file_name="results.zip",
            mime="application/zip",
        )
