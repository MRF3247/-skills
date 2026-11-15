#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Kimi（Moonshot 直连）写中文自媒体正文，并直接报出平台口径的字数。

用法：
  python3 kimi_text.py prompt.md [--out body.md] [--model kimi-k3.1-pro]
  cat prompt.md | python3 kimi_text.py - --out body.md

要点（踩过的坑）：
  * kimi-k3 / kimi-k3.1-pro 默认开思考，reasoning_content 会吃光 max_tokens，
    content 回空串（finish_reason=length）——所以默认带 thinking disabled；
    万一仍然空，自动抬 max_tokens 重试一次。
  * 这两个模型只接受默认 temperature（传 0.85 会 400），故不传。
  * key 从 ~/.hermes/.env 的 KIMI_API_KEY 读，不打印。
  * 输出末尾若是一行以 # 开头的 tag 行，会分开报「正文 / tag / 合计」三笔字数
    （小红书上限：合计 ≤1000 含标点）。
"""
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://api.moonshot.cn/v1/chat/completions"


def read_key():
    for line in open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8"):
        if line.startswith("KIMI_API_KEY="):
            return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("NO_KIMI_KEY: ~/.hermes/.env 里没有 KIMI_API_KEY")


def chat(key, prompt, model, max_tokens, disable_thinking=True):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens}
    if disable_thinking:
        body["thinking"] = {"type": "disabled"}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=600).read())
    except urllib.error.HTTPError as e:
        raise SystemExit("HTTP %s: %s" % (e.code, e.read().decode()[:300]))
    choice = data["choices"][0]
    return (choice["message"].get("content") or "").strip(), choice.get("finish_reason")


def counts(text):
    lines = [l for l in text.split("\n") if l.strip()]
    if lines and lines[-1].lstrip().startswith("#"):
        tags, bodytext = lines[-1], "\n".join(lines[:-1])
    else:
        tags, bodytext = "", text
    flat = lambda s: len(s.replace("\n", ""))
    return flat(bodytext), len(tags), flat(text)


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    src = args[0]
    out_path = args[args.index("--out") + 1] if "--out" in args else None
    model = args[args.index("--model") + 1] if "--model" in args else "kimi-k3.1-pro"
    prompt = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()

    key = read_key()
    text, finish = chat(key, prompt, model, 2500)
    if not text:  # 思考模型把额度吃光了
        text, finish = chat(key, prompt, model, 8000, disable_thinking=False)
    if not text:
        raise SystemExit("EMPTY_CONTENT: finish_reason=%s，检查 prompt 是否过长或模型额度" % finish)

    if out_path:
        open(out_path, "w", encoding="utf-8").write(text + "\n")
    print(text)
    body, tags, total = counts(text)
    print("\n--- 字数：正文 %d / tag %d / 合计 %d（小红书上限 1000 含标点）---" % (body, tags, total))


if __name__ == "__main__":
    main()
