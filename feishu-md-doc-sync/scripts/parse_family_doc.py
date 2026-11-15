#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 浏览器采集_视觉风格家谱.md → family_data.json（家族/模板/表格行/图片路径）"""
import json
import re
import os

SRC = "/Users/Jin/Documents/医时知识库/视觉风格参考/浏览器采集_视觉风格家谱.md"
OUT = "/Users/Jin/Documents/Hermes/feishu_sync/family_data.json"

with open(SRC, encoding="utf-8") as f:
    text = f.read()

lines = text.split("\n")

doc_title = None
intro_paras = []      # 标题后到第一个 ## 之间的说明段落
tip_lines = []        # tip callout 内容
families = []         # 家族列表

i = 0
# 跳过 YAML frontmatter
if lines and lines[0].strip() == "---":
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        i += 1
    i += 1  # 跳过结束 ---

# 标题（跳过前导空行）
while i < len(lines) and not lines[i].strip():
    i += 1
if i < len(lines) and lines[i].startswith("# "):
    doc_title = lines[i][2:].strip()
    i += 1

# 开头说明 + tip
in_tip = False
while i < len(lines):
    ln = lines[i].strip()
    if ln.startswith("## "):
        break
    if ln.startswith("> [!tip]"):
        in_tip = True
        i += 1
        continue
    if in_tip:
        if ln.startswith("> "):
            tip_lines.append(ln[2:].strip())
            i += 1
            continue
        elif ln == ">":
            i += 1
            continue
        else:
            in_tip = False
    if ln:
        intro_paras.append(ln)
    i += 1

# 家族
cur_family = None
in_abstract = False
abs_lines = []
while i < len(lines):
    ln = lines[i].strip()
    if ln.startswith("## "):
        if cur_family:
            if abs_lines:
                cur_family["abstract"] = "\n".join(abs_lines)
            families.append(cur_family)
        m = re.match(r"## (.+?)(?:（(\d+) 张）)?$", ln)
        name = m.group(1).strip() if m else ln[3:].strip()
        cur_family = {
            "name": name,
            "count_hint": m.group(2) if m else None,
            "abstract": "",
            "rows": [],
        }
        in_abstract = False
        abs_lines = []
        i += 1
        continue
    if cur_family is None:
        i += 1
        continue
    if ln.startswith("> [!abstract]"):
        in_abstract = True
        abs_lines = []
        i += 1
        continue
    if in_abstract:
        if ln.startswith("> "):
            abs_lines.append(ln[2:].strip())
            i += 1
            continue
        elif ln == ">":
            i += 1
            continue
        else:
            in_abstract = False
    if ln.startswith("|"):
        # 表格行
        cells = [c.strip() for c in ln.strip("|").split("|")]
        # 跳过表头/分隔行
        if cells and cells[0] == "样张":
            i += 1
            continue
        if cells and re.fullmatch(r":?-{2,}:?", cells[0]):
            i += 1
            continue
        if len(cells) >= 5:
            img_src_m = re.search(r'src="([^"]+)"', cells[0])
            img_path = img_src_m.group(1) if img_src_m else ""
            fname_m = re.search(r'alt="([^"]*)"', cells[0])
            fname = fname_m.group(1) if fname_m else cells[1]
            cur_family["rows"].append({
                "img_rel": img_path,
                "file_name": fname or cells[1],
                "elements": cells[2],
                "prompt_cn": cells[3],
                "prompt_en": cells[4],
            })
        i += 1
        continue
    i += 1

if cur_family:
    if abs_lines:
        cur_family["abstract"] = "\n".join(abs_lines)
    families.append(cur_family)

# 汇总
total_imgs = sum(len(f["rows"]) for f in families)
data = {
    "doc_title": doc_title,
    "intro_paras": intro_paras,
    "tip_lines": tip_lines,
    "families": [
        {
            "name": f["name"],
            "abstract": "\n".join(abs_lines),
            "rows": f["rows"],
        }
        for f in families
    ],
    "total_imgs": total_imgs,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"标题: {doc_title}")
print(f"说明段落: {len(intro_paras)}, tip 行: {len(tip_lines)}")
print(f"家族数: {len(families)}, 图片总数: {total_imgs}")
for f in families:
    print(f"  - {f['name']}: {len(f['rows'])} 张, 模板{'有' if f['abstract'] else '无'}")
# 校验图片路径存在性
missing = []
for f in families:
    for r in f["rows"]:
        p = os.path.join(os.path.dirname(SRC), r["img_rel"])
        if not os.path.exists(p):
            missing.append(r["img_rel"])
print(f"缺失图片: {len(missing)}")
for m in missing[:10]:
    print("   ", m)
