import core


def test_signature_is_stable_and_distinguishes():
    a = core.comment_signature(["hello"])
    assert a == core.comment_signature(["hello"])
    assert a != core.comment_signature(["hello", "more"])
    assert core.comment_signature([]) == "0:"


def test_classify_order_pending_first():
    assert core.classify_ask("@lead pending: waiting, then confirm") == "pending"
    assert core.classify_ask("@lead decision: A or B?") == "decision"
    assert core.classify_ask("@lead please look") == "review"
    assert core.classify_ask("no tag here") is None


def test_diff_rules():
    prev = {"a": {"status": "In Progress", "comment_sig": "1:x", "title": "a"},
            "b": {"status": "For Review", "comment_sig": "1:y", "title": "b"}}
    curr = {"a": {"status": "Done", "comment_sig": "1:x", "title": "a"},
            "b": {"status": "Done", "comment_sig": "2:z", "title": "b"},
            "c": {"status": "To Do", "comment_sig": "0:", "title": "c", "created_day": "d"}}
    d = core.diff(prev, curr, "d")
    assert set(d["completed"]) == {"a", "b"}
    assert d["advanced"] == ["b"]          # a moved column, no comment -> not advanced
    assert d["new"] == ["c"]


def test_task_id_subtask():
    assert core.task_id_of("ENG-063c: Choose who sees") == "ENG-063c"
