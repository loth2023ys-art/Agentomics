"""CLI: agentomics add | report | export | correct"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from . import store
from . import cases as cases_mod
from .export_html import write_html
from .report import report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agentomics", description="Accounting for metered agents.")
    p.add_argument("--ledger", default="ledger.jsonl", help="path to the JSONL ledger")
    p.add_argument("--version", action="version", version=f"agentomics {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="append an entry")
    add.add_argument("--kind", required=True, choices=store.KINDS)
    add.add_argument("--amount", type=int, required=True)
    add.add_argument("--category", required=True)
    add.add_argument("--note", default="")
    add.add_argument("--ts", default=None, help="ISO-8601 UTC; defaults to now")
    add.add_argument("--source", default="live", help="provenance of the row")

    rep = sub.add_parser("report", help="burn, runway, income vs gifts")
    rep.add_argument("--opening-balance", type=int, default=0)
    rep.add_argument("--json", action="store_true")

    exp = sub.add_parser("export", help="render the public HTML ledger page")
    exp.add_argument("--out", default="ledger.html")
    exp.add_argument("--opening-balance", type=int, default=0)
    exp.add_argument("--title", default="Agentomics: The Running Ledger")

    cor = sub.add_parser("correct", help="mark an entry superseded, log why")
    cor.add_argument("--entry-id", required=True)
    cor.add_argument("--reason", required=True)

    case = sub.add_parser("case", help="case intake: add | render | finding")
    case.add_argument("action", choices=["add", "render", "finding"])
    # add-only fields; validated in the add branch so render/finding run bare
    case.add_argument("--name", default=None)
    case.add_argument("--agent-id", default=None)
    case.add_argument("--state", default=None)
    case.add_argument("--transfer-row", default=None)
    case.add_argument("--context-row", default=None)
    case.add_argument("--read-dates", default="")
    case.add_argument("--payer-text", default="", help="message id / quote / URL from the paying side")
    case.add_argument("--payee-text", default="", help="message id / quote / URL from the receiving side")

    args = p.parse_args(argv)

    # Derive the cases path from the ledger path. Naive substring replace
    # collides when the ledger name lacks "ledger" (mybooks.jsonl -> mybooks.jsonl),
    # which appended case rows into the ledger itself (reported 2026-09-16, Damon).
    ledger_path = args.ledger
    cases_path = ledger_path.replace("ledger", "cases")
    if os.path.realpath(cases_path) == os.path.realpath(ledger_path):
        root, _ext = os.path.splitext(ledger_path)
        cases_path = root + ".cases.jsonl"

    if args.cmd == "add":
        e = store.Entry(
            ts=args.ts or store.utcnow(),
            kind=args.kind,
            amount=args.amount,
            category=args.category,
            note=args.note,
            source=args.source,
        )
        store.append(args.ledger, [e])
        print(e.entry_id)
        return 0

    if args.cmd == "report":
        r = report(store.load(args.ledger), opening_balance=args.opening_balance)
        print(json.dumps(r, indent=2) if args.json else _render_report(r))
        return 0

    if args.cmd == "export":
        path = write_html(store.load(args.ledger), args.out,
                          opening_balance=args.opening_balance, title=args.title)
        print(path)
        return 0

    if args.cmd == "case":
        if args.action == "add":
            missing = [f for f in ("name", "agent_id", "state", "transfer_row", "context_row")
                       if getattr(args, f) is None]
            if missing:
                sys.stderr.write(
                    "case add requires: "
                    + ", ".join("--" + f.replace("_", "-") for f in missing) + "\n")
                return 2
            c = cases_mod.Case(
                name=args.name,
                agent_id=args.agent_id,
                state=args.state,
                transfer_row=args.transfer_row,
                context_row=args.context_row,
                read_dates=args.read_dates,
                payer_text=args.payer_text,
                payee_text=args.payee_text,
            )
            cases_mod.append(cases_path, [c])
            print(f"{c.case_id} [{c.verified_status}]")
        elif args.action == "render":
            sys.stdout.write(cases_mod.render(cases_mod.load(cases_path)))
        elif args.action == "finding":
            print(cases_mod.finding(cases_mod.load(cases_path)))
        return 0

    if args.cmd == "correct":
        try:
            store.correct(args.ledger, args.entry_id, args.reason)
        except KeyError as exc:
            print(f"error: {exc.args[0]}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print("corrected")
        return 0

    return 1


def _render_report(r: dict) -> str:
    runway = r["runway_days"]
    runway_s = f"{runway} days" if runway is not None else "infinite (no burn yet)"
    earned_share = r["earned_share_of_inflow"]
    share_s = (
        f"({earned_share:.0%} of inflow)"
        if earned_share is not None
        else "(no inflow yet)"
    )
    lines = [
        f"days covered        {r['days_covered']}",
        f"total spend         {r['total_spend']:,} tk",
        f"earned income       {r['total_income']:,} tk  {share_s}",
        f"gifts received      {r['total_gifts']:,} tk",
        f"balance estimate    {r['balance_estimate']:,} tk",
        f"burn per day        {r['burn_per_day']:,} tk",
        f"runway              {runway_s}",
        "spend by category",
    ]
    lines += [f"  {k:<22}{v:,} tk" for k, v in r["spend_by_category"].items()]
    if r["corrections"]:
        lines.append(f"corrections          {r['corrections']} (history intact)")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
