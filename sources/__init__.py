"""A source returns a list of task dicts:

    {"id": str, "title": str, "status": str, "url": str,
     "created_day": "YYYY-MM-DD", "comments": [str, ...]}

Write one adapter per tracker. Two are included: a JSON file (for demos and
tests) and a Lark Tasks adapter (the original target of this design).
"""
