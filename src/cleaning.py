from pathlib import Path

import geopandas as gpd
import pandas as pd

PROCESSED = Path("data/processed")


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[áà]", "a", regex=True)
        .str.replace(r"[éè]", "e", regex=True)
        .str.replace(r"[íì]", "i", regex=True)
        .str.replace(r"[óò]", "o", regex=True)
        .str.replace(r"[úù]", "u", regex=True)
        .str.replace(r"[ñ]", "n", regex=True)
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^\w]", "_", regex=True)
    )
    return df


def _pad_ubigeo(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.zfill(6)


def clean_ipress(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize_cols(df).drop_duplicates()
    # In this dataset NORTE contains longitude values and ESTE contains latitude values
    df = df.rename(columns={"norte": "lon", "este": "lat"})
    df["ubigeo"] = _pad_ubigeo(df["ubigeo"])
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df[df["estado"].str.upper().str.strip() == "ACTIVADO"] if "estado" in df.columns else df
    return df.reset_index(drop=True)


def clean_distritos(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf.columns = [c.lower() for c in gdf.columns]
    # Build a 6-digit UBIGEO from the numeric district id stored as IDDIST
    gdf["ubigeo"] = _pad_ubigeo(gdf["iddist"])
    return gdf


def clean_ccpp(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = _normalize_cols(gdf).drop_duplicates()
    # CÓDIGO is a 10-digit code; first 6 digits are the district UBIGEO
    code_col = next(c for c in gdf.columns if "digo" in c and "int" not in c)
    gdf["ubigeo"] = gdf[code_col].astype(str).str[:6].str.zfill(6)
    return gdf.reset_index(drop=True)


def clean_emergencias(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize_cols(df).drop_duplicates()
    df["ubigeo"] = _pad_ubigeo(df["ubigeo"])
    df["nro_total_atenciones"] = pd.to_numeric(df["nro_total_atenciones"], errors="coerce")
    df["nro_total_atendidos"] = pd.to_numeric(df["nro_total_atendidos"], errors="coerce")
    # Newer files (2018+) store totals in nu_total_atendidos instead
    if "nu_total_atendidos" in df.columns:
        nu = pd.to_numeric(df["nu_total_atendidos"], errors="coerce")
        df["nro_total_atendidos"] = df["nro_total_atendidos"].fillna(nu)
        df["nro_total_atenciones"] = df["nro_total_atenciones"].fillna(nu)
        df = df.drop(columns=["nu_total_atendidos"], errors="ignore")
    # Drop rows with no attendance data at all
    df = df.dropna(subset=["nro_total_atenciones", "nro_total_atendidos"], how="all")
    return df.reset_index(drop=True)


def save_processed(ipress: pd.DataFrame, distritos: gpd.GeoDataFrame,
                   ccpp: gpd.GeoDataFrame, emerg: pd.DataFrame) -> None:
    """Persist all cleaned datasets to data/processed/."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ipress.to_csv(PROCESSED / "ipress_clean.csv", index=False)
    distritos.to_file(PROCESSED / "distritos_clean.gpkg", driver="GPKG")
    ccpp.to_file(PROCESSED / "ccpp_clean.gpkg", driver="GPKG")
    emerg.to_csv(PROCESSED / "emergencias_clean.csv", index=False)
    print(f"Saved cleaned files to {PROCESSED.resolve()}")
