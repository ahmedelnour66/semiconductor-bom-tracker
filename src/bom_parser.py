"""Parse a customer's BOM (CSV) into a normalized list of parts to look up."""

import pandas as pd

REQUIRED_COLUMNS = {"manufacturer", "mpn", "qty"}


def load_bom(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"BOM is missing required columns: {missing}. "
            f"Expected at least: {sorted(REQUIRED_COLUMNS)}"
        )

    df["mpn"] = df["mpn"].astype(str).str.strip().str.upper()
    df["manufacturer"] = df["manufacturer"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["mpn"]).reset_index(drop=True)
    return df
