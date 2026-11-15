"""
列出当前账号「有下载权限」的课程 → 生成 course_index.json
=========================================================
判据：对每门课第一节视频调 play_auth，成功=有权限（这是下载链路第一步，
      没买课会返回「该视频您无权限观看！」）。

用法：
  .venv/bin/python list_courses.py          # 全平台扫一遍，生成 course_index.json
  .venv/bin/python list_courses.py --print  # 顺便打印清单
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api.helixlife.cn/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.join(HERE, "course_index.json")


def token():
    p = os.path.join(HERE, "token.txt")
    if os.path.exists(p):
        t = open(p, encoding="utf-8").read().strip()
        if t:
            return t
    sys.exit("缺 token.txt —— 先跑 jlx_login.py")


def g(url, tok):
    H = {
        "authorization": f"Bearer {tok}",
        "platform": "pc",
        "source": "PC",
        "referer": "https://www.helixlife.cn/",
        "user-agent": "Mozilla/5.0",
    }
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25).read())


def all_courses(tok):
    out, page = [], 1
    while True:
        for attempt in range(3):
            try:
                d = g(f"{API}/edu/courses?type=mine&page={page}&page_size=100", tok)["data"]
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)
        out += d["data"]
        if page >= d["meta"]["last_page"]:
            break
        page += 1
    return out


def check(c, tok):
    try:
        d = g(f"{API}/edu/courses/{c['uuid']}/lessons", tok).get("data") or []
        v = [x for x in d if x.get("type") == "video"]
        if not v:
            return None
        # 权限是「按节」授予的，不能只试一节：
        #   ① 第一节常是免费试看（is_free=True），拿它验会把「没买」误判成「有权限」；
        #   ② 最后一节可能是后加的新课/单独售卖，拿它验会把「已买」误判成「无权限」。
        # 正确做法：取前 3 个非免费节，任一节能换到 PlayAuth 即算有权限。
        paid = [x for x in v if not x.get("is_free")] or v
        probes = paid[:3]
        hit = 0
        for x in probes:
            data = json.dumps({"video_id": x["path"]["path"]}, separators=(",", ":"))
            f = base64.b64encode(urllib.parse.quote(data).encode()).decode()
            if g(f"{API}/public/upload/play_auth?f={f}", tok).get("success"):
                hit += 1
        if not hit:
            return None
        return {"title": c["title"], "uuid": c["uuid"], "videos": len(v)}
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="打印清单")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    tok = token()
    cs = all_courses(tok)
    print(f"平台课程 {len(cs)} 门，逐门验权限…")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        res = list(ex.map(lambda c: check(c, tok), cs))
    allowed = [r for r in res if r]
    allowed.sort(key=lambda x: -x["videos"])
    for i, r in enumerate(allowed, 1):
        r["no"] = i
    allowed = [{"no": r["no"], "title": r["title"], "uuid": r["uuid"], "videos": r["videos"]} for r in allowed]
    json.dump(allowed, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tot = sum(r["videos"] for r in allowed)
    print(f"有权限 {len(allowed)} 门 / {tot} 节（{time.time()-t0:.0f}s）→ {IDX}")
    if args.print:
        for r in allowed:
            print(f"{r['no']:03d}. [{r['videos']:3d}节] {r['title']}  |  {r['uuid']}")


if __name__ == "__main__":
    main()
