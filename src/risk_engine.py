"""
Turn raw Nexar part data into a per-line risk assessment.

Deliberately simple to start: three checks that cover most of what a small
manufacturer actually cares about (obsolescence, stock, single-sourcing,
lead time). Add more once pilot customers tell you what they actually need —
don't guess ahead of real feedback.
"""

from typing import Optional

EOL_STATUSES = {"obsolete", "eol", "end of life", "nrnd", "not recommended for new designs"}
LOW_STOCK_THRESHOLD = 100
LONG_LEAD_TIME_DAYS = 26 * 7  # ~6 months — adjust for your target industry


def _get_spec(part: dict, attribute_name: str) -> Optional[str]:
    for spec in part.get("specs", []):
        if spec["attribute"]["name"].lower() == attribute_name.lower():
            return spec.get("displayValue") or spec.get("value")
    return None


def assess_part(part: Optional[dict], requested_qty: int, check_single_source: bool = True) -> dict:
    if part is None:
        return {
            "risk": "UNKNOWN",
            "reason": "Part not found on Nexar — verify MPN or check manually",
        }

    lifecycle = (_get_spec(part, "lifecyclestatus") or "").lower()
    sellers = part.get("sellers", []) or []

    total_stock = sum(
        (offer.get("inventoryLevel") or 0)
        for seller in sellers
        for offer in (seller.get("offers") or [])
    )
    lead_times = [
        offer.get("factoryLeadDays")
        for seller in sellers
        for offer in (seller.get("offers") or [])
        if offer.get("factoryLeadDays")
    ]
    max_lead_time = max(lead_times) if lead_times else None

    flags = []
    if any(status in lifecycle for status in EOL_STATUSES):
        flags.append(f"Lifecycle status: {lifecycle}")
    if total_stock < max(LOW_STOCK_THRESHOLD, requested_qty):
        flags.append(f"Low stock across distributors: {total_stock} units")
    if check_single_source and len(sellers) <= 1:
        flags.append(f"Single or no distributor source ({len(sellers)} found)")
    if max_lead_time and max_lead_time > LONG_LEAD_TIME_DAYS:
        flags.append(f"Long lead time: {max_lead_time} days")

    if not flags:
        risk = "LOW"
    elif any(f.startswith("Lifecycle") for f in flags):
        risk = "HIGH"
    else:
        risk = "MEDIUM"

    return {"risk": risk, "reason": "; ".join(flags) if flags else "No issues found"}
