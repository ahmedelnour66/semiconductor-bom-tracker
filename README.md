# Semiconductor BOM Risk Tracker — Concierge MVP

A stripped-down tool that takes a customer's Bill of Materials (BOM) and
flags components at risk of obsolescence, low stock, single-sourcing, or
long lead times — using live data from the Nexar (Octopart) API.

This is deliberately **not** a web app yet. You run it by hand for each
pilot customer and send them the report. No dashboard, no accounts, no
server to maintain. Build that only once people are actually paying for
the output.

## What's here

```
semiconductor-bom-tracker/
├── main.py              # CLI entry point — run this
├── src/
│   ├── nexar_client.py  # Talks to the Nexar API (auth + part lookup)
│   ├── bom_parser.py    # Reads and cleans a customer's BOM CSV
│   ├── risk_engine.py   # The actual risk scoring logic — your core IP
│   └── report.py        # Writes the output spreadsheet
├── data/
│   └── sample_bom.csv   # Test data — use this before touching a real BOM
├── requirements.txt
└── .env.example         # Copy to .env and fill in your own credentials
```

## Setup (do this once)

1. **Install Python 3.11+** if you don't have it: https://www.python.org/downloads/
   Check with `python3 --version`.

2. **Get Nexar API credentials** (free tier exists):
   - Sign up at https://nexar.com
   - Go to your API dashboard, create an "App"
   - Under the app's Authorization tab, request the `supply.domain` scope
   - Copy the Client ID and Client Secret

3. **Clone/copy this project**, then from inside the folder:

   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

   Open `.env` and paste in your real Client ID / Secret.

4. **Verify the Nexar query still matches their schema.** Their GraphQL
   schema evolves — before your first real run, open
   https://api.nexar.com/graphql/, paste in the query from
   `src/nexar_client.py` (`QUERY_TEMPLATE`), and confirm it returns data
   without errors. Fix any field name mismatches there first — it's much
   faster to debug in the Playground than in your own code.

## Running it

```bash
python main.py --bom data/sample_bom.csv --out report.xlsx
```

This prints a summary and writes `report.xlsx` with a risk flag and reason
per part.

## Using it with a real pilot customer

1. Get their BOM as a CSV with at minimum `manufacturer`, `mpn`, `qty` columns
   (extra columns like `designator` are fine — they're ignored).
2. Run the command above pointing at their file.
3. Open the resulting spreadsheet, sanity-check a few HIGH-risk lines
   manually against the Nexar Playground or the distributor site directly
   — don't send a report to a paying customer you haven't spot-checked.
4. Send it over, and actually get on a call to hear what they think.

## Next steps once this validates

- Tune `risk_engine.py` thresholds based on what pilot customers say is
  actually useful vs. noise.
- Add historical tracking (store results in a database) so you can alert
  on *changes*, not just point-in-time status — this is usually more
  valuable than a one-off report.
- Only then: build a web UI / accounts, so customers can self-serve
  instead of you running this by hand.

## A note on licensing before you charge for this

Check Nexar's terms of service for any restrictions on reselling or
redistributing their data as part of a commercial product before you
start invoicing customers. Terms can change — verify current terms
directly with Nexar rather than assuming.
