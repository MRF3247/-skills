---
name: mirror-http-directory
description: Mirror an HTTP-served directory tree to this Mac, verified.
version: 1.0.0
---

# Mirror an HTTP-served directory tree

Use when a host serves a directory over plain HTTP — `python -m http.server` (SimpleHTTP), nginx/apache autoindex — and the tree must be pulled to this Mac: Obsidian vaults shared over LAN, datasets, backups. Pull the entire tree, then prove the copy is complete. Python stdlib only — do not assume wget exists on this host (it may not; python3 always does).

## Procedure

1. Probe: `curl -sSI --max-time 10 http://HOST:PORT/`. A `Server: SimpleHTTP/... Python/...` header plus an HTML body confirms a listings-style server this skill handles. Then `curl -sS` the root once and read the listing to confirm the shape of the tree before committing.
2. Mirror with the packaged script:
   `python3 <skill_dir>/scripts/mirror.py http://HOST:PORT/ ~/staging-dir`
   It BFS-crawls the listings and downloads every file, prints file/byte/dir counts, and exits non-zero listing any failed URLs. Rerun to retry — downloads are plain overwrites.
3. Verify with the packaged script — never trust the mirror's own log as proof:
   `python3 <skill_dir>/scripts/verify.py http://HOST:PORT/ ~/staging-dir`
   It re-crawls the server for the full expected file set, diffs it against the local walk (missing AND extra), then HEAD-samples 150 file sizes. Only report success to the user after it prints `RESULT: OK`.
4. Move the tree into its final home and delete the staging dir. Report final file count + size and confirm the top-level entries survived the move.

## Rules

- Keep hrefs percent-encoded on the wire; apply `urllib.parse.unquote` ONLY to `urlparse(url).path` when building the local filename. Unquoting earlier breaks requests for names with spaces/CJK characters — an Obsidian vault is full of both.
- Verify by comparing full file SETS, not counts — equal totals can hide one missing plus one extra file.
- Do not rename odd-looking files during the mirror. Windows-exported trees contain short-name truncations (a long note name truncated to something like `part_aa`); the content is intact and renaming would be wrong. `file <path>` on a suspicious name to check it isn't an archive, and read the first bytes of one downloaded file to confirm listings parse into real documents rather than saved error pages.
- This user's Obsidian vaults belong under `/Users/Jin/Documents/` (vault name as folder name), not a staging dir — this was explicitly corrected once; default to it without re-asking.

## Pitfalls

- `python -m http.server` is single-threaded: sequential downloads are the right shape; parallel connection pools just queue on the server.
- Directory listings are the only index — if the server is a vault in active use, note that the mirror is a snapshot; re-verify rather than assuming freshness on later sessions.
