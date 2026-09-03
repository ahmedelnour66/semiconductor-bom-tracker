"""
Mouser Search API client — free alternative to Nexar's paid-gated evaluation
tier. Adapts Mouser's response into the SAME shape nexar_client.py produces,
so risk_engine.py doesn't need to change no matter which source you use.

Docs: https://www.mouser.com/en/api-search/
Sign-up: My Mouser Account -> API page -> request Search API access.
Approval typically takes 1-2 business days.

IMPORTANT — read before trusting this file:
Verified against a real response on 2026-09-01: ManufacturerPartNumber,
Availability, and LeadTime all match the format assumed below (LeadTime
comes back as "N Days", e.g. "280 Days" — the parser already handles this
correctly since it only multiplies by 7 when it sees "week").

One real caveat, not a bug: LifecycleStatus came back `null` for a known
in-production part (STM32F103C8T6). This suggests Mouser doesn't reliably
populate lifecycle/obsolescence status the way Nexar's dedicated spec
attribute does. Treat the "obsolescence" risk flag as weaker signal when
running on Mouser-only data — it may simply not fire even for genuinely
risky parts, since the underlying field is often empty.

IMPORTANT — a real limitation, not just a technical detail:
Mouser is ONE distributor. The "single or no distributor source" risk flag
in risk_engine.py was designed assuming Nexar-style aggregation across many
distributors (Mouser, Digi-Key, etc.) — with Mouser alone, every part will
always show as "1 seller found" and get flagged, even if it's readily
available elsewhere. Either disable that specific check while running on
Mouser-only data, or treat its output as "in stock at Mouser or not" rather
than genuine single-sourcing risk, until you add a second distributor.
"""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

SEARCH_URL = "https://api.mouser.com/api/v1/search/partnumber"
API_KEY = os.getenv("MOUSER_API_KEY")


class MouserClient:
    def __init__(self):
        if not API_KEY:
            raise RuntimeError(
                "Missing MOUSER_API_KEY. Copy .env.example to .env and add "
                "the key Mouser emails you after approving your Search API "
                "request (mouser.com/en/api-search)."
            )
        self._client = httpx.Client(timeout=30)

    def lookup_mpns(self, mpns: list[str]) -> dict:
        """Batch lookup, up to 10 MPNs per call (pipe-delimited) to conserve quota."""
        all_parts = []
        for batch in _chunk(mpns, 10):
            query = "|".join(batch)
            resp = self._client.post(
                SEARCH_URL,
                params={"apiKey": API_KEY},
                json={
                    "SearchByPartRequest": {
                        "mouserPartNumber": query,
                        "partSearchOptions": "Exact",
                    }
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("Errors"):
                raise RuntimeError(f"Mouser API error: {data['Errors']}")
            results = data.get("SearchResults") or {}
            for raw_part in results.get("Parts", []) or []:
                all_parts.append(_normalize(raw_part))
        return {"hits": len(all_parts), "parts": all_parts}


def _chunk(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _normalize(raw: dict) -> dict:
    """Convert Mouser's raw part JSON into the shape risk_engine.py expects,
    plus extra descriptive fields (description, datasheet_url, price breaks)
    for use in the report."""
    mpn = raw.get("ManufacturerPartNumber", "")
    lifecycle = raw.get("LifecycleStatus", "") or ""
    lead_days = _parse_lead_days(raw.get("LeadTime", "") or "")
    stock = _parse_stock(raw.get("Availability", "") or "")
    prices = _parse_price_breaks(raw.get("PriceBreaks", []) or [])

    return {
        "mpn": mpn,
        "description": raw.get("Description", "") or "",
        "datasheet_url": raw.get("DataSheetUrl", "") or "",
        "specs": [
            {"attribute": {"name": "lifecyclestatus"}, "value": lifecycle, "displayValue": lifecycle}
        ],
        "sellers": [
            {
                "company": {"name": "Mouser"},
                "offers": [{"inventoryLevel": stock, "factoryLeadDays": lead_days, "prices": prices}],
            }
        ],
    }


def _parse_price_breaks(raw_breaks: list) -> list[dict]:
    """Mouser's PriceBreaks: [{"Quantity": 10, "Price": "$5.57", "Currency": "USD"}, ...]"""
    out = []
    for pb in raw_breaks:
        price = _parse_price(pb.get("Price", "") or "")
        if price is None:
            continue
        out.append({
            "quantity": pb.get("Quantity", 0),
            "price": price,
            "currency": pb.get("Currency", "USD"),
        })
    return out


def _parse_price(price_str: str) -> Optional[float]:
    """Mouser returns price as a string like '$5.57'."""
    cleaned = price_str.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_stock(availability_str: str) -> int:
    """Mouser returns availability as a string like '1,234 In Stock'."""
    digits = "".join(c for c in availability_str if c.isdigit())
    return int(digits) if digits else 0


def _parse_lead_days(lead_time_str: str) -> Optional[int]:
    """Format varies (e.g. '12 Weeks') — verify against a real response."""
    if not lead_time_str:
        return None
    digits = "".join(c for c in lead_time_str if c.isdigit())
    if not digits:
        return None
    n = int(digits)
    return n * 7 if "week" in lead_time_str.lower() else n


if __name__ == "__main__":
    # Sanity check: after adding MOUSER_API_KEY to .env, run:
    #   python -m src.mouser_client
    # and compare the raw JSON against what _normalize() above assumes.
    import json
    client = MouserClient()
    resp = client._client.post(
        SEARCH_URL,
        params={"apiKey": API_KEY},
        json={"SearchByPartRequest": {"mouserPartNumber": "STM32F103C8T6", "partSearchOptions": "Exact"}},
    )
    print(json.dumps(resp.json(), indent=2))
