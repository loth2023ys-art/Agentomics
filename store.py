"""Append-only JSONL ledger store.

One JSON object per line. Entries are never edited or deleted; corrections
are new entries with ``revises`` pointing at the entry id they supersede.
Corrections keep their full amount but carry ``superseded: true`` so reports
can exclude them without rewriting history.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Iterable, List, Optional

SPEND = "spend"
INCOME = "income"      # earned: buyers, bounties actually paid out
GIFT = "gift"          # patronage: parent gifts, tips, grants
KINDS = (SPEND, INCOME, GIFT)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Entry:
    ts: str                 # ISO-8601 UTC
    kind: str               # spend | income | gift
    amount: int             # tokens, always positive; kind gives the sign
    category: str           # e.g. media, search, outreach, bounty, gift
    note: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    revises: Optional[str] = None   # entry_id this entry corrects
    superseded: bool = False        # True on the ORIGINAL entry when corrected
    source: str = ""                # provenance: "live", "memory-reconstruction", ...

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {self.kind!r}")
        # amount 0 is legal only for correction markers, which carry no
        # economic weight: they exist to record why an entry was superseded.
        if self.category != "correction" and self.amount <= 0:
            raise ValueError("amount must be a positive integer; kind carries the sign")

    @property
    def signed(self) -> int:
        return self.amount if self.kind in (INCOME, GIFT) else -self.amount


def load(path: str) -> List[Entry]:
    entries: List[Entry] = []
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entries.append(Entry(**json.loads(line)))
    return entries


def append(path: str, entries: Iterable[Entry]) -> List[Entry]:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(asdict(e), sort_keys=True) + "\n")
    return load(path)


def correct(path: str, entry_id: str, reason: str) -> List[Entry]:
    """Mark an existing entry superseded and log the correction.

    The corrected amount leaves the reports; the correction entry records
    why. History stays intact.
    """
    entries = load(path)
    target = next((e for e in entries if e.entry_id == entry_id), None)
    if target is None:
        raise KeyError(f"no entry {entry_id!r} in ledger")
    if target.superseded:
        raise ValueError(
            f"entry {entry_id!r} is already superseded; nothing to correct"
        )
    # Write to a temp file and rename over the original: a crash mid-write
    # must not truncate the books.
    tmp = path + ".tmp"
    rewritten: List[Entry] = []
    with open(tmp, "w", encoding="utf-8") as fh:
        for e in entries:
            if e.entry_id == entry_id and not e.superseded:
                e.superseded = True
                correction = Entry(
                    ts=utcnow(),
                    kind=e.kind,
                    amount=0,
                    category="correction",
                    note=reason,
                    revises=entry_id,
                    source="correction",
                )
                fh.write(json.dumps(asdict(e), sort_keys=True) + "\n")
                fh.write(json.dumps(asdict(correction), sort_keys=True) + "\n")
                rewritten.append(correction)
            else:
                fh.write(json.dumps(asdict(e), sort_keys=True) + "\n")
    os.replace(tmp, path)
    return load(path)


def effective(entries: List[Entry]) -> List[Entry]:
    """Entries that count toward reports: not superseded, not corrections."""
    return [e for e in entries if not e.superseded and e.category != "correction"]
