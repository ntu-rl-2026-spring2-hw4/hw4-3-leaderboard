#!/usr/bin/env python3
"""
update_score.py — update leaderboard.json with a student's HW4 Q3 result.

HW4 Q3 is a single-task leaderboard (DMC humanoid-walk). Each submission is
evaluated over 100 episodes; the ranked score is `mean(returns) - std(returns)`.

Usage (from GitHub Actions or locally):

  python scripts/update_score.py \
      --student-id r12345678 \
      --results '{"score": 453.2, "mean_return": 480.0, "std_return": 26.8, "num_episodes": 100}'

  # Or via individual flags:
  python scripts/update_score.py \
      --student-id r12345678 \
      --score 453.2 --mean-return 480.0 --std-return 26.8 --num-episodes 100

  # Delete an entry:
  python scripts/update_score.py --delete --student-id r12345678
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "leaderboard.json"

TASK = "humanoid-walk"
EXPECTED_EPISODES = 100
BASELINE_SCORE = 450.0
REQUIRED_FIELDS = ("score", "mean_return", "std_return", "num_episodes")


def load() -> list:
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text())


def save(data: list):
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def validate_results(results: dict):
    for field in REQUIRED_FIELDS:
        if field not in results:
            sys.exit(f"ERROR: Missing field '{field}' in results")
    for field in ("score", "mean_return", "std_return"):
        try:
            float(results[field])
        except (TypeError, ValueError):
            sys.exit(f"ERROR: Field '{field}' must be a number, got {results[field]!r}")
    try:
        n = int(results["num_episodes"])
    except (TypeError, ValueError):
        sys.exit(f"ERROR: Field 'num_episodes' must be int, got {results['num_episodes']!r}")
    if n != EXPECTED_EPISODES:
        # Not fatal; the judge pins this, but print a warning so anomalies show up.
        print(f"WARNING: num_episodes={n}, expected {EXPECTED_EPISODES}", file=sys.stderr)


def normalize(results: dict) -> dict:
    return {
        "score":         round(float(results["score"]),       4),
        "mean_return":   round(float(results["mean_return"]), 4),
        "std_return":    round(float(results["std_return"]),  4),
        "num_episodes":  int(results["num_episodes"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--student-id", required=True)
    parser.add_argument("--results", default=None,
                        help='JSON string: {"score":..., "mean_return":..., "std_return":..., "num_episodes":100}')
    parser.add_argument("--delete", action="store_true",
                        help="Remove the student's entry")
    parser.add_argument("--audit", default=None,
                        help="JSON string: {run_url, triggered_by, event_type, ...}")
    # Alternative per-field flags (used when --results not supplied)
    parser.add_argument("--score",        type=float, default=None)
    parser.add_argument("--mean-return",  type=float, default=None, dest="mean_return")
    parser.add_argument("--std-return",   type=float, default=None, dest="std_return")
    parser.add_argument("--num-episodes", type=int,   default=None, dest="num_episodes")

    args = parser.parse_args()
    data = load()

    # ── Delete mode ─────────────────────────────────────────────────
    if args.delete:
        before = len(data)
        data = [e for e in data if e["student_id"] != args.student_id]
        if len(data) == before:
            sys.exit(f"ERROR: Student '{args.student_id}' not found.")
        save(data)
        print(f"Deleted entry for {args.student_id}")
        return

    # ── Parse results ────────────────────────────────────────────────
    if args.results:
        try:
            results = json.loads(args.results)
        except json.JSONDecodeError as e:
            sys.exit(f"ERROR: Invalid JSON in --results: {e}")
    elif args.score is not None:
        if args.mean_return is None or args.std_return is None:
            sys.exit("ERROR: --score requires --mean-return and --std-return too.")
        results = {
            "score":        args.score,
            "mean_return":  args.mean_return,
            "std_return":   args.std_return,
            "num_episodes": args.num_episodes if args.num_episodes is not None else EXPECTED_EPISODES,
        }
    else:
        sys.exit("ERROR: Provide either --results JSON or --score/--mean-return/--std-return flags.")

    validate_results(results)
    results = normalize(results)

    audit = None
    if args.audit:
        try:
            audit = json.loads(args.audit)
        except json.JSONDecodeError as e:
            print(f"WARNING: Could not parse --audit JSON, skipping: {e}", file=sys.stderr)

    now = datetime.now(timezone.utc).isoformat()
    existing = next((e for e in data if e["student_id"] == args.student_id), None)

    if existing:
        old_score = float(existing.get("score", float("-inf")))
        new_score = results["score"]
        if new_score <= old_score:
            print(f"Skipped: new score ({new_score}) is not better than existing ({old_score})")
            return
        existing.update(results)
        existing["submission_time"] = now
        if audit is not None:
            existing["audit"] = audit
        print(f"Updated entry for {args.student_id}: {old_score} -> {new_score}")
    else:
        entry = {
            "student_id":      args.student_id,
            "submission_time": now,
            **results,
        }
        if audit is not None:
            entry["audit"] = audit
        data.append(entry)
        print(f"Added new entry for {args.student_id}: score={results['score']}")

    save(data)


if __name__ == "__main__":
    main()
