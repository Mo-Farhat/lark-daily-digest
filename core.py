"""Pure logic: stable signatures, ask classification, snapshot diffing.

No network, no clock, no globals -- everything here is unit-testable.
"""
import hashlib
import re

DONE_STATES = {"done", "closed", "complete", "completed"}

PENDING_WORDS = ("pending",)
DECISION_WORDS = ("decision", "decide", "direction", "approve", "approval",
                  "sign off", "sign-off", "input", "clarif", "confirm")
REVIEW_WORDS = ("review", "test")

REPLY_MARKERS = ("feedback from", "direction from", "confirmed by",
                 "approved by", "per ")


def comment_signature(texts):
    """Stable fingerprint of a comment thread.

    Never use Python's built-in hash() here: it is salted per process, so the
    same comment gets a different value on every run and every commented task
    looks 'active today'. SHA-1 of the text is stable across runs.
    """
    joined = "\n".join(texts)
    return f"{len(texts)}:{hashlib.sha1(joined.encode()).hexdigest()[:12]}" if texts else "0:"


def classify_ask(text, handle="@lead"):
    """Route a flagged task by ONE deliberate keyword near the handle.

    Order matters: 'pending' is checked first because ordinary decision-like
    words can appear inside a sentence that is really saying 'not yet'.
    Returns 'pending' | 'decision' | 'review' | None (handle not present).
    """
    low = text.lower()
    pos = low.find(handle.lower())
    if pos < 0:
        return None
    window = low[pos:pos + 200]
    if any(w in window for w in PENDING_WORDS):
        return "pending"
    if any(w in window for w in DECISION_WORDS):
        return "decision"
    return "review"  # includes REVIEW_WORDS and the unlabelled default


def records_reply(comments_after_flag):
    """Has someone recorded the lead's answer since the flag was raised?"""
    return any(m in c.lower() for c in comments_after_flag for m in REPLY_MARKERS)


def diff(prev, curr, today):
    """Compare yesterday's snapshot to today's.

    prev/curr: {task_id: {title, status, comment_sig, comments:[...]}}
    Returns dict of lists of task ids.
    Rules (each one learned the hard way, see docs/DESIGN-NOTES.md):
      * completed  = status is a done state NOW and was not before. A column
                     move alone is never completion.
      * advanced   = comment signature changed. Column moves and generic
                     'updated_at' bumps do not count.
      * a task new to the snapshot has no baseline, so it is not 'advanced'
        unless it was created today.
    """
    out = {"completed": [], "advanced": [], "blocked": [], "new": []}
    for tid, t in curr.items():
        p = prev.get(tid)
        status = t["status"].strip().lower()
        if status in DONE_STATES and (p is None or p["status"].strip().lower() not in DONE_STATES):
            out["completed"].append(tid)
        if status == "blocked":
            out["blocked"].append(tid)
        if p is None:
            if t.get("created_day") == today:
                out["new"].append(tid)
            continue
        if t["comment_sig"] != p["comment_sig"] and p.get("comment_sig") is not None:
            out["advanced"].append(tid)
    return out


TASK_ID_RE = re.compile(r"\b([A-Z]{2,4}-?\d{3,4}[a-z]?)\b")


def task_id_of(title):
    m = TASK_ID_RE.search(title or "")
    return m.group(1) if m else None
