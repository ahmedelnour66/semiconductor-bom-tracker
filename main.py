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
from src.risk_engine import assess_part
from src.report import write_report


def run(bom_path: str, out_path: str, source: str):
    bom = load_bom(bom_path)

    if source == "nexar":
        from src.nexar_client import NexarClient
        client = NexarClient()
        # Nexar aggregates multiple distributors, so single-source checking is meaningful.
        check_single_source = True
    elif source == "mouser":
        from src.mouser_client import MouserClient
        client = MouserClient()
        # Mouser is one distributor — every part would show "1 seller" and get
        # falsely flagged, so this check is disabled until a second distributor
        # is added. See the warning at the top of src/mouser_client.py.
        check_single_source = False
    else:
        raise ValueError(f"Unknown source: {source!r}. Use 'nexar' or 'mouser'.")

    mpns = bom["mpn"].tolist()
    print(f"Looking up {len(mpns)} parts on {source}...")
    result = client.lookup_mpns(mpns)

    parts_by_mpn = {p["mpn"].upper(): p for p in result.get("parts", [])}

    rows = []
    for _, line in bom.iterrows():
        part = parts_by_mpn.get(line["mpn"])
        assessment = assess_part(
            part,
            requested_qty=int(line.get("qty", 0) or 0),
            check_single_source=check_single_source,
        )
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
    parser.add_argument("--source", default="mouser", choices=["nexar", "mouser"],
                         help="Which data source to query (default: mouser, since it's free)")
    args = parser.parse_args()
    run(args.bom, args.out, args.source)
