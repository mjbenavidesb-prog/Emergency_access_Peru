import geopandas as gpd
import pandas as pd

# Peru falls mostly in UTM zone 18S — metric CRS for distance calculations
CRS_METRIC = "EPSG:32718"
CRS_GEO = "EPSG:4326"


def build_ipress_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Convert cleaned IPRESS DataFrame to GeoDataFrame using NORTE/ESTE columns."""
    valid = df.dropna(subset=["lat", "lon"]).copy()
    return gpd.GeoDataFrame(
        valid,
        geometry=gpd.points_from_xy(valid["lon"], valid["lat"]),
        crs=CRS_GEO,
    )


def sjoin_to_distritos(
    points: gpd.GeoDataFrame, distritos: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Spatial join: assign district attributes to each point (left join)."""
    # Align CRS
    if points.crs != distritos.crs:
        points = points.to_crs(distritos.crs)
    joined = gpd.sjoin(points, distritos[["ubigeo", "distrito", "provincia", "departamen", "geometry"]], how="left", predicate="within")
    joined = joined.drop(columns=["index_right"], errors="ignore")
    # Prefer the spatially-derived ubigeo over the tabular one
    if "ubigeo_right" in joined.columns:
        joined["ubigeo"] = joined["ubigeo_right"].fillna(joined.get("ubigeo_left", joined["ubigeo_right"]))
        joined = joined.drop(columns=["ubigeo_left", "ubigeo_right"], errors="ignore")
    return joined


def compute_nearest_ipress_distance(
    ccpp: gpd.GeoDataFrame, ipress: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    For each populated center, find the distance (km) to the nearest IPRESS.
    Returns ccpp with added columns: nearest_ipress, dist_km.
    """
    ccpp_m = ccpp.to_crs(CRS_METRIC).copy()
    ipress_m = ipress.to_crs(CRS_METRIC).copy()

    result = gpd.sjoin_nearest(
        ccpp_m,
        ipress_m[["nombre_del_establecimiento", "categoria", "geometry"]],
        how="left",
        distance_col="dist_m",
    )
    result = result.drop(columns=["index_right"], errors="ignore")
    result["dist_km"] = result["dist_m"] / 1000
    return result.to_crs(CRS_GEO)


def aggregate_ipress_by_district(ipress_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Count facilities and beds per district."""
    return (
        ipress_gdf.groupby("ubigeo")
        .agg(
            n_ipress=("ubigeo", "count"),
            n_camas=("camas", "sum"),
        )
        .reset_index()
    )


def aggregate_ccpp_by_district(ccpp_with_district: gpd.GeoDataFrame) -> pd.DataFrame:
    """Count populated centers per district."""
    return (
        ccpp_with_district.groupby("ubigeo")
        .agg(
            n_ccpp=("ubigeo", "count"),
            avg_dist_km=("dist_km", "mean"),
            max_dist_km=("dist_km", "max"),
        )
        .reset_index()
    )


def aggregate_emergencias_by_district(emerg: pd.DataFrame, year: int = None) -> pd.DataFrame:
    """Sum emergency attendances per district, optionally filtered by year."""
    df = emerg.copy()
    if year is not None:
        df = df[df["anho"] == year]
    return (
        df.groupby("ubigeo")
        .agg(
            total_atenciones=("nro_total_atenciones", "sum"),
            total_atendidos=("nro_total_atendidos", "sum"),
        )
        .reset_index()
    )
