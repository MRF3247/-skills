#!/usr/bin/env python3
"""链接 -> 得到大脑知识库：提交 -> 轮询 note_id -> 抽查 AI 总结 -> 入库。

用法：
  python3 link_to_kb.py --kb 07oPGma0 --tag 医时选题库 URL [URL ...]
  python3 link_to_kb.py --kb 07oPGma0 --json pairs.json        # [{"title":..,"url":..}, ...]
  python3 link_to_kb.py --kb 07oPGma0 URL --dry-run            # 只看抓取结果，不入库

要点：
- 链接笔记一律走 OpenAPI 提交 + 轮询；`getnote save <url>` 会同步等待并超时（任务其实已受理）。
- 每条打印 content 字符数：<300 视为没抓到正文，用 --dry-run 先看再决定。
- 多页站点（在线书/文档站）：AI 总结只覆盖落地页，需另补一条章节目录索引笔记（见 SKILL.md）。
"""
import argparse, json, os, random, subprocess, sys, time, urllib.error, urllib.request

BASE = "https://openapi.biji.com"


def _load_env():
    p = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api(method, path, body=None, timeout=45):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": os.environ["GETNOTE_API_KEY"],
            "X-Client-ID": os.environ["GETNOTE_CLIENT_ID"],
            "Content-Type": "application/json",
        },
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:  # qps_bucket_exceeded
                wait = 2.0 * (2 ** attempt) + random.uniform(0, 1.5)
                print(f"  429, wait {wait:.0f}s", flush=True)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("rate limited")


def submit(url, title, tag):
    body = {"note_type": "link", "link_url": url, "tags": [tag] if tag else []}
    if title:
        body["title"] = title
    d = api("POST", "/open/api/v1/resource/note/save", body)
    tasks = (d.get("data") or {}).get("tasks") or []
    if not tasks:
        raise RuntimeError(json.dumps(d, ensure_ascii=False)[:180])
    return tasks[0]["task_id"]


def poll(tid):
    dd = api("POST", "/open/api/v1/resource/note/task/progress", {"task_id": tid}).get("data") or {}
    return dd.get("status"), dd.get("note_id")


def detail(note_id):
    d = api("GET", f"/open/api/v1/resource/note/detail?id={note_id}")
    return (d.get("data") or {}).get("note") or {}


def kb_add(kb, ids):
    r = subprocess.run(
        ["getnote", "kb", "add", kb] + [str(i) for i in ids] + ["-o", "json"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    try:
        return json.loads(r.stdout).get("data", {})
    except Exception:
        return {"raw": (r.stdout or r.stderr)[:300]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", required=True, help="topic_id，如 07oPGma0")
    ap.add_argument("--tag", default="", help="同时打的标签，通常等于库名")
    ap.add_argument("--json", help="[{title,url}, ...] 清单文件")
    ap.add_argument("--dry-run", action="store_true", help="只提交+看内容，不入库")
    ap.add_argument("--min-len", type=int, default=300, help="正文长度下限，低于则告警")
    ap.add_argument("urls", nargs="*")
    a = ap.parse_args()

    _load_env()
    items = []
    if a.json:
        items = [(e.get("title") or "", e["url"]) for e in json.load(open(a.json))]
    items += [("", u) for u in a.urls]
    if not items:
        sys.exit("给 URL 或 --json 清单")

    tasks = {}
    for title, url in items:
        try:
            tid = submit(url, title, a.tag)
            tasks[url] = {"task_id": tid, "note_id": None, "title": title, "len": 0}
            print(f"提交 {url[:70]} -> task {tid}", flush=True)
        except Exception as e:
            tasks[url] = {"task_id": None, "note_id": None, "title": title, "error": str(e)[:150]}
            print(f"提交失败 {url[:70]} | {e}", flush=True)
        time.sleep(2.5)  # 串行，防 429

    deadline = time.time() + 600
    while any(not v.get("note_id") and v.get("task_id") for v in tasks.values()) and time.time() < deadline:
        for url, v in tasks.items():
            if v.get("note_id") or not v.get("task_id"):
                continue
            try:
                status, nid = poll(v["task_id"])
                if nid:
                    v["note_id"] = nid
                    print(f"  {url[:50]} -> note_id {nid}", flush=True)
                elif status == "failed":
                    v["error"] = "task failed"
                    print(f"  {url[:50]} 任务失败", flush=True)
            except Exception as e:
                print("  poll err", e, flush=True)
            time.sleep(1.5)
        time.sleep(8)

    ready = []
    for url, v in tasks.items():
        if not v.get("note_id"):
            continue
        for _ in range(12):
            n = detail(v["note_id"])
            content = n.get("content") or ""
            v["len"] = len(content)
            if v["len"] >= a.min_len:
                ready.append(v["note_id"])
                break
            time.sleep(15)
        print(f"  {v['title'][:40] or url[:40]} 正文 {v['len']} 字符"
              + ("" if v["len"] >= a.min_len else "  <-- 疑似没抓到正文，核对后再入库"), flush=True)

    if a.dry_run:
        print("dry-run，未入库。tasks:", json.dumps(tasks, ensure_ascii=False, indent=1))
        return
    if ready:
        for i in range(0, len(ready), 20):
            res = kb_add(a.kb, ready[i:i + 20])
            print(f"入库 {i + len(ready[i:i + 20])}/{len(ready)}:", json.dumps(res, ensure_ascii=False), flush=True)
    print("汇总:", json.dumps(tasks, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
