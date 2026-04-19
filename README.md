# NTU 2026 Spring DRL HW4 Q3 Leaderboard

Static leaderboard for the NTU Deep Reinforcement Learning course HW4 Q3
(DMC **humanoid-walk**), hosted on **GitHub Pages**.
Scores are stored in `leaderboard.json` and displayed at the GitHub Pages URL
of this repo.

## Task & scoring

- Environment: `humanoid-walk` (dm_control suite) via `make_dmc_env(..., flatten=True, use_pixels=False)`.
- Episodes per submission: **100**.
- Ranking score: **`mean(returns) − std(returns)`**.
- Baseline: **450** (score ≥ 450 ⇒ full partial-credit on the leaderboard portion).

## How submissions are received

The judge workflow triggers score updates by calling the GitHub
**repository_dispatch** API:

```
POST https://api.github.com/repos/{OWNER}/{REPO}/dispatches
Authorization: Bearer {LEADERBOARD_TOKEN}
Content-Type: application/json
```

Payload:

```json
{
  "event_type": "submit_score",
  "client_payload": {
    "student_id": "r12345678",
    "results": {
      "score":        453.2,
      "mean_return":  480.0,
      "std_return":    26.8,
      "num_episodes": 100
    },
    "audit": {
      "repository": "<org>/r12345678_repo",
      "run_id":     "12345678901",
      "run_url":    "https://github.com/<org>/r12345678_repo/actions/runs/12345678901",
      "sha":        "abc123def456...",
      "actor":      "r12345678"
    }
  }
}
```

This triggers the `update_leaderboard` workflow → `scripts/update_score.py`
→ commits updated `leaderboard.json` → GitHub Pages auto-deploys.

The `LEADERBOARD_TOKEN` must have **`repo` scope**.

## `leaderboard.json` entry shape

```json
{
  "student_id":      "r12345678",
  "submission_time": "2026-04-20T13:21:41.261920+00:00",
  "score":           453.2,
  "mean_return":     480.0,
  "std_return":      26.8,
  "num_episodes":    100,
  "audit":           { "run_url": "..." }
}
```

Only strictly-better scores overwrite an existing entry (`update_score.py`
compares `score` and skips no-op updates).

## Admin: re-judging all submissions

When `judge.py` in the judge repo is updated, you can re-evaluate every
existing submission **without asking students to re-commit**. Each student's
workflow checks out the judge from `main` at run time, so re-running their
last GitHub Actions run picks up the new judge automatically.

The flow:

1. Push the new `judge.py` to the judge repo `main`.
2. Pull this repo and back up + clear `leaderboard.json` (Baselines are kept):
   ```bash
   git pull
   python scripts/clear_leaderboard.py
   git add leaderboard.json
   git commit -m "leaderboard: clear for re-judge"
   git push
   ```
   `clear_leaderboard.py` writes a timestamped backup to `backup/` (gitignored)
   and prints the exact command to run next.
3. Wait until the `Update Leaderboard` workflow is idle in the Actions tab.
4. Trigger re-runs of every student's last judge run:
   ```bash
   python scripts/rerun_all.py --from backup/leaderboard.<timestamp>.json --dry-run
   python scripts/rerun_all.py --from backup/leaderboard.<timestamp>.json
   ```
   The script reads the student list and `audit.run_url` from the backup file
   and calls `gh run rerun` against each student's repo. Entries whose
   `student_id` starts with `Baseline` are skipped. Requires `gh` authenticated
   as an org admin.
5. Each re-run dispatches `submit_score` back here. The `Update Leaderboard`
   workflow has a top-level `concurrency: { group: leaderboard-writer,
   cancel-in-progress: false }` so multiple writers serialize on a single
   queue — no `git push` races, no dropped submissions.

To re-judge a single student instead of everyone:

```bash
python scripts/rerun_all.py --only b12508026
```
