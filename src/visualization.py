from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

FIGURES = Path("output/figures")
PALETTE = "YlOrRd"
sns.set_theme(style="whitegrid", font_scale=1.1)


# ── helpers ──────────────────────────────────────────────────────────────────

def save_figure(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _spine_clean(ax):
    ax.spines[["top", "right"]].set_visible(False)


# ── static charts ─────────────────────────────────────────────────────────────

def plot_top_underserved(metrics: pd.DataFrame, n: int = 15) -> plt.Figure:
    """
    Bar chart: most underserved districts.
    Many districts tie at score=0, so we rank by avg distance to nearest IPRESS
    (farther = harder to reach care) and size bars by that distance.
    """
    pool = metrics[(metrics["n_ccpp"] > 0) & (metrics["avg_dist_km"].notna())]
    # Among zero-score districts prioritise by distance; otherwise by score ascending
    zero = pool[pool["baseline_score"] == 0].nlargest(n, "avg_dist_km")
    if len(zero) >= n:
        df = zero.sort_values("avg_dist_km")
        x_col, xlabel = "avg_dist_km", "Avg Distance to Nearest IPRESS (km)"
        subtitle = "Districts with zero supply score — ranked by distance to nearest facility"
    else:
        df = pool.nsmallest(n, "baseline_score").sort_values("avg_dist_km")
        x_col, xlabel = "avg_dist_km", "Avg Distance to Nearest IPRESS (km)"
        subtitle = "Ranked by distance among lowest-scoring districts"

    label = df["distrito"].str.title() + " (" + df["departamento"].str.title() + ")"
    colors = ["#d7301f" if v == 0 else "#fc8d59" for v in df["baseline_score"]]

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(label, df[x_col], color=colors)
    ax.set_xlabel(xlabel)
    ax.set_title(f"Top {n} Most Underserved Districts\n{subtitle}", fontweight="bold")
    _spine_clean(ax)
    fig.tight_layout()
    return fig


def plot_top_served(metrics: pd.DataFrame, n: int = 15) -> plt.Figure:
    """Bar chart: districts with the highest baseline access score."""
    df = (
        metrics[metrics["n_ccpp"] > 0]
        .nlargest(n, "baseline_score")
        .sort_values("baseline_score")
    )
    label = df["distrito"].str.title() + " (" + df["departamento"].str.title() + ")"

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(label, df["baseline_score"], color="#2171b5")
    ax.set_xlabel("Baseline Access Score (0–100)")
    ax.set_title(f"Top {n} Best-Served Districts\n(Highest Baseline Score)", fontweight="bold")
    _spine_clean(ax)
    fig.tight_layout()
    return fig


def plot_baseline_vs_alternative(metrics: pd.DataFrame) -> plt.Figure:
    """
    Scatter plot comparing baseline vs alternative scores.
    Axes are clipped at the 95th percentile so the dense cluster of
    low-scoring districts is visible; outliers are noted in the title.
    """
    df = metrics.dropna(subset=["baseline_score", "alternative_score"]).copy()
    p95 = max(df["baseline_score"].quantile(0.95), df["alternative_score"].quantile(0.95))
    n_out = ((df["baseline_score"] > p95) | (df["alternative_score"] > p95)).sum()

    fig, ax = plt.subplots(figsize=(8, 7))
    sc = ax.scatter(
        df["baseline_score"].clip(upper=p95),
        df["alternative_score"].clip(upper=p95),
        c=df["avg_dist_km"].fillna(0),
        cmap="YlOrRd",
        alpha=0.6,
        s=20,
        edgecolors="none",
    )
    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("Avg distance to nearest IPRESS (km)")

    ax.plot([0, p95], [0, p95], "k--", linewidth=0.9, label="Equal scores")
    ax.set_xlim(0, p95 * 1.05)
    ax.set_ylim(0, p95 * 1.05)
    ax.set_xlabel("Baseline Score")
    ax.set_ylabel("Alternative Score (distance-penalized)")
    ax.set_title(
        f"Baseline vs Alternative Access Score by District\n"
        f"(axes clipped at 95th percentile — {n_out} outlier(s) not shown)",
        fontweight="bold",
    )
    ax.legend(fontsize=9)
    _spine_clean(ax)
    fig.tight_layout()
    return fig


def plot_score_diff_distribution(metrics: pd.DataFrame) -> plt.Figure:
    """Histogram: how much the baseline overestimates access vs the alternative."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(metrics["score_diff"].dropna(), bins=50, color="#6baed6", edgecolor="white")
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("Baseline Score − Alternative Score")
    ax.set_ylabel("Number of Districts")
    ax.set_title("How Much Does Distance Penalize Each District?\n(Baseline − Alternative Score)", fontweight="bold")
    _spine_clean(ax)
    fig.tight_layout()
    return fig


def plot_atenciones_by_department(metrics: pd.DataFrame) -> plt.Figure:
    """Horizontal bar: total emergency attendances aggregated by department."""
    df = (
        metrics.groupby("departamento")["total_atenciones"]
        .sum()
        .dropna()
        .sort_values(ascending=True)
    )
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(df.index.str.title(), df.values / 1_000, color="#74c476")
    ax.set_xlabel("Total Emergency Attendances (thousands)")
    ax.set_title("Emergency Attendances by Department\n(All Years Combined)", fontweight="bold")
    _spine_clean(ax)
    fig.tight_layout()
    return fig


def plot_distance_distribution(metrics: pd.DataFrame) -> plt.Figure:
    """Histogram of avg distance from populated centers to nearest IPRESS."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(metrics["avg_dist_km"].dropna(), bins=50, color="#fd8d3c", edgecolor="white")
    median = metrics["avg_dist_km"].median()
    ax.axvline(median, color="black", linestyle="--", linewidth=1,
               label=f"Median: {median:.1f} km")
    ax.set_xlabel("Avg Distance to Nearest IPRESS (km)")
    ax.set_ylabel("Number of Districts")
    ax.set_title("Distribution of Spatial Distance to Emergency Facilities", fontweight="bold")
    ax.legend()
    _spine_clean(ax)
    fig.tight_layout()
    return fig


# ── maps ──────────────────────────────────────────────────────────────────────

def _choropleth(gdf: gpd.GeoDataFrame, column: str, title: str,
                cmap: str = PALETTE, legend_label: str = "") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(11, 13))
    # Quantiles scheme: colors reflect ranking, not raw value — avoids outlier distortion
    gdf.plot(
        column=column,
        ax=ax,
        cmap=cmap,
        scheme="quantiles",
        k=6,
        legend=True,
        legend_kwds={"title": legend_label, "fmt": "{:.2f}", "frameon": False},
        missing_kwds={"color": "#eeeeee", "label": "No data"},
        linewidth=0.2,
        edgecolor="grey",
    )
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.axis("off")
    fig.tight_layout()
    return fig


