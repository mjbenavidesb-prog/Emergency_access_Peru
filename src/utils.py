from pathlib import Path


def ensure_dirs() -> None:
    for folder in ("data/raw", "data/processed", "output/figures", "output/tables"):
        Path(folder).mkdir(parents=True, exist_ok=True)
