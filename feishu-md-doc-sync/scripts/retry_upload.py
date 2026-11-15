#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补传失败/缺失的图片（webp 需要同时传 width+height，用 sips 探测尺寸）"""
import json
import subprocess
import os
import sys
import time

BASE = "/Users/Jin/Documents/Hermes/feishu_sync"
IMG_DIR = "/Users/Jin/Documents/医时知识库/视觉风格参考"
STATE_FILE = os.path.join(BASE, "upload_state.json")
IMG_WIDTH = "240"

state = json.load(open(STATE_FILE, encoding="utf-8"))
doc_id = state["doc_id"]
uploads = state.setdefault("uploads", {})
data = json.load(open(os.path.join(BASE, "family_data.json"), encoding="utf-8"))

# 从 family_data 找出所有缺少有效 token 的图
all_rels = []
for fam in data["families"]:
    for row in fam["rows"]:
        rel = row["img_rel"]
        if rel not in all_rels:
            all_rels.append(rel)

to_retry = [rel for rel in all_rels if not uploads.get(rel) or uploads.get(rel) == "MISSING"]
if not to_retry:
    print(f"没有需要补传的图片（{len(all_rels)} 张全部有 token）")
    sys.exit(0)

print(f"待补传: {len(to_retry)} 张")

def get_size(path):
    """用 sips 获取图片宽高"""
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                       capture_output=True, text=True)
    w = h = None
    for ln in r.stdout.splitlines():
        if "pixelWidth" in ln:
            w = int(ln.split(":")[1].strip())
        if "pixelHeight" in ln:
            h = int(ln.split(":")[1].strip())
    return w, h

def run(cmd, cwd=None, timeout=180):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return r.returncode, r.stdout, r.stderr

failures = []
for rel in to_retry:
    abs_path = os.path.join(IMG_DIR, rel)
    if not os.path.exists(abs_path):
        print(f"文件不存在: {rel}")
        failures.append(rel)
        continue
    ext = os.path.splitext(rel)[1].lower()
    args = ["lark-cli", "docs", "+media-insert", "--doc", doc_id,
            "--file", "./" + rel, "--width", IMG_WIDTH]
    if ext == ".webp":
        w, h = get_size(abs_path)
        if w and h:
            # 按 240px 宽等比算高
            args += ["--height", str(int(h * int(IMG_WIDTH) / w))]
        else:
            print(f"webp 尺寸探测失败: {rel}")
    ok = False
    for attempt in range(4):
        rc, out, err = run(args, cwd=IMG_DIR)
        if rc == 0:
            try:
                token = json.loads(out)["data"]["file_token"]
                uploads[rel] = token
                ok = True
                print(f"OK {rel} -> {token}")
                break
            except Exception:
                pass
        time.sleep(3)
    if not ok:
        print(f"FAIL {rel}")
        failures.append(rel)
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"\n补传完成: 成功 {len(to_retry) - len(failures)}/{len(to_retry)}")
if failures:
    print("仍失败:", failures)