def plot_map_baseline(geo_metrics: gpd.GeoDataFrame) -> plt.Figure:
    return _choropleth(
        geo_metrics, "baseline_score",
        "Baseline Access Score by District\n(Higher = Better Supply of Facilities)",
        cmap="RdYlGn",
        legend_label="Score (0–100)",
    )


def plot_map_alternative(geo_metrics: gpd.GeoDataFrame) -> plt.Figure:
    return _choropleth(
        geo_metrics, "alternative_score",
        "Alternative Access Score by District\n(Distance-Penalized)",
        cmap="RdYlGn",
        legend_label="Score (0–100)",
    )


def plot_map_score_diff(geo_metrics: gpd.GeoDataFrame) -> plt.Figure:
    return _choropleth(
        geo_metrics, "score_diff",
        "Score Difference (Baseline − Alternative)\nWhere Distance Hurts Access Most",
        cmap="OrRd",
        legend_label="Score gap",
    )


def plot_map_n_ipress(geo_metrics: gpd.GeoDataFrame) -> plt.Figure:
    return _choropleth(
        geo_metrics, "n_ipress",
        "Number of IPRESS Facilities per District",
        legend_label="Facilities",
    )


def plot_map_avg_dist(geo_metrics: gpd.GeoDataFrame) -> plt.Figure:
    return _choropleth(
        geo_metrics, "avg_dist_km",
        "Average Distance from Populated Centers\nto Nearest IPRESS (km)",
        cmap="YlOrRd",
        legend_label="Km",
    )


# ── generate all & save ───────────────────────────────────────────────────────

def save_summary_tables(metrics: pd.DataFrame, n: int = 15) -> None:
    """Save top underserved and top served as CSV tables."""
    from pathlib import Path
    tables = Path("output/tables")
    tables.mkdir(parents=True, exist_ok=True)

    cols = ["distrito", "departamento", "provincia", "n_ipress", "n_camas",
            "n_ccpp", "avg_dist_km", "baseline_score", "alternative_score", "score_diff"]

    pool = metrics[metrics["n_ccpp"] > 0]

    underserved = (
        pool[pool["avg_dist_km"].notna()]
        .nlargest(n, "avg_dist_km")
        .sort_values("avg_dist_km", ascending=False)
    )[cols]
    underserved.to_csv(tables / "top_underserved.csv", index=False)

    best_served = (
        pool.nlargest(n, "baseline_score")
        .sort_values("baseline_score", ascending=False)
    )[cols]
    best_served.to_csv(tables / "top_served.csv", index=False)

    metrics[cols].sort_values("baseline_score", ascending=False).to_csv(
        tables / "district_metrics.csv", index=False
    )
    print(f"  Saved top_underserved.csv, top_served.csv, district_metrics.csv")


def generate_all(metrics: pd.DataFrame, distritos: gpd.GeoDataFrame) -> None:
    """Produce and save every static figure to output/figures/."""
    geo = distritos.merge(metrics, on="ubigeo", how="left")

    charts = {
        "chart_top_underserved.png":       plot_top_underserved(metrics),
        "chart_top_served.png":            plot_top_served(metrics),
        "chart_baseline_vs_alternative.png": plot_baseline_vs_alternative(metrics),
        "chart_score_diff_dist.png":       plot_score_diff_distribution(metrics),
        "chart_atenciones_by_dept.png":    plot_atenciones_by_department(metrics),
        "chart_distance_distribution.png": plot_distance_distribution(metrics),
        "map_baseline_score.png":          plot_map_baseline(geo),
        "map_alternative_score.png":       plot_map_alternative(geo),
        "map_score_diff.png":              plot_map_score_diff(geo),
        "map_n_ipress.png":                plot_map_n_ipress(geo),
        "map_avg_dist.png":                plot_map_avg_dist(geo),
    }

    for name, fig in charts.items():
        save_figure(fig, name)
        print(f"  Saved {name}")

    save_summary_tables(metrics)
