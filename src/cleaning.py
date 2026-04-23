import pandas as pd


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.drop_duplicates()
    return df
