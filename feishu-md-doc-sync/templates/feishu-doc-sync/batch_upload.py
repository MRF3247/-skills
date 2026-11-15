#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量上传本地图片到飞书临时文档，收集 file_token 映射（断点续跑，实测可用）。
用法: python3 batch_upload.py <images_dir> <data.json>
- data.json 内任意嵌套结构含 "img_rel": "子目录/图.jpg" 即可（脚本按文档顺序收集去重）
- 自动创建临时文档（标题固定），进度存同目录 upload_state.json（doc_id + uploads 映射）
- WebP/BMP 自动用 sips 探测尺寸补 --height（+media-insert 对非 PNG/JPEG/GIF 必须显式宽高）
- --file 必须相对路径且不越出 cwd → 以 images_dir 为 cwd 执行
- 上传完成后 file_token 供 XML 构建：<img src="<token>" width="240" name="文件名"/>
"""
import json
import os
import subprocess
import sys
import time

IMG_DIR = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
DATA_FILE = sys.argv[2] if len(sys.argv) > 2 else "data.json"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_state.json")
IMG_WIDTH = "240"  # 目标显示宽度 px

data = json.load(open(DATA_FILE, encoding="utf-8"))
state = json.load(open(STATE_FILE, encoding="utf-8")) if os.path.exists(STATE_FILE) else {}


def run(cmd, cwd=None, timeout=180):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def sips_size(path):
    """macOS sips 探测宽高（WebP/BMP 无自动尺寸检测时用）"""
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                       capture_output=True, text=True)
    w = h = None
    for ln in r.stdout.splitlines():
        if "pixelWidth" in ln:
            w = int(ln.split(":")[1].strip())
        if "pixelHeight" in ln:
            h = int(ln.split(":")[1].strip())
    return w, h


# 1. 临时文档
doc_id = state.get("doc_id")
if not doc_id:
    rc, out, err = run(["lark-cli", "docs", "+create", "--title", "临时-图片中转站（自动删除，勿动）"])
    try:
        doc_id = json.loads(out)["data"]["document"]["document_id"]
    except Exception:
        print("创建临时文档失败:", out[:500], err[:200])
        sys.exit(1)
    state["doc_id"] = doc_id
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("临时文档:", doc_id)

uploads = state.setdefault("uploads", {})

# 2. 收集全部 img_rel（保持出现顺序，去重）
all_rels, seen = [], set()


def walk(obj):
    if isinstance(obj, dict):
        if "img_rel" in obj:
            rel = obj["img_rel"]
            if rel not in seen:
                seen.add(rel)
                all_rels.append(rel)
        for v in obj.values():
            walk(v)
    elif isinstance(obj, list):
        for v in obj:
            walk(v)


walk(data)

print(f"共 {len(all_rels)} 张，已上传 {len(uploads)} 张")

# 3. 逐张上传（断点续跑 + 重试）
failures = []
for idx, rel in enumerate(all_rels, 1):
    if rel in uploads:
        continue
    abs_path = os.path.join(IMG_DIR, rel)
    if not os.path.exists(abs_path):
        print(f"[{idx}/{len(all_rels)}] 跳过（文件不存在）: {rel}")
        uploads[rel] = "MISSING"
        failures.append((rel, "file missing"))
        continue
    args = ["lark-cli", "docs", "+media-insert", "--doc", doc_id,
            "--file", "./" + rel, "--width", IMG_WIDTH]
    if os.path.splitext(rel)[1].lower() in (".webp", ".bmp"):
        w, h = sips_size(abs_path)
        if w and h:
            args += ["--height", str(int(h * int(IMG_WIDTH) / w))]
    ok = False
    for attempt in range(4):
        rc, out, err = run(args, cwd=IMG_DIR)
        if rc == 0:
            try:
                token = json.loads(out)["data"]["file_token"]
                uploads[rel] = token
                ok = True
                break
            except Exception:
                pass
        time.sleep(2 + attempt * 2)
    print(f"[{idx}/{len(all_rels)}] {'OK ' if ok else 'FAIL '}{rel}")
    if not ok:
        failures.append((rel, out[-200:] + err[-200:]))
    if idx % 5 == 0 or not ok:
        json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n完成: 成功 {len([v for v in uploads.values() if v != 'MISSING'])}/{len(all_rels)}")
for rel, why in failures:
    print("  FAIL:", rel, "|", why[:120])
