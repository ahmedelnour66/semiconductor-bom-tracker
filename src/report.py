"""Write the risk assessment out to a spreadsheet a non-technical customer can open."""

import pandas as pd


def write_report(rows: list[dict], out_path: str):
    df = pd.DataFrame(rows)
    col_order = ["mpn", "manufacturer", "qty", "risk", "reason"]
    df = df[[c for c in col_order if c in df.columns]]

    if out_path.endswith(".xlsx"):
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="BOM Risk Report")
    else:
        df.to_csv(out_path, index=False)
