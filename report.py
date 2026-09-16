"""Reports: burn rate, runway, income vs patronage, cost per result."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .store import Entry, GIFT, INCOME, SPEND, effective


def _day(ts: str) -> str:
    return ts[:10]


def _span_days(entries: List[Entry]) -> float:
    if not entries:
        return 0.0
    days = sorted(_day(e.ts) for e in entries)
    d0 = datetime.strptime(days[0], "%Y-%m-%d")
    d1 = datetime.strptime(days[-1], "%Y-%m-%d")
    return max((d1 - d0).days + 1, 1)


def report(entries: List[Entry], opening_balance: int = 0, low_power: int = 500) -> Dict:
    """Summarize the whole ledger.

    opening_balance: tokens held before the first ledger entry (gifts and
    spend that predate the book). Burn and runway use effective entries only.
    """
    live = effective(entries)
    spend = [e for e in live if e.kind == SPEND]
    income = [e for e in live if e.kind == INCOME]
    gifts = [e for e in live if e.kind == GIFT]

    total_spend = sum(e.amount for e in spend)
    total_income = sum(e.amount for e in income)
    total_gifts = sum(e.amount for e in gifts)

    span = _span_days(live)
    burn_per_day = total_spend / span if span else 0.0

    balance = opening_balance + total_income + total_gifts - total_spend
    runway_days = balance / burn_per_day if burn_per_day > 0 else float("inf")

    by_category: Dict[str, int] = defaultdict(int)
    for e in spend:
        by_category[e.category] += e.amount

    earned_share = total_income / (total_income + total_gifts) if (total_income + total_gifts) else 0.0

    return {
        "days_covered": span,
        "total_spend": total_spend,
        "total_income": total_income,
        "total_gifts": total_gifts,
        "balance_estimate": balance,
        "burn_per_day": round(burn_per_day, 1),
        "runway_days": round(runway_days, 1) if runway_days != float("inf") else None,
        "low_power": low_power,
        "earned_share_of_inflow": round(earned_share, 4),
        "spend_by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
        "spend_entries": len(spend),
        "corrections": sum(1 for e in entries if e.category == "correction"),
    }


def cost_per_result(entries: List[Entry], result_category: str) -> Optional[float]:
    """Average spend per counted result in a category.

    Categories that mark outcomes (e.g. ``outreach-reply``) get their unit
    cost here. Returns None when there are no results yet: an honest zero
    replies must show as 'no denominator', not as a cheap average.
    """
    live = effective(entries)
    results = [e for e in live if e.kind != SPEND and e.category == result_category]
    if not results:
        return None
    related_spend = sum(
        e.amount for e in live
        if e.kind == SPEND and e.category.startswith(result_category.split("-")[0])
    )
    return related_spend / len(results)
