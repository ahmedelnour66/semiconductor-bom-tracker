"""
CLI entry point for the concierge MVP.

You run this by hand for each pilot customer's BOM — no dashboard, no
accounts, no server. That's intentional: prove people want the output
before building the self-serve product around it.

Usage:
    python main.py --bom data/sample_bom.csv --out report.xlsx
"""

import argparse

from src.bom_parser import load_bom
from src.nexar_client import NexarClient
from src.risk_engine import assess_part
from src.report import write_report


def run(bom_path: str, out_path: str):
    bom = load_bom(bom_path)
    client = NexarClient()

    mpns = bom["mpn"].tolist()
    print(f"Looking up {len(mpns)} parts on Nexar...")
    result = client.lookup_mpns(mpns)

    parts_by_mpn = {}
    for item in result:
        if isinstance(item, dict):
            for p in item.get("parts", []):
                parts_by_mpn[p["mpn"].upper()] = p

    rows = []
    for _, line in bom.iterrows():
        part = parts_by_mpn.get(line["mpn"])
        assessment = assess_part(part, requested_qty=int(line.get("qty", 0) or 0))
        rows.append({
            "mpn": line["mpn"],
            "manufacturer": line["manufacturer"],
            "qty": line.get("qty"),
            **assessment,
        })

    write_report(rows, out_path)
    print(f"Report written to {out_path}")

    n_high = sum(1 for r in rows if r["risk"] == "HIGH")
    n_med = sum(1 for r in rows if r["risk"] == "MEDIUM")
    print(f"Summary: {n_high} HIGH risk, {n_med} MEDIUM risk, {len(rows) - n_high - n_med} other")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assess BOM component risk via Nexar")
    parser.add_argument("--bom", required=True, help="Path to customer BOM CSV")
    parser.add_argument("--out", default="report.xlsx", help="Output report path (.xlsx or .csv)")
    args = parser.parse_args()
    run(args.bom, args.out)
