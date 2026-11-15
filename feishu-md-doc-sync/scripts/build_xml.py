#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 file_token 构建飞书 XML 文档内容 → feishu_doc.xml"""
import json
import os
import re
from xml.sax.saxutils import escape

BASE = "/Users/Jin/Documents/Hermes/feishu_sync"
DATA_FILE = os.path.join(BASE, "family_data.json")
STATE_FILE = os.path.join(BASE, "upload_state.json")
OUT_XML = os.path.join(BASE, "feishu_doc.xml")
IMG_WIDTH = "240"
SNAPSHOT = "2026-08-05"

data = json.load(open(DATA_FILE, encoding="utf-8"))
state = json.load(open(STATE_FILE, encoding="utf-8"))
uploads = state.get("uploads", {})

def esc(t):
    """XML 转义，保留反引号为普通字符"""
    return escape(t)

def prompt_text(t):
    """去掉英文提示词两侧的反引号"""
    t = t.strip()
    if len(t) >= 2 and t.startswith("`") and t.endswith("`"):
        return t[1:-1]
    return t

# ---- 构建 XML ----
parts = []

# 标题
parts.append(f"<title>{esc(data['doc_title'])}</title>")

# 开头说明（原文更新张数并标注快照）
intro = data["intro_paras"][0] if data["intro_paras"] else ""
intro = re.sub(r"^\d+\s*张", "225 张", intro)
parts.append(f"<p>{esc(intro)}（数据快照：{SNAPSHOT}，共 {data['total_imgs']} 张原图）</p>")

# tip 使用方式 → callout
if data["tip_lines"]:
    tip_body = "".join(f"<p>{esc(ln)}</p>" for ln in data["tip_lines"] if ln)
    parts.append(f'<callout emoji="bulb">{tip_body}</callout>')

# 家族
for fam in data["families"]:
    parts.append(f"<h2>{esc(fam['name'])}（{len(fam['rows'])} 张）</h2>")
    # 模板 callout（abstract）
    if fam["abstract"]:
        # 解析模板文本：适用 / 画面元素 / 风格提示词（中文）/ 风格提示词（英文）
        abs_text = fam["abstract"]
        abs_paras = []
        # 按 **xxx**： 分段
        segs = re.split(r"\n(?=\*\*)", abs_text)
        for seg in segs:
            seg = seg.strip()
            if not seg:
                continue
            if seg.startswith("**"):
                m = re.match(r"\*\*(.+?)\*\*[：:]\s*(.*)", seg, re.S)
                if m:
                    label = m.group(1)
                    content = m.group(2).strip()
                    abs_paras.append(f"<p><b>{esc(label)}</b>：{esc(prompt_text(content))}</p>")
                    continue
            abs_paras.append(f"<p>{esc(seg)}</p>")
        parts.append(f'<callout emoji="abstract" background-color="blue">{chr(10).join(abs_paras)}</callout>')

    # 表格
    rows_xml = []
    for row in fam["rows"]:
        rel = row["img_rel"]
        token = uploads.get(rel, "")
        img_xml = ""
        if token and token != "MISSING":
            img_xml = f'<img src="{token}" width="{IMG_WIDTH}" name="{esc(row["file_name"])}"/>'
        else:
            img_xml = f"<p>[图缺失: {esc(row['file_name'])}]</p>"
        rows_xml.append(
            "<tr>"
            f"<td>{img_xml}</td>"
            f"<td><p>{esc(row['file_name'])}</p></td>"
            f"<td><p>{esc(row['elements'])}</p></td>"
            f"<td><p>{esc(row['prompt_cn'])}</p></td>"
            f"<td><p>{esc(prompt_text(row['prompt_en']))}</p></td>"
            "</tr>"
        )
    thead = ("<thead><tr>"
             "<th><p>样张</p></th><th><p>文件名</p></th><th><p>画面元素</p></th>"
             "<th><p>风格提示词（中文）</p></th><th><p>风格提示词（英文）</p></th>"
             "</tr></thead>")
    parts.append(f"<table><colgroup><col width=\"240\"/><col width=\"140\"/><col width=\"260\"/><col width=\"260\"/><col width=\"320\"/></colgroup>{thead}<tbody>{''.join(rows_xml)}</tbody></table>")

# 结尾说明
parts.append(f"<p>—— 本页由本地笔记《浏览器采集_视觉风格家谱.md》自动同步生成（快照 {SNAPSHOT}），图片均为 1640×2048 级原图。</p>")

xml_content = "\n".join(parts)
with open(OUT_XML, "w", encoding="utf-8") as f:
    f.write(xml_content)

print(f"XML 生成: {OUT_XML} ({len(xml_content)} bytes)")
print(f"图片引用: {sum(1 for t in uploads.values() if t and t != 'MISSING')} / {data['total_imgs']}")
missing = [rel for rel, t in uploads.items() if not t or t == "MISSING"]
if missing:
    print("未上传图片:", missing[:10])
