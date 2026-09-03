"""Extract pricing for a part at a specific order quantity.

Distributor prices come in quantity tiers (e.g. $7.97 at qty 1, $4.35 at
qty 250). This picks the tier that actually applies to what's being ordered.
Kept separate from risk_engine.py on purpose — pricing isn't risk, and
mixing them would make both harder to change independently.
"""

from typing import Optional


def price_at_qty(part: dict, qty: int) -> Optional[float]:
    """Return the per-unit price that applies at the given order quantity,
    or None if no pricing data is available for this part."""
    prices = _all_prices(part)
    if not prices:
        return None

    applicable = [p for p in prices if p.get("quantity", 0) <= qty]
    chosen = max(applicable, key=lambda p: p["quantity"]) if applicable \
        else min(prices, key=lambda p: p["quantity"])
    return chosen.get("price")


def _all_prices(part: dict) -> list[dict]:
    out = []
    for seller in part.get("sellers", []) or []:
        for offer in seller.get("offers", []) or []:
            out.extend(offer.get("prices", []) or [])
    return out
