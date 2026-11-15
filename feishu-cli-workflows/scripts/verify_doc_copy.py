#!/usr/bin/env python3
"""校验「文档完整复制」：对比源文档与目标文档的结构/文本/图片。

用法（cwd 任意）：
    python3 verify_doc_copy.py --src <源 doc token> --dst <目标 doc token>

判定：三个 ok 全 True 才算完整复制。任一 False 时看 details 定位丢失位置。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter


def cli(*args):
    env = dict(os.environ)
    env["PATH"] = env.get("PATH", "") + os.pathsep + os.path.expanduser("~/.local/bin")
    out = subprocess.run(["lark-cli", *args], capture_output=True, text=True, env=env).stdout
    return json.loads(out[out.find("{"):])


def fetch_xml(token):
    data = cli("docs", "+fetch", "--doc", token, "--doc-format", "xml",
               "--detail", "full", "--as", "user")
    if not data.get("ok"):
        sys.exit(f"fetch failed for {token}: {data}")
    return data["data"]["document"]["content"]


def tag_counts(xml):
    return Counter(re.findall(r"<([a-zA-Z_][\w-]*)", xml))


def plain_text(xml):
    xml = re.sub(r"<img[^>]*>", "", xml)
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", xml))


def img_tokens(xml):
    return set(re.findall(r'<img[^>]*src="([^"]+)"', xml))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    args = ap.parse_args()

    s, d = fetch_xml(args.src), fetch_xml(args.dst)
    cs, cd = tag_counts(s), tag_counts(d)
    keys = sorted(set(cs) | set(cd))
    diffs = {k: [cs.get(k, 0), cd.get(k, 0)] for k in keys if cs.get(k, 0) != cd.get(k, 0)}

    ts, td = plain_text(s), plain_text(d)
    text_ok = ts == td
    first_diff = None
    if not text_ok:
        for i, (a, b) in enumerate(zip(ts, td)):
            if a != b:
                first_diff = {"pos": i, "src": ts[max(0, i - 40):i + 80], "dst": td[max(0, i - 40):i + 80]}
                break

    isrc, idst = img_tokens(s), img_tokens(d)
    report = {
        "tags_ok": not diffs,
        "text_ok": text_ok,
        "text_len": [len(ts), len(td)],
        "images": {"src": len(isrc), "dst": len(idst), "shared_tokens": len(isrc & idst),
                   "independent_copy": not (isrc & idst)},
        "details": {"tag_diffs": diffs, "first_text_diff": first_diff},
    }
    report["all_ok"] = report["tags_ok"] and text_ok and report["images"]["independent_copy"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["all_ok"] else 1)


if __name__ == "__main__":
    main()
