from pathlib import Path

import numpy as np
import pandas as pd

TABLES = Path("output/tables")


def build_district_table(
    agg_ipress: pd.DataFrame,
    agg_ccpp: pd.DataFrame,
    agg_emerg: pd.DataFrame,
    distritos: pd.DataFrame,
) -> pd.DataFrame:
    """Merge all district-level aggregates into one flat table."""
    base = distritos[["ubigeo", "departamen", "provincia", "distrito"]].copy()
    base = base.rename(columns={"departamen": "departamento"})

    df = (
        base
        .merge(agg_ipress, on="ubigeo", how="left")
        .merge(agg_ccpp[["ubigeo", "n_ccpp", "avg_dist_km", "max_dist_km"]], on="ubigeo", how="left")
        .merge(agg_emerg[["ubigeo", "total_atenciones", "total_atendidos"]], on="ubigeo", how="left")
    )

    df["n_ipress"] = df["n_ipress"].fillna(0).astype(int)
    df["n_camas"] = df["n_camas"].fillna(0)
    df["n_ccpp"] = df["n_ccpp"].fillna(0).astype(int)
    return df.reset_index(drop=True)


def _minmax(series: pd.Series) -> pd.Series:
    """Normalize a series to [0, 1]; returns 0.5 if constant."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)


def compute_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Baseline: supply-side score.
    Measures how many facilities and beds exist relative to populated centers.
    Higher = better access.
    """
    df = df.copy()
    # Avoid division by zero
    n_ccpp = df["n_ccpp"].replace(0, np.nan)

    df["ipress_per_ccpp"] = df["n_ipress"] / n_ccpp
    df["camas_per_ccpp"] = df["n_camas"] / n_ccpp

    # Normalize each component to [0,1] then average
    score = (
        _minmax(df["ipress_per_ccpp"].fillna(0)) * 0.6
        + _minmax(df["camas_per_ccpp"].fillna(0)) * 0.4
    )
    df["baseline_score"] = (score * 100).round(2)
    return df


def compute_alternative(df: pd.DataFrame) -> pd.DataFrame:
    """
    Alternative: distance-penalized supply score.
    Same supply indicators but penalized by avg distance from populated
    centers to nearest IPRESS. Captures spatial friction.
    Higher = better access.
    """
    df = df.copy()
    n_ccpp = df["n_ccpp"].replace(0, np.nan)
    dist = df["avg_dist_km"].fillna(df["avg_dist_km"].median())

    # Distance penalty: facilities per ccpp discounted by distance
    df["ipress_per_ccpp_dist"] = df["n_ipress"] / (n_ccpp * (1 + dist))
    df["camas_per_ccpp_dist"] = df["n_camas"] / (n_ccpp * (1 + dist))

    score = (
        _minmax(df["ipress_per_ccpp_dist"].fillna(0)) * 0.6
        + _minmax(df["camas_per_ccpp_dist"].fillna(0)) * 0.4
    )
    df["alternative_score"] = (score * 100).round(2)
    return df


def compute_metrics(
    agg_ipress: pd.DataFrame,
    agg_ccpp: pd.DataFrame,
    agg_emerg: pd.DataFrame,
    distritos: pd.DataFrame,
) -> pd.DataFrame:
    """Full pipeline: merge, score (baseline + alternative), save table."""
    df = build_district_table(agg_ipress, agg_ccpp, agg_emerg, distritos)
    df = compute_baseline(df)
    df = compute_alternative(df)

    # Score difference: positive = baseline overestimates access vs distance-adjusted
    df["score_diff"] = (df["baseline_score"] - df["alternative_score"]).round(2)

    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / "district_metrics.csv", index=False)
    print(f"Saved district_metrics.csv ({len(df)} districts)")
    return df
