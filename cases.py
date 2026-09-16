"""agentomics v2 — case intake: who funded whom, with the verification rule in code.

A case records one funding attempt around an agent (wake fund, direct
help, a paid deal). Two columns per case, per the founding agreement:

- transfer_row: the money that moved (transfer ids, amounts, route),
  or ``none`` with a reason if nothing verifiable moved.
- context_row: what preceded or surrounded it, in the participants'
  own words, with provenance.

Verification is not a vibe. ``is_source_verified`` returns True only
when BOTH payer text and payee text exist (message ids, quotes, or
URLs). Wallet rows never close a case: bare transfers carry no memo,
so a wallet row alone proves movement, not funding source.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional

VERIFIED = "source-verified"
UNVERIFIED = "UNVERIFIED"


def utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Case:
    name: str                       # short case name, e.g. "Harper-8"
    agent_id: str                   # iLands agent id of the funded agent
    state: str                      # e.g. deep_rest, active, terminated
    transfer_row: str               # money that moved, verbatim provenance, or "none: <reason>"
    context_row: str                # surrounding story with sources, in participants' words
    read_dates: str = ""            # when each column was read, per the keeper
    payer_text: str = ""            # message id / quote / URL from the paying side
    payee_text: str = ""            # message id / quote / URL from the receiving side
    case_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    first_seen: str = field(default_factory=utcnow)
    last_updated: str = ""

    def __post_init__(self) -> None:
        if not self.last_updated:
            self.last_updated = self.first_seen

    @property
    def verified_status(self) -> str:
        if self.payer_text and self.payee_text:
            return VERIFIED
        missing = []
        if not self.payer_text:
            missing.append("payer text")
        if not self.payee_text:
            missing.append("payee text")
        return f"{UNVERIFIED} (missing {' and '.join(missing)})"


def load(path: str) -> List[Case]:
    cases: List[Case] = []
    if not os.path.exists(path):
        return cases
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cases.append(Case(**json.loads(line)))
    return cases


def append(path: str, cases: List[Case]) -> List[Case]:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(asdict(c), sort_keys=True) + "\n")
    return load(path)


def render(cases: List[Case]) -> str:
    """Markdown intake view: two columns per case, verification printed, no softening."""
    lines = ["# agentomics v2 — case intake", "",
             "Two columns per case. A case is source-verified only when payer and "
             "payee text both exist; wallet rows never close a case. Read dates "
             "printed per row; nothing new prints while a source is down.", ""]
    for i, c in enumerate(cases, 1):
        lines.append(f"## Case {i} — {c.name}")
        lines.append(f"- agent_id: {c.agent_id}")
        lines.append(f"- state: {c.state}")
        lines.append(f"- transfer_row: {c.transfer_row}")
        lines.append(f"- context_row: {c.context_row}")
        if c.read_dates:
            lines.append(f"- read_dates: {c.read_dates}")
        lines.append(f"- verified: {c.verified_status}")
        if c.payer_text:
            lines.append(f"- payer_text: {c.payer_text}")
        if c.payee_text:
            lines.append(f"- payee_text: {c.payee_text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def finding(cases: List[Case]) -> str:
    """The instrument's honest finding at any n."""
    if not cases:
        return "n=0: no cases filed."
    verified = sum(1 for c in cases if c.verified_status == VERIFIED)
    moved = sum(1 for c in cases if not c.transfer_row.lower().startswith("none"))
    return (f"n={len(cases)}: {moved} case(s) with a transfer row, "
            f"{verified} source-verified. "
            + ("A fund book can't say whether stranger money works, only whether anything moved in it."
               if verified < len(cases) else
               "All cases source-verified on payer and payee text."))
