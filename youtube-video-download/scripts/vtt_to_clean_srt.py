#!/usr/bin/env python3
"""把 yt-dlp 下的 WebVTT 字幕转成干净的 SRT。

ffmpeg 直接 vtt->srt 会留下字面量 \\h、多余折行和重复行，本脚本自行解析。
用法: python vtt_to_clean_srt.py <file.vtt> [out.srt]
"""
import re
import sys


def clean_text(lines):
    txt = " ".join(lines)
    txt = re.sub(r"<[^>]+>", "", txt)          # <c>, <00:00:02.000> 等标签
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
    txt = txt.replace("&gt;", ">").replace("\\h", " ")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def fmt(ts):
    h, m, s = ts.split(":")
    return f"{int(h):02d}:{int(m):02d}:{s.replace('.', ',')}"


def convert(src, dst=None):
    raw = open(src, encoding="utf-8-sig").read()
    dst = dst or re.sub(r"\.vtt$", ".srt", src)
    out, idx, seen = [], 0, set()
    for block in re.split(r"\n\s*\n", raw.strip()):
        if "-->" not in block:
            continue
        lines = [l for l in block.splitlines() if l.strip()]
        tline = next(l for l in lines if "-->" in l)
        m = re.match(r"([\d:.]+)\s*-->\s*([\d:.]+)", tline.strip())
        if not m:
            continue
        txt = clean_text([l for l in lines if "-->" not in l])
        # 滚动式自动字幕会产出大量逐词碎片，去掉与前一条完全相同或无内容的
        if not txt or txt in seen:
            continue
        seen.add(txt)
        idx += 1
        out.append(f"{idx}\n{fmt(m.group(1))} --> {fmt(m.group(2))}\n{txt}\n")
    open(dst, "w", encoding="utf-8").write("\n".join(out))
    print(f"OK {idx} cues -> {dst}")
    return dst


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
