import geopandas as gpd
import pandas as pd


def build_geodataframe(df: pd.DataFrame, lat_col: str, lon_col: str, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs=crs)


def spatial_join(points: gpd.GeoDataFrame, polygons: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gpd.sjoin(points, polygons, how="left", predicate="within")
