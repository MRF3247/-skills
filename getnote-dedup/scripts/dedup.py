#!/usr/bin/env python3
"""End-to-end dedup for 得到大脑 (Get笔记) link notes via the getnote CLI.

Phases:
  plan    (default) Pull all notes, group by normalized title, resolve original
          URLs, write dedup_plan.json (same title + same URL = duplicate; keep
          earliest). No deletions.
  execute Delete planned duplicates, verifying each with a re-probe. Resumable:
          already-deleted ids are skipped. Run in BACKGROUND — ~10-15 min for
          ~80 notes; foreground calls time out and kill it mid-run.
  verify  Re-pull all notes and assert the plan was fully applied.

Usage:
  python3 dedup.py <workdir> [plan|execute|verify]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit


def sh(args, timeout=60):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def get_json(args, tries=3, timeout=60):
    last = ""
    for a in range(tries):
        r = sh(args, timeout)
        try:
            return json.loads(r.stdout)
        except Exception:
            last = (r.stderr or r.stdout)[:200]
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"getnote JSON failed: {' '.join(args)} :: {last}")


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "").casefold()
    t = re.sub(r"\s+", "", t)
    return re.sub(r"^[\W_]+|[\W_]+$", "", t)


def norm_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    p = urlsplit(u)
    return (f"{p.scheme.lower()}://{p.netloc.lower()}{p.path.rstrip('/')}"
            + (f"?{p.query}" if p.query else "") + (f"#{p.fragment}" if p.fragment else ""))


def resolve_url(nid: str) -> str:
    """Original URL: top-level url field, else link attachments (bilibili-style)."""
    r = sh(["getnote", "note", nid, "--field", "url"])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    note = get_json(["getnote", "note", nid, "-o", "json"])["data"]["note"]
    urls = sorted({a["url"] for a in (note.get("attachments") or [])
                   if a.get("type") == "link" and a.get("url")})
    return "|".join(urls)


def gone(nid: str) -> bool:
    """True if the note no longer exists (empty title reply, or note_not_found)."""
    r = sh(["getnote", "note", nid, "--field", "title"])
    if r.returncode == 0:
        return not r.stdout.strip()
    return "note_not_found" in (r.stderr or "") or "笔记不存在" in (r.stderr or "")


def pull_all(workdir: str):
    r = sh(["getnote", "notes", "--all", "--limit", "100", "-o", "json"], timeout=900)
    data = json.loads(r.stdout)
    notes = data["data"]["notes"]
    with open(os.path.join(workdir, "all_notes.json"), "w") as f:
        json.dump(data, f, ensure_ascii=False)
    return notes


def phase_plan(workdir: str):
    notes = pull_all(workdir)
    print(f"pulled {len(notes)} notes", flush=True)

    groups = defaultdict(list)
    for n in notes:
        k = norm_title(n.get("title", ""))
        if k:  # empty titles would cluster into one fake group
            groups[k].append(n)
    dup_groups = [v for v in groups.values() if len(v) > 1]
    ids = [n["id"] for g in dup_groups for n in g]
    print(f"{len(dup_groups)} same-title groups, {len(ids)} notes; resolving urls...", flush=True)

    with ThreadPoolExecutor(4) as ex:
        url_map = dict(zip(ids, ex.map(resolve_url, ids)))

    to_delete, keeps, diff_urls = [], [], []
    for g in dup_groups:
        entries = [{"id": n["id"], "created_at": n.get("created_at", ""),
                    "title": n.get("title", ""), "url": norm_url(url_map.get(n["id"], ""))}
                   for n in g]
        by_url = defaultdict(list)
        for e in entries:
            if e["url"]:
                by_url[e["url"]].append(e)
        found = False
        for url, es in by_url.items():
            if len(es) > 1:
                found = True
                es.sort(key=lambda x: x["created_at"])
                keeps.append({"keep_id": es[0]["id"], "title": es[0]["title"], "url": url})
                for e in es[1:]:
                    e["keep_id"] = es[0]["id"]
                    to_delete.append(e)
        if not found:
            diff_urls.append({"title": g[0].get("title", ""),
                              "urls": [url_map.get(n["id"]) for n in g]})

    with open(os.path.join(workdir, "dedup_plan.json"), "w") as f:
        json.dump({"delete": to_delete, "keep": keeps, "diff_url_groups": diff_urls},
                  f, ensure_ascii=False, indent=1)
    print(f"plan: delete {len(to_delete)} | keep {len(keeps)} dup groups | "
          f"{len(diff_urls)} same-title-different-url groups (NOT duplicates)", flush=True)


def phase_execute(workdir: str):
    with open(os.path.join(workdir, "dedup_plan.json")) as f:
        dels = json.load(f)["delete"]
    assert len({d["id"] for d in dels}) == len(dels), "duplicate ids in plan"
    assert all(d["url"] for d in dels), "refusing to delete a note with unknown url"

    pending = [d for d in dels if not gone(d["id"])]  # resume support
    print(f"{len(dels)} planned, {len(dels) - len(pending)} already gone, "
          f"deleting {len(pending)}", flush=True)

    log, failed = [], []
    for i, d in enumerate(pending, 1):
        ok = False
        for attempt in range(3):
            sh(["getnote", "note", "delete", d["id"], "--yes"])
            time.sleep(1)
            if gone(d["id"]):
                ok = True
                break
            time.sleep(2 * (attempt + 1))
        log.append({**d, "ok": ok})
        if not ok:
            failed.append(d["id"])
        print(f"[{i}/{len(pending)}] {'OK' if ok else 'FAIL'} {d['id']} {d['title'][:36]}", flush=True)

    with open(os.path.join(workdir, "delete_log.json"), "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    print(f"DONE: {len(pending) - len(failed)}/{len(pending)} deleted, {len(failed)} failed", flush=True)
    if failed:
        sys.exit(1)


def phase_verify(workdir: str):
    with open(os.path.join(workdir, "dedup_plan.json")) as f:
        plan = json.load(f)
    before = json.load(open(os.path.join(workdir, "all_notes.json")))["data"]["notes"]
    after = pull_all(workdir)
    after_ids = {n["id"] for n in after}
    still = [d["id"] for d in plan["delete"] if d["id"] in after_ids]
    missing_keeps = [k["keep_id"] for k in plan["keep"] if k["keep_id"] not in after_ids]
    print(f"before {len(before)}, after {len(after)}, diff {len(before) - len(after)}")
    print(f"planned deletes still present: {len(still)} (want 0)")
    print(f"kept notes missing: {len(missing_keeps)} (want 0)")
    if still or missing_keeps:
        sys.exit(1)
    print("VERIFY OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("phase", nargs="?", default="plan", choices=["plan", "execute", "verify"])
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True)
    {"plan": phase_plan, "execute": phase_execute, "verify": phase_verify}[a.phase](a.workdir)


if __name__ == "__main__":
    main()
