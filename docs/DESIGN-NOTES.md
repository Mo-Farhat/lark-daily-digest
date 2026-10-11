# Design notes: bugs that shaped this

Each rule in `core.py` exists because the naive version broke in production.

1. **Never use Python's `hash()` for change detection.** It is randomised per process (`PYTHONHASHSEED`), so unchanged comments got a new signature every run and nearly the whole board showed as "active today". Use SHA-1 (`comment_signature`).
2. **A signature format change causes a one-night false positive.** Old and new placeholders for "no comments" differ as strings, so every zero-comment task looks changed once. It self-corrects; don't chase it as a bug.
3. **A column move is not a completion.** Completed = closed only. A looser "I did my part" definition collides with a stricter written rule; settle the definition with the decision-maker, not in code.
4. **"Advanced" = new comment only.** Generic `updated_at` changes fire from unrelated edits, and a task whose previous fetch failed will look freshly edited when it recovers.
5. **Route asks with a single deliberate keyword, not inference.** Guessing "pending" from words like "once"/"before" both missed real cases and misfired on ordinary sentences. A controlled vocabulary is auditable.
6. **Only the latest comment governs a flag.** Comments are a permanent record; scanning history would mean a flag could never clear. Check `pending` before `decision` words, since decision-sounding phrases appear inside "not yet" sentences.
7. **Batch LLM calls.** One call across ~60 tasks hit the API timeout and the entire digest fell back to bare titles. Batches of 12 mean one slow batch loses only its own tasks.
8. **LLMs conflate similar neighbours.** Two thematically similar tasks in one batch swapped summaries. Key results by task ID (not position) and consider separating similar tasks across batches.
9. **Cap the noisiest section.** A hard limit on "Advanced today" means a future detection bug can never again dump the whole board on the reader.
10. **Multi-board tasks:** never let a blank section overwrite a real one when the same task appears on several boards.
11. **A nightly diff is not a continuous observer.** A task that moves through several states and back in a day shows only its net result. Document this limit up front.
12. **"Today" must be your calendar day.** Query and bucket in the configured timezone, not the CI runner's UTC.
