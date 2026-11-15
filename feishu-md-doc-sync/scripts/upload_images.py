#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量上传 225 张样张原图到飞书临时文档，收集 file_token 映射（断点续跑）"""
import json
import subprocess
import os
import sys
import time

BASE = "/Users/Jin/Documents/Hermes/feishu_sync"
IMG_DIR = "/Users/Jin/Documents/医时知识库/视觉风格参考"
STATE_FILE = os.path.join(BASE, "upload_state.json")
DATA_FILE = os.path.join(BASE, "family_data.json")
IMG_WIDTH = "240"

data = json.load(open(DATA_FILE, encoding="utf-8"))
state = {}
if os.path.exists(STATE_FILE):
    state = json.load(open(STATE_FILE, encoding="utf-8"))

def run(cmd, cwd=None, timeout=120):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return r.returncode, r.stdout, r.stderr

# 1. 确保临时文档存在
doc_id = state.get("doc_id")
if not doc_id:
    rc, out, err = run(["lark-cli", "docs", "+create", "--title", "临时-图片中转站（自动删除，勿动）"])
    try:
        doc_id = json.loads(out)["data"]["document"]["document_id"]
    except Exception:
        print("创建临时文档失败:", out[:500], err[:500])
        sys.exit(1)
    state["doc_id"] = doc_id
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("临时文档:", doc_id)

uploads = state.setdefault("uploads", {})

# 收集全部图片（保持家族顺序）
all_imgs = []
for fam in data["families"]:
    for row in fam["rows"]:
        all_imgs.append(row["img_rel"])

# 去重（同一路径可能出现在多个家族？保险起见保留顺序去重）
seen = set()
imgs = []
for p in all_imgs:
    if p not in seen:
        seen.add(p)
        imgs.append(p)

print(f"共 {len(imgs)} 张图，已上传 {len(uploads)} 张")

failures = []
for idx, rel in enumerate(imgs, 1):
    if rel in uploads:
        continue
    # 文件存在性
    abs_path = os.path.join(IMG_DIR, rel)
    if not os.path.exists(abs_path):
        print(f"[{idx}/{len(imgs)}] 跳过（文件不存在）: {rel}")
        failures.append((rel, "file missing"))
        uploads[rel] = "MISSING"
        continue
    # 上传
    ok = False
    for attempt in range(4):
        rc, out, err = run(
            ["lark-cli", "docs", "+media-insert",
             "--doc", doc_id,
             "--file", "./" + rel,
             "--width", IMG_WIDTH],
            cwd=IMG_DIR, timeout=180)
        if rc == 0:
            try:
                token = json.loads(out)["data"]["file_token"]
                uploads[rel] = token
                ok = True
                break
            except Exception:
                pass
        time.sleep(2 + attempt * 2)
    if ok:
        print(f"[{idx}/{len(imgs)}] OK {rel} -> {token}")
    else:
        print(f"[{idx}/{len(imgs)}] FAIL {rel}: {out[:200]} {err[:200]}")
        failures.append((rel, out[-200:] + err[-200:]))
    # 每张后保存状态（断点续跑）
    if idx % 5 == 0 or not ok:
        json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n完成: 成功 {len([v for v in uploads.values() if v != 'MISSING'])} / {len(imgs)}")
if failures:
    print("失败列表:")
    for rel, reason in failures:
        print("  ", rel, "|", reason[:120])
