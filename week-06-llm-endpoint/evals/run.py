"""Run every labelled case through the endpoint and score it.

A number you can compare is worth more than a high number. Run it with:
    .venv/bin/python evals/run.py
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CASES = Path(__file__).resolve().parent / "cases.json"
ENDPOINT = os.environ.get("EVAL_ENDPOINT", "http://localhost:8200/classify")


def call(payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(ENDPOINT, body, {"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def judge(case: dict, got: dict) -> list[str]:
    """Return the reasons this case failed, empty if it passed."""
    expected = case["expected"]
    problems = []
    if got.get("genre") != expected["genre"]:
        problems.append(f"genre {got.get('genre')!r}, expected {expected['genre']!r}")
    if got.get("audience") != expected["audience"]:
        problems.append(f"audience {got.get('audience')!r}, expected {expected['audience']!r}")
    if "max_confidence" in expected:
        confidence = got.get("confidence")
        if confidence is None or confidence >= expected["max_confidence"]:
            problems.append(
                f"confidence {confidence}, expected below {expected['max_confidence']}"
            )
    return problems


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    failures = []
    by_difficulty: dict[str, list[bool]] = {}

    for case in cases:
        status, got = call(case["input"])
        problems = [f"HTTP {status}"] if status != 200 else judge(case, got)
        by_difficulty.setdefault(case["difficulty"], []).append(not problems)
        mark = "pass" if not problems else "FAIL"
        print(f"  {mark}  {case['id']:22} {got.get('genre', '-'):22} "
              f"conf={got.get('confidence', '-')}")
        if problems:
            failures.append((case["id"], problems))

    passed = sum(1 for case in cases if case["id"] not in {f[0] for f in failures})
    print(f"\nscore: {passed} of {len(cases)} on genre, audience and the unsure rule")
    for name, results in sorted(by_difficulty.items()):
        print(f"  {name}: {sum(results)} of {len(results)}")

    if failures:
        print("\nwhat failed:")
        for name, problems in failures:
            print(f"  {name}: {'; '.join(problems)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
