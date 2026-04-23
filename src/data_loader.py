import pandas as pd
from pathlib import Path

RAW = Path("data/raw")


def load_data(filename: str) -> pd.DataFrame:
    path = RAW / filename
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file format: {suffix}")
