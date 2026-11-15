#!/usr/bin/env python3
"""正文 → 飞书 DocxXML 的唯一实现（不要手写/不要从会话历史里复制旧版）。

规则（用户 2026-10 多次强调，见 SKILL.md「文档排版（手机阅读优先）」）：
- 每句/每行一个独立 <p>，任何行首、段首都不允许有空格（全角也不例外）
- ▫️ 条目各自一个 <p> 且顶格
- 段与段之间插一个只含全角空格 U+3000 的 <p>
- 不用 <br/> 软换行（复制到小红书会全部并成一段）

用法：
    python3 body_xml.py 正文.md            # 输出 XML 到 stdout
    python3 body_xml.py 正文.md -o out.xml
    python3 body_xml.py 正文.md --check    # 只验收：行首空格 / <br/> / U+3000 用例
"""
import argparse
import html
import re
import sys

SPACER = "\u3000"          # 段间空行段
SENT_SPLIT = r"(?<=[。！？])"   # ；不拆：一个分号会把 ⚠️ 段塞断


def body_xml(text: str, spacer: str = SPACER) -> str:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    # 先把「连续的 ▫️ 段」合并成一个列表组：条目之间只换行、不换段、不空行
    grouped = []
    for b in blocks:
        is_list = all(ln.strip().startswith("▫️") for ln in b.split("\n") if ln.strip())
        if is_list and grouped and grouped[-1][1]:
            grouped[-1][0].extend([ln.strip() for ln in b.split("\n") if ln.strip()])
        else:
            grouped.append([[ln.strip() for ln in b.split("\n") if ln.strip()], is_list])

    out = []
    for bi, (lines, is_list) in enumerate(grouped):
        if is_list:
            # 列表条目各自一个 <p>（<br/> 复制到小红书会丢换行），条间不插空行段
            for x in lines:
                out.append("<p>" + html.escape(x) + "</p>")
        else:
            for line in lines:
                for sent in [x.strip() for x in re.split(SENT_SPLIT, line) if x.strip()]:
                    out.append("<p>" + html.escape(sent) + "</p>")
        if bi != len(grouped) - 1:
            out.append(f"<p>{spacer}</p>")
    return "\n".join(out)


def check(xml_out: str) -> list:
    problems = []
    if "\u3000\u3000" in xml_out:
        problems.append("出现连续两个全角空格（续行缩进回归）")
    for para in re.findall(r"<p>(.*?)</p>", xml_out, flags=re.S):
        if para == SPACER:
            continue
        if para[:1] in (" ", "\u3000", "\u00a0"):
            problems.append(f"段首有空格：{para[:18]!r}")
            break
        if ("<br/>" in para or "<br>" in para):
            problems.append(f"出现 <br/> 软换行（复制到小红书会丢）：{para[:20]!r}")
            break
    # 列表条目之间不允许插 　 空行段
    paras = [x for x in re.findall(r"<p>(.*?)</p>", xml_out, flags=re.S)]
    for i in range(len(paras) - 2):
        if paras[i].strip().startswith("▫️") and paras[i+1].strip() == SPACER and paras[i+2].strip().startswith("▫️"):
            problems.append("列表条目之间插了 　 空行段（会多出一行）")
            break
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    ap.add_argument("--check", action="store_true", help="只做验收，不写文件")
    a = ap.parse_args()
    text = open(a.src, encoding="utf-8").read()
    xml_out = body_xml(text)
    problems = check(xml_out)
    if problems:
        print("FAIL: " + "；".join(problems), file=sys.stderr)
        sys.exit(1)
    if a.check:
        print("OK: 行首无空格 / 无 <br/> / 无续行缩进")
        return
    if a.out:
        open(a.out, "w", encoding="utf-8").write(xml_out)
        print(f"written {a.out}  ({len(xml_out)} chars)")
    else:
        print(xml_out)


if __name__ == "__main__":
    main()
