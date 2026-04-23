import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

FIGURES = Path("output/figures")


def plot_map(gdf: gpd.GeoDataFrame, column: str, title: str = "") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(column=column, ax=ax, legend=True, cmap="YlOrRd")
    ax.set_title(title)
    ax.axis("off")
    return fig


def plot_chart(df: pd.DataFrame, x: str, y: str, title: str = "") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df[x], df[y])
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    return fig


def save_figure(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
