#!/usr/bin/env python3
"""
Re-run every student's judge workflow listed in leaderboard.json.

Use case: you updated judge.py in hw3-2-judge-workflow and want every
student's last submission re-evaluated against the new judge, without
asking students to re-commit.

How it works:
  1. Read leaderboard.json from the repo root.
  2. For each entry, parse audit.run_url to get (owner/repo, run_id).
  3. Call `gh run rerun <run_id> --repo <owner/repo>`.
  4. The student's workflow re-runs, which checks out the latest judge
     from main, evaluates, and dispatches `submit_score` back here.

Skips entries whose student_id starts with "Baseline" (those are
hand-curated and have no real run_url).

Requires: `gh` CLI authenticated as an admin of the org.

Usage:
    python scripts/rerun_all.py                                 # rerun everyone (reads ./leaderboard.json)
    python scripts/rerun_all.py --dry-run                       # print what would happen
    python scripts/rerun_all.py --only b12508026                # rerun a single student
    python scripts/rerun_all.py --from backup/leaderboard.json  # read names from a backup file
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_LEADERBOARD = Path(__file__).resolve().parent.parent / "leaderboard.json"
RUN_URL_RE = re.compile(
    r"^https://github\.com/([^/]+/[^/]+)/actions/runs/(\d+)"
)
SKIP_PREFIX = "Baseline"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="print actions without calling gh")
    p.add_argument("--only", metavar="STUDENT_ID", help="only rerun this student")
    p.add_argument("--sleep", type=float, default=0.5, help="seconds to sleep between calls (default 0.5)")
    p.add_argument(
        "--from", dest="source", metavar="PATH", default=str(DEFAULT_LEADERBOARD),
        help="path to leaderboard JSON to read student list from "
             "(default: ./leaderboard.json; use a backup if the live file has been cleared)",
    )
    return p.parse_args()


def rerun(repo: str, run_id: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "(dry-run)"
    r = subprocess.run(
        ["gh", "run", "rerun", run_id, "--repo", repo],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        return True, r.stdout.strip() or "ok"
    return False, (r.stderr or r.stdout).strip()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        print(f"error: source file not found: {source}", file=sys.stderr)
        return 1
    print(f"reading student list from: {source}")
    data = json.loads(source.read_text())

    targets = []
    for entry in data:
        sid = entry.get("student_id", "")
        if sid.startswith(SKIP_PREFIX):
            continue
        if args.only and sid != args.only:
            continue
        url = (entry.get("audit") or {}).get("run_url", "")
        m = RUN_URL_RE.match(url)
        if not m:
            print(f"[skip] {sid}: cannot parse run_url ({url!r})")
            continue
        targets.append((sid, m.group(1), m.group(2)))

    if not targets:
        print("nothing to rerun")
        return 1 if args.only else 0

    print(f"about to rerun {len(targets)} student(s)" + (" [DRY RUN]" if args.dry_run else ""))
    if not args.dry_run and not args.only:
        ans = input("proceed? [y/N] ").strip().lower()
        if ans != "y":
            print("aborted")
            return 1

    ok = fail = 0
    failures = []
    for sid, repo, run_id in targets:
        success, msg = rerun(repo, run_id, args.dry_run)
        marker = "OK  " if success else "FAIL"
        print(f"  [{marker}] {sid:12s} {repo}#{run_id}  {msg}")
        if success:
            ok += 1
        else:
            fail += 1
            failures.append((sid, repo, run_id, msg))
        time.sleep(args.sleep)

    print(f"\ndone: {ok} ok, {fail} failed")
    if failures:
        print("\nfailed entries:")
        for sid, repo, run_id, msg in failures:
            print(f"  {sid}  {repo}#{run_id}  -- {msg}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
