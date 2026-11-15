---
name: getnote-dedup
description: Use when getnote notes have duplicates. Title+URL dedup.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
required_commands:
  - getnote
metadata:
  hermes:
    tags: [getnote, dedup, notes, biji]
---

# getnote 去重（得到大脑重复笔记清理）

User's dedup rule: a duplicate = a link note with the same title AND the same original URL as another. Keep the **earliest created** per group, delete the rest. Deletion moves notes to the trash (recoverable ~30 days), so it is safe to execute after showing the plan.

## Quick run

Use the bundled `scripts/dedup.py` (its absolute path is in the skill dir, e.g. `~/.hermes/skills/note-taking/getnote-dedup/scripts/dedup.py`):

```shell
python3 scripts/dedup.py ~/getnote-dedup plan     # pull all, group, resolve urls, write dedup_plan.json. No deletions.
python3 scripts/dedup.py ~/getnote-dedup execute  # delete planned ids, verify each via re-probe. BACKGROUND ONLY.
python3 scripts/dedup.py ~/getnote-dedup verify   # re-pull all, assert plan fully applied
```

Run `plan` first, show the user the group/count summary, then run `execute` with terminal(background=true, notify=true), then `verify` and report exact counts.

## API facts (learned the hard way)

- `getnote notes --all --limit 100 -o json` pulls everything (~2 min for ~950 notes, ~10 MB json).
- The LIST json has NO original url. Per note: `getnote note <id> --field url`. If empty, fetch full note json and use `attachments[]` where `type == "link"` (bilibili-style saves store the url there, top-level url is null).
- `getnote note delete <id> --yes` moves to trash. Do NOT trust its stdout/exit code — verify by re-probing `getnote note <id> --field title`: empty output (exit 0) or stderr `note_not_found`/`笔记不存在` = gone.
- `note_not_found` during execute = already deleted by an earlier interrupted run → treat as success. The script is resumable (it re-probes and skips gone ids).

## Pitfalls

- NEVER delete on title match alone. Generic scrape titles collide across different sources (`YT` was 3 different YouTube videos; X posts share a display title). Compare normalized URLs (lowercase scheme/host, strip trailing `/`, keep query).
- Exclude empty titles from grouping — they cluster into one fake "duplicate" group.
- Only delete notes whose URL resolved; unknown/empty-URL notes stay untouched.
- ~80 deletions take 10-15 min sequential. Foreground terminal times out (~420 s) and kills the run mid-way — always background. If interrupted anyway: probe survivors, re-run execute.
- 4 parallel workers are fine for url fetches / probes; keep deletes sequential with ~1 s pauses (rate limits).
- Final verify must match exactly: (before_count − after_count) == planned deletions, 0 planned ids present, every keep_id present. Don't finalize on approximate counts.
- Duplicate storms (one note saved 5-7× within minutes, e.g. 2026-08-19/26 in user's account) come from client retry/sync bugs; they can recur after bulk re-saves — rerunning this skill is the fix.
- Audit trail in the workdir: `all_notes.json` (pre-state), `dedup_plan.json`, `delete_log.json`.
