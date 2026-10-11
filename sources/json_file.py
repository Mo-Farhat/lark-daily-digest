import json


def fetch(path="examples/sample_tasks.json"):
    with open(path) as f:
        return json.load(f)
