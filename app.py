import streamlit as st

from src.data_loader import load_data
from src.cleaning import clean_data
from src.geospatial import build_geodataframe
from src.metrics import compute_metrics
from src.visualization import plot_map, plot_chart

st.set_page_config(page_title="Emergency Access Peru", layout="wide")

st.title("Emergency Access in Peru")
st.markdown("District-level analysis of emergency service accessibility.")
