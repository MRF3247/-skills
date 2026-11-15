#!/usr/bin/env python3
"""只补抓上一轮漏掉的期刊源（EuropePMC 并发超时后恢复用）。

用法：
  python3 scripts/retry_missing_journals.py --input /tmp/cand.json --days 3 --out /tmp/retry.json

为什么需要它：fetch_all_sources.py 用 6 线程并发打 EuropePMC，偶发一轮里十来个源同时
urlopen timeout；重跑整批通常又超时，而单源串行重试几乎必成功。上一轮结果 JSON 里
已经有的 source 名跳过，只补缺的刊，省掉 54 本刊的重复请求。

只管 JOURNALS（EuropePMC）。RSS 源超时直接重跑那次 fetch 即可，量小。
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_all_sources as F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="上一轮 fetch_all_sources 输出的 JSON")
    ap.add_argument("--days", type=int, default=3, help="回看天数，要和上一轮用的一致")
    ap.add_argument("--out", default="/tmp/retry_missing.json")
    a = ap.parse_args()

    try:
        prev = json.load(open(a.input))
    except Exception as e:
        sys.exit(f"读不到 {a.input}: {e}")

    present = {r.get("source") for r in prev}
    missing = [(n, i) for n, i in F.JOURNALS.items() if n not in present]
    print(f"上一轮 {len(present)} 个源有货，{len(missing)} 本刊缺失 → 串行重抓")

    cutoff = (datetime.now() - timedelta(days=a.days)).strftime("%Y-%m-%d")
    out, still_empty = [], []
    for name, issn in missing:
        rows = F.fetch_epmc(name, issn, cutoff)   # 内部已吞异常，失败只会返回 []
        print(f"  {name:34} {len(rows)}")
        if not rows:
            still_empty.append(name)
        out += rows
        time.sleep(1)

    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"补回 {len(out)} 条 → {a.out}")
    if still_empty:
        print("仍 0 条（发文节奏慢，正常；放大 --days 再试）: " + ", ".join(still_empty))


if __name__ == "__main__":
    main()
