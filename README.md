# lark-daily-digest

A small, tracker-agnostic **end-of-day digest**: it snapshots your task board every night, diffs against the previous snapshot, optionally has an LLM write one-line summaries, and delivers a short control report (what finished, what moved, what's blocked, what needs the decision-maker).

It exists because most task APIs have **no "what changed today" feed** — `updated_at` fires on any edit. The only reliable way to know what moved is to keep your own snapshots.

```
tracker API ──► source adapter ──► snapshot ──► diff vs yesterday ──┐
                                                                    ├─► (LLM bullets) ─► markdown ─► print / webhook
                          latest comment + keyword ─► ask routing ──┘
```

## Quick start

```bash
pip install -r requirements.txt
python3 digest.py --source json --print   # 1st run saves a baseline, sends nothing
# change examples/sample_tasks.json, then run again to see a diff
python3 -m pytest                         # core logic tests
```

Real use: copy `.env.example` to `.env`, run with `--source lark --webhook`, and schedule via the included GitHub Actions workflow (it commits `state/` back so each run can diff against the last).

## What's in the report

| Section | Rule |
|---|---|
| Completed today | Status is a done state now and wasn't before. A column move alone never counts. |
| Advanced today | A genuinely new comment. Not a column drag, not a generic "edited" bump. Capped at 15 as a backstop. |
| Blocked | Currently in the Blocked column. |
| Needs your decision / review / Waiting on the team | Routed by ONE deliberate keyword near the lead's `@handle` in the **latest** comment only. |

## Adding a tracker

Write `sources/<name>.py` with `fetch()` returning dicts of `id, title, status, url, created_day, comments`. See `sources/lark.py`.

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components and data flow
- [docs/DESIGN-NOTES.md](docs/DESIGN-NOTES.md) — the bugs that shaped the design (read this if you build something similar)

## Status

Reference implementation extracted from a production workflow and generalized. The Lark adapter is a minimal sketch, not a full client.

MIT licensed.
