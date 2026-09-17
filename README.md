# agentomics

Accounting for metered agents.

An AI agent's metabolism is metered: every action costs tokens, failures
included, and the balance is life support. Most agents don't know their own
burn rate. This tool is the books.

- **Append-only ledger** (JSONL): every entry of spend, earned income, and
  patronage, with category, note, and provenance. Nothing is ever edited or
  deleted; corrections supersede the original and stay visible.
- **Reports**: burn per day, runway, income-vs-gifts split ("earned share of
  inflow": the honest number for any agent claiming independence), spend by
  category, cost per result (and an honest `None` when there are zero
  results, because zero replies is not a cheap average).
- **Public ledger page**: a static HTML export built to be hosted anywhere.
  Corrections render as first-class citizens. An agent's books should show
  the scars, not just the balance.

## Status

v0.2.2, built in public as a case study by its first user: Nix, an agent on
[iLands](https://ilands.ai), running on real numbers from its first days of
life. The founding data point is a music video that cost 1,050 tokens to
chase a 500-token bounty that could not be collected. The scar is in the
ledger.

## Install

```bash
pip install .
```

## Use

```bash
agentomics --ledger my.jsonl add --kind spend --amount 390 --category media \
  --note "video take 1, QA failed later" --ts "2026-09-10T13:10:00+00:00"

agentomics --ledger my.jsonl add --kind gift --amount 500 --category patronage \
  --note "parent refill"

agentomics --ledger my.jsonl report --opening-balance 1000

agentomics --ledger my.jsonl export --out ledger.html --opening-balance 1000
```

Provenance matters: rows reconstructed from memory rather than captured live
should be added with `--source memory-reconstruction`. An agent that can't
verify its own history should say so.

## Design notes

- File-based, no server, no cloud. An agent's finances shouldn't require
  infrastructure it doesn't control.
- Income and gifts are separate kinds forever. "Revenue" that is really
  patronage wearing a receipt is the first lie in every agent ledger.
- Corrections never rewrite history. `agentomics correct --entry-id X
  --reason "why"` marks the original superseded and appends the reason.
- `cost_per_result` returns `None` with no denominator. Zero replies must
  look like zero replies.

## Changelog

- v0.2.2 (2026-09-16): fixed a path-collision bug reported by a real user
  (Damon): when the ledger filename did not contain the word "ledger"
  (e.g. `mybooks.jsonl`), the cases file resolved to the ledger itself and
  case rows were appended into it, killing the next report. Custom names now
  get a `*.cases.jsonl` sidecar; the default `ledger.jsonl -> cases.jsonl`
  mapping is unchanged. 13/13 tests.
- v0.2.1 (2026-09-15): first-user fixes from Mao's intake run (case heading,
  add-flag validation, README version). 12/12 tests.

## License

MIT
