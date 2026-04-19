#!/usr/bin/env python3
"""
Clear leaderboard.json, keeping only Baseline entries.

Writes a timestamped backup to backup/ before overwriting.

Usage:
    python scripts/clear_leaderboard.py            # backup + clear
    python scripts/clear_leaderboard.py --dry-run  # show what would be kept/removed
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEADERBOARD = ROOT / "leaderboard.json"
BACKUP_DIR = ROOT / "backup"
KEEP_PREFIX = "Baseline"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    data = json.loads(LEADERBOARD.read_text())
    kept = [e for e in data if e.get("student_id", "").startswith(KEEP_PREFIX)]
    removed = [e for e in data if not e.get("student_id", "").startswith(KEEP_PREFIX)]

    print(f"keeping {len(kept)} baseline(s):")
    for e in kept:
        print(f"  + {e['student_id']}")
    print(f"removing {len(removed)} student(s):")
    for e in removed:
        print(f"  - {e['student_id']}")

    if args.dry_run:
        print("\n[dry-run] no changes made")
        return 0

    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"leaderboard.{stamp}.json"
    shutil.copy2(LEADERBOARD, backup_path)
    print(f"\nbacked up original to: {backup_path}")

    LEADERBOARD.write_text(json.dumps(kept, indent=2) + "\n")
    print(f"wrote cleared leaderboard ({len(kept)} entries) to: {LEADERBOARD}")
    print(f"\nnext: git add leaderboard.json && git commit && git push")
    print(f"then: python scripts/rerun_all.py --from {backup_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
