#!/usr/bin/env python3
"""把 +record-list 的 ndjson 转成物料文档 XML（四图并排 grid + 文案），供 lark-cli docs +update 使用。

用法:
  python3 build_material_doc_xml.py <records.ndjson> <图片目录> [--text-field 润色正文] [--out-dir <目录>]

约定:
  - ndjson 每行一条记录，字段名用表格里的中文列名（内容标题/润色正文/DS建议正文/DOI/来源链接/内容分类/原文发布日期/封面建议文案/图文建议标题）。
  - 图片目录里按序号放 plainNN.png / coverNN.png / p2NN.png / p3NN.png（NN 从 01 起，与 ndjson 行序一致）。
  - 输出 xmlNN.xml，并打印 序号 -> 文件 与 标题 的映射，便于逐条 overwrite。
"""
import argparse
import json
import os
import sys

CAPTIONS = [
    ("plain", "封面（无文案）"),
    ("cover", "封面（带文案）"),
    ("p2", "P2 来源页截图"),
    ("p3", "P3 关键结果截图"),
]


def esc(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def paras(text):
    return "".join(f"<p>{esc(line)}</p>" for line in (text or "").split("\n") if line.strip())


def build(record, idx, text_field, img_dir):
    title = record.get("内容标题") or ""
    cover_text = record.get("封面建议文案") or ""
    post_title = record.get("图文建议标题") or ""
    body = (record.get(text_field) or record.get("DS建议正文") or "").strip()
    draft = (record.get("DS建议正文") or "").strip()
    doi = record.get("DOI") or ""
    src = record.get("来源链接") or ""
    cat = "、".join(record.get("内容分类") or []) if isinstance(record.get("内容分类"), list) else (record.get("内容分类") or "")
    date = (record.get("原文发布日期") or "")[:10]

    missing = [f"{stem}{idx:02d}.png" for stem, _ in CAPTIONS if not os.path.exists(os.path.join(img_dir, f"{stem}{idx:02d}.png"))]
    if missing:
        print(f"WARN 缺少图片: {', '.join(missing)}", file=sys.stderr)

    cols = "".join(
        f'<column width-ratio="0.25"><img path="@./{stem}{idx:02d}.png" caption="{cap}"/></column>'
        for stem, cap in CAPTIONS
    )
    out = [f"<title>{esc(title)}</title>", "<h1>封面与截图</h1>", f"<grid>{cols}</grid>",
           f"<p>封面文案：{esc(cover_text)}</p>", "<h1>图文标题</h1>", f"<p>{esc(post_title)}</p>",
           "<h1>正文</h1>", paras(body), "<h1>出处</h1>",
           f"<p>DOI：{esc(doi)}</p><p>来源链接：{esc(src)}</p><p>内容分类：{esc(cat)}</p><p>原文日期：{esc(date)}</p>"]
    if draft:
        out += ["<h1>附：DS 初稿</h1>", paras(draft)]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ndjson")
    ap.add_argument("img_dir")
    ap.add_argument("--text-field", default="润色正文", help="正文列名（Kimi润色正文/润色正文/DS建议正文）")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    out_dir = args.out_dir or args.img_dir
    os.makedirs(out_dir, exist_ok=True)
    with open(args.ndjson, encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh if line.strip()]

    for idx, record in enumerate(records, 1):
        xml = build(record, idx, args.text_field, args.img_dir)
        path = os.path.join(out_dir, f"xml{idx:02d}.xml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml)
        print(f"{idx}\t{os.path.abspath(path)}\t{record.get('record_id','')}\t{record.get('内容标题','')}")


if __name__ == "__main__":
    main()
