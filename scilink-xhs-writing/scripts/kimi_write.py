#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Kimi（Moonshot API）写稿：一条命令把 prompt 文件变成草稿文件。

为什么不用 kimi-code CLI：CLI 走 OAuth，授权失效时直接报
「The provided authorization grant is invalid」；API Key 稳定得多。

关键参数（踩过的坑）：
  * kimi-k3 / kimi-k3.1-pro 是思考模型，默认会把 token 全烧在 reasoning 上、
    content 返回空字符串 —— 必须传 thinking={"type":"disabled"}。
  * kimi-k3 只接受 temperature=1，传别的直接 400 —— 默认不传。
  * engine_overloaded_error 会随机出现 —— 内置 4 次指数退避重试。

用法：
    python3 kimi_write.py prompt.md --out draft.md
    cat prompt.md | python3 kimi_write.py -
    python3 kimi_write.py prompt.md --thinking --model kimi-k3 --max-tokens 4000
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

API = "https://api.moonshot.cn/v1/chat/completions"


def load_key():
    for env in ("KIMI_API_KEY", "MOONSHOT_API_KEY"):
        if os.environ.get(env):
            return os.environ[env]
    for path in (os.path.expanduser("~/.hermes/.env"), os.path.expanduser("~/.env")):
        try:
            for line in open(path, encoding="utf-8"):
                for env in ("KIMI_API_KEY", "MOONSHOT_API_KEY"):
                    if line.startswith(env + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            continue
    sys.exit("未找到 KIMI_API_KEY：请写入 ~/.hermes/.env 或导出环境变量")


def call(key, model, prompt, max_tokens, thinking):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens}
    if not thinking:
        body["thinking"] = {"type": "disabled"}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=420).read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        raise RuntimeError(f"HTTP {e.code}: {detail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt_file", help="prompt 文件路径，或 - 从 stdin 读")
    ap.add_argument("--out", default=None, help="草稿输出路径；默认 stdout")
    ap.add_argument("--model", default="kimi-k3.1-pro")
    ap.add_argument("--max-tokens", type=int, default=2500)
    ap.add_argument("--thinking", action="store_true", help="保留思考链（更慢、更贵）")
    ap.add_argument("--tries", type=int, default=4)
    a = ap.parse_args()

    prompt = sys.stdin.read() if a.prompt_file == "-" else open(a.prompt_file, encoding="utf-8").read()
    if not prompt.strip():
        sys.exit("prompt 为空")
    key = load_key()

    last = None
    for i in range(a.tries):
        try:
            r = call(key, a.model, prompt, a.max_tokens, a.thinking)
            msg = r["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if not text:
                raise RuntimeError("content 为空：多半是思考链吃光了 token，检查 thinking 参数或调大 --max-tokens")
            u = r.get("usage", {})
            print(f"[kimi] {a.model} 完成 prompt={u.get('prompt_tokens')} completion={u.get('completion_tokens')} 字数={len(text)}",
                  file=sys.stderr)
            if a.out:
                open(a.out, "w", encoding="utf-8").write(text + "\n")
                print(f"[kimi] 已写入 {a.out}", file=sys.stderr)
            else:
                print(text)
            return
        except Exception as e:                     # noqa: BLE001 — 网络/限流/空返回都重试
            last = e
            wait = 5 * (2 ** i)
            print(f"[kimi] 第 {i + 1} 次失败：{e}；{wait}s 后重试", file=sys.stderr)
            time.sleep(wait)
    sys.exit(f"Kimi 调用失败（重试 {a.tries} 次）：{last}")


if __name__ == "__main__":
    main()
