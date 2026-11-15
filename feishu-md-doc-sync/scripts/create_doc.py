#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建骨架文档 + 逐家族 append，带超时重试与断点续跑"""
import json
import subprocess
import os
import sys
import time

BASE = "/Users/Jin/Documents/Hermes/feishu_sync"
STATE_FILE = os.path.join(BASE, "create_state.json")

state = {}
if os.path.exists(STATE_FILE):
    state = json.load(open(STATE_FILE, encoding="utf-8"))

def run(args, cwd=BASE, timeout=180):
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return r.returncode, r.stdout, r.stderr

def parse(out):
    try:
        return json.loads(out)
    except Exception:
        return None

# 1. 创建骨架
doc_id = state.get("doc_id")
if not doc_id:
    rc, out, err = run(["lark-cli", "docs", "+create", "--content", "@skeleton.xml"], timeout=300)
    d = parse(out)
    if d and d.get("ok"):
        doc_id = d["data"]["document"]["document_id"]
        state["doc_id"] = doc_id
        state["url"] = d["data"]["document"]["url"]
        json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("骨架创建:", doc_id)
    else:
        print("骨架创建失败:", out[:400], err[:200])
        sys.exit(1)

# 2. 逐家族 append
done = set(state.get("appended", []))
for idx in range(1, 12):
    fam_file = f"family_{idx:02d}.xml"
    if idx in done:
        print(f"[{idx}/11] 跳过（已完成）: {fam_file}")
        continue
    ok = False
    for attempt in range(3):
        try:
            rc, out, err = run(["lark-cli", "docs", "+update", "--doc", doc_id,
                                "--command", "append", "--content", f"@{fam_file}"], timeout=300)
        except subprocess.TimeoutExpired:
            print(f"[{idx}/11] {fam_file} 超时（第{attempt+1}次）")
            time.sleep(5)
            continue
        d = parse(out)
        if d and d.get("ok"):
            ok = True
            break
        print(f"[{idx}/11] {fam_file} 失败（第{attempt+1}次）: {out[:150]}")
        time.sleep(5)
    if not ok:
        print(f"[{idx}/11] {fam_file} 三次失败，中断。可重跑脚本续传。")
        json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        sys.exit(2)
    done.add(idx)
    state["appended"] = sorted(done)
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[{idx}/11] OK {fam_file}")

print("\n全部完成:", state.get("url", doc_id))
