#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文字卡校验：像素级（溢出/贴边）+ 文字级（双向核对用户原稿是否被改）

用法：
  python3 verify_cards.py --png  <png目录>                        # 像素级校验
  python3 verify_cards.py --text <原稿.txt> <pages目录>            # 双向文字核对
        [--layout "品牌名" --layout "页码" ...]                    # 声明你加过的版式文字
  python3 verify_cards.py --marks <pages目录>                      # 逐页高亮清单

为什么几何问题必须看像素，而不是看视觉模型：
  拼版缩略图分辨率不足，视觉模型会把最空的一张报成「最挤」；而且正文（两端对齐）的行宽
  和页脚横线一样宽，用「最宽的行」当横线会定位错。

为什么文字要双向核对：
  正向只能证明「原稿的每段都还在」，证明不了「你没往里面塞自己的话」。
  反向残差才是私加内容的探测器。
"""
import argparse
import os
import re
import sys

try:
    from PIL import Image
    import numpy as np
except ImportError:
    sys.exit("需要 Pillow 与 numpy：pip install pillow numpy")


def visible_text(html: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", h))


def find_footer_rule(ink):
    """自底向上找页脚横线：底部 15% 内、span 宽、且行内填充率 > 0.9 的实线。

    自底向上是关键：封面时间轴、目录分隔线同样是「宽度拉满的实线」，
    自上而下扫描会先撞上它们，把内容末行定位错。
    行内填充率是关键：正文行宽度和横线相当，只有横线的填充率接近 1.0。
    """
    H, W = ink.shape
    min_span = int(W * 0.72)
    for y in range(H - 1, int(H * 0.85), -1):
        nz = np.nonzero(ink[y])[0]
        if len(nz) < 100:
            continue
        span = nz.max() - nz.min() + 1
        if span < min_span:
            continue
        if len(nz) / span > 0.9:
            return y
    return None


def check_px(png_dir, paper=(252, 251, 248), scale=2):
    paper = np.array(paper)
    safe_min = 44 * scale
    comfy = 60 * scale
    bad = []
    print(f"{'页':>6} {'页脚线y':>8} {'内容末y':>8} {'距线':>7} {'左':>6} {'右':>6}  判断")
    for f in sorted(os.listdir(png_dir)):
        if not f.lower().endswith(".png"):
            continue
        im = Image.open(os.path.join(png_dir, f)).convert("RGB")
        a = np.asarray(im).astype(np.int16)
        ink = np.abs(a - paper).max(axis=2) > 12
        H, W = ink.shape
        rule = find_footer_rule(ink)
        if rule is None:
            print(f"{f[:6]:>6}  未找到页脚横线（页脚无 border-top？）")
            continue
        nz = np.nonzero(ink[: rule - 4].sum(axis=1))[0]
        end = int(nz.max()) if len(nz) else 0
        cols = np.nonzero(ink.sum(axis=0))[0]
        gap = rule - end
        tag = "OK" if gap >= comfy else ("尚可" if gap >= safe_min else "⚠️溢出/贴页脚")
        if gap < safe_min:
            bad.append(f)
        print(f"{f[:6]:>6} {rule:>8} {end:>8} {gap:>7} {cols.min():>6} {W - cols.max():>6}  {tag}")
    print(f"\n溢出/贴边页: {bad if bad else '无'}")
    return bad


def check_text(src_txt, pages_dir, layout_strings):
    norm = lambda s: re.sub(r"\s+", "", s)
    src_lines = [l.strip() for l in open(src_txt, encoding="utf-8") if l.strip()]
    all_text = "".join(
        visible_text(open(os.path.join(pages_dir, f), encoding="utf-8").read())
        for f in sorted(os.listdir(pages_dir)) if f.endswith(".html")
    )
    print("=== 正向：原稿每一段是否原样出现在渲染结果里 ===")
    missing = []
    for i, line in enumerate(src_lines, 1):
        if norm(line) in all_text:
            print(f"  ✓ 第{i:>3}行")
        else:
            key = norm(line)
            j = next((k for k in range(len(key)) if key[: k + 1] not in all_text), 0)
            missing.append(i)
            print(f"  ✗ 第{i:>3}行  首个不匹配处: …{line[max(0, j - 25): j + 25]}…")

    print("\n=== 反向：渲染结果里有没有原稿之外的正文（= 你没报备的私加内容）===")
    resid = all_text
    for s in [norm(x) for x in src_lines] + [norm(x) for x in layout_strings]:
        resid = resid.replace(s, "")
    if resid:
        print(f"  ⚠️ 残差 {len(resid)} 字，逐项确认是否已向用户报备：\n  {resid!r}")
    else:
        print("  ✓ 残差为空：页面上只有原稿内容 + 你声明的版式文字")
    print("\n提示：章节号「一、」在版面上常被拆成「一」+ 标题两段渲染，顿号会消失——")
    print("      这属于版式改动，要在交付时说明并给出恢复办法，别让它悄悄混在残差里。")
    return missing


def check_marks(pages_dir):
    """逐页列出实际渲染的 <mark> 术语与条数。

    高亮清单是字符串事实，只能从 HTML 源码统计：拼版缩略图分辨率不足，
    实测视觉模型会把没标记的词报成高亮、又把真标记的漏掉。
    顺带按段检查上限（每段 3 处）——超了就该按优先级砍。
    """
    total = 0
    print("=== 每页实际高亮（从 HTML 源码统计）===")
    for f in sorted(os.listdir(pages_dir)):
        if not f.endswith(".html"):
            continue
        h = open(os.path.join(pages_dir, f), encoding="utf-8").read()
        marks = re.findall(r'<mark[^>]*>(.*?)</mark>', h, flags=re.S)
        soft = len(re.findall(r'<mark class="soft"', h))
        total += len(marks)
        head = f"\n{f[:6]}  共 {len(marks)} 处"
        print(head + (f"（其中淡笔 .soft {soft} 处）" if soft else ""))
        for m in marks:
            print(f"     • {m}")
        for i, para in enumerate(re.findall(r'<p class="p">(.*?)</p>', h, flags=re.S), 1):
            n = len(re.findall(r'<mark[^>]*>', para))
            if n > 3:
                print(f"     ⚠️ 第{i}段有 {n} 处高亮，超过上限 3")
    print(f"\n全套高亮合计 {total} 处")
    print("提醒：整套高亮少于 6 处通常意味着术语没标到位；单页某段 3 处以上则是过密。")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", help="PNG 目录，做像素级校验")
    ap.add_argument("--text", nargs=2, metavar=("原稿.txt", "pages目录"), help="双向文字核对")
    ap.add_argument("--layout", action="append", default=[],
                    help="你加过的版式文字（品牌名、页码、目录标题等），可重复")
    ap.add_argument("--scale", type=int, default=2, help="渲染倍率，默认 2")
    ap.add_argument("--marks", help="pages目录，逐页列出 <mark> 高亮清单")
    args = ap.parse_args()
    if not args.png and not args.text and not args.marks:
        ap.error("至少给 --png / --text / --marks 之一")
    if args.png:
        check_px(args.png, scale=args.scale)
    if args.text:
        if args.png:
            print()
        check_text(args.text[0], args.text[1], args.layout)
    if args.marks:
        if args.png or args.text:
            print()
        check_marks(args.marks)


if __name__ == "__main__":
    main()
