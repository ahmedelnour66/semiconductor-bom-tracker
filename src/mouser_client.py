"""
Mouser Search API client — free alternative to Nexar's paid-gated evaluation
tier. Adapts Mouser's response into the SAME shape nexar_client.py produces,
so risk_engine.py doesn't need to change no matter which source you use.

Docs: https://www.mouser.com/en/api-search/
Sign-up: My Mouser Account -> API page -> request Search API access.
Approval typically takes 1-2 business days.

IMPORTANT — read before trusting this file:
I could not verify the exact response field names against Mouser's official
Search API Developer Guide (I only found a Cart/Order API guide, plus
several independent third-party clients that agree with each other on
field names like ManufacturerPartNumber, LifecycleStatus, Availability,
LeadTime). They're consistent enough to be a solid starting point, but NOT
confirmed against Mouser's own docs. Once your key is approved:
  1. Run this file directly: `python -m src.mouser_client`
  2. Compare the printed raw JSON against what `_normalize()` below assumes
  3. Fix any mismatches before running main.py for real

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
            results = data.get("SearchResults") or {}
            for raw_part in results.get("Parts", []) or []:
                all_parts.append(_normalize(raw_part))
        return {"hits": len(all_parts), "parts": all_parts}


def _chunk(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _normalize(raw: dict) -> dict:
    """Convert Mouser's raw part JSON into the shape risk_engine.py expects.
    VERIFY field names against a real response (see module docstring) before
    trusting this in production."""
    mpn = raw.get("ManufacturerPartNumber", "")
    lifecycle = raw.get("LifecycleStatus", "") or ""
    lead_days = _parse_lead_days(raw.get("LeadTime", "") or "")
    stock = _parse_stock(raw.get("Availability", "") or "")

    return {
        "mpn": mpn,
        "specs": [
            {"attribute": {"name": "lifecyclestatus"}, "value": lifecycle, "displayValue": lifecycle}
        ],
        "sellers": [
            {
                "company": {"name": "Mouser"},
                "offers": [{"inventoryLevel": stock, "factoryLeadDays": lead_days}],
            }
        ],
    }


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
