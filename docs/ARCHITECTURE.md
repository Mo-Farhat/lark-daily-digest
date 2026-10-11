# Architecture

| File | Role |
|---|---|
| `core.py` | Pure functions: stable comment signature, ask classification, snapshot diff. No I/O, fully tested. |
| `sources/` | One adapter per tracker, all returning the same task dict shape. |
| `digest.py` | Orchestration: fetch → snapshot → diff → summarise → render → deliver. |
| `state/` | `latest.json` plus dated copies in `archive/`, so the board's position on any past day can be proven rather than reconstructed. |
| `.github/workflows/digest.yml` | Scheduler + persistence (commits `state/` back). |

## Run lifecycle

1. Fetch all tasks via the source adapter.
2. Load `state/latest.json`. If absent, save a baseline and stop (first run reports nothing, by design).
3. Diff, classify asks from each task's latest comment, collect the tasks worth mentioning.
4. Summarise in batches of 12 (optional LLM); any failed batch falls back to titles for its own tasks only.
5. Render markdown, save the new snapshot, deliver.

## Failure philosophy

Every optional layer (LLM, webhook, per-batch summaries) degrades to a plainer output instead of failing the run. The deterministic layer (what moved, who's asked) never depends on the LLM, so any line in the digest can be traced to an exact cause.
