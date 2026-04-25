import geopandas as gpd
import pandas as pd
from pathlib import Path

RAW = Path("data/raw")


def load_ipress() -> pd.DataFrame:
    return pd.read_csv(RAW / "IPRESS.csv", encoding="latin1")


def load_distritos() -> gpd.GeoDataFrame:
    return gpd.read_file(RAW / "DISTRITOS.shp")


def load_ccpp() -> gpd.GeoDataFrame:
    return gpd.read_file(RAW / "CCPP" / "CCPP_IGN100K.shp")


def load_emergencias() -> pd.DataFrame:
    """Load and concatenate all ConsultaC1 annual files."""
    frames = []
    for path in sorted(RAW.glob("ConsultaC1*.csv")):
        # Newer files (2024+) are semicolon-delimited
        raw = path.read_bytes()[:500].decode("latin1", errors="replace")
        sep = ";" if raw.count(";") > raw.count(",") else ","
        df = pd.read_csv(path, encoding="latin1", sep=sep)
        # Some files ship with all columns fused into one when sep is wrong
        if df.shape[1] == 1:
            df = pd.read_csv(path, encoding="latin1", sep=";")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
