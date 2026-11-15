#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 libtv 画布节点拉取无水印原图（正确做法，勿用 `libtv download`）：
`libtv node <名>` 查询 data.url[] 的 CDN 原 URL → urllib 直接下载。
已验证：CLI download 会叠加「AI生成」+「LibTV」水印且 --without-ai-watermark/--vip 无效；
CDN 原 URL 是无水印的。用法: python3 fetch_originals.py [节点名...]
（在 libtv 工作目录运行；改 NODES 列表即可批量）
"""
import subprocess, json, os, sys, urllib.request

ENV = dict(os.environ)
ENV["PATH"] = "/Users/Jin/.libtv:" + ENV.get("PATH", "")

NODES = [f"S{i}-p1封面" for i in range(1, 11)] + [f"S{i}-p2方法卡" for i in range(1, 11)]

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=120)

def fetch(url, dst):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    open(dst, "wb").write(data)
    return len(data)

def main():
    nodes = sys.argv[1:] or NODES
    for node in nodes:
        r = run(["libtv", "node", node])
        try:
            d = json.loads(r.stdout)
            urls = d.get("data", {}).get("url", [])
        except Exception as e:
            print(f"! {node} 解析失败: {e}")
            continue
        if not urls:
            print(f"! {node} 无 url")
            continue
        for i, u in enumerate(urls, 1):
            dst = f"{node}_{i}.png"
            try:
                n = fetch(u, dst)
                print(f"OK {node}_{i} {n//1024}KB")
            except Exception as e:
                print(f"! {node}_{i} 下载失败: {e}")

if __name__ == "__main__":
    main()
