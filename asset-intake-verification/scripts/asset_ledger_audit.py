#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""素材台账对账：比对 <库根>/<子目录>/*.gif 与 <库根>/README.md 里逐条登记的条目。

用法: python3 asset_ledger_audit.py [库根=~/Documents/素材/表情包] [子目录=GIF动图] [README=README.md]
输出: 条目数/文件数、重名、台账有登记但目录无文件、目录有文件但未登记、体积 Top5。

规则:
  - macOS 文件名是 NFD、README 文本多为 NFC，**必须先 unicodedata.normalize('NFC') 归一化**，
    否则同一名字会被判成不匹配、假报错位。
  - 发现错位**只报告，不自动配对/改名**：改名无实锤，交用户确认或拉源文件做 md5 比对。
纯标准库，任意 python3 都能跑。
"""
import os
import re
import sys
import unicodedata


def nfc(s):
    return unicodedata.normalize("NFC", s)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/素材/表情包")
    subdir = sys.argv[2] if len(sys.argv) > 2 else "GIF动图"
    readme_name = sys.argv[3] if len(sys.argv) > 3 else "README.md"

    readme_path = os.path.join(root, readme_name)
    asset_dir = os.path.join(root, subdir)
    if not os.path.isfile(readme_path) or not os.path.isdir(asset_dir):
        print(f"路径不对：{readme_path} / {asset_dir}")
        return 1

    readme = open(readme_path, encoding="utf-8").read()
    pattern = r"^- \*\*" + re.escape(subdir) + r"/([^*]+)\*\*"
    entries = [nfc(e) for e in re.findall(pattern, readme, flags=re.M)]
    files = {nfc(f) for f in os.listdir(asset_dir) if f.endswith(".gif")}

    print(f"台账条目数: {len(entries)}  |  {subdir}/ gif 数: {len(files)}")
    dupes = sorted({e for e in entries if entries.count(e) > 1})
    print(f"重名条目: {dupes if dupes else '无'}")

    missing = [e for e in entries if e not in files]
    print(f"\n[台账有登记 / 目录无文件] {len(missing)} 条:")
    for e in missing:
        for i, line in enumerate(readme.splitlines(), 1):
            if e in nfc(line):
                print(f"  L{i}: {line[:150]}")
                break

    unreg = sorted(files - set(entries))
    print(f"\n[目录有文件 / 台账无登记] {len(unreg)} 个:")
    for f in unreg:
        print(f"  {f}  ({os.path.getsize(os.path.join(asset_dir, f))} B)")

    sizes = sorted(((os.path.getsize(os.path.join(asset_dir, f)), f) for f in files), reverse=True)
    print("\n体积 Top5:")
    for s, f in sizes[:5]:
        print(f"  {s / 1e6:.1f}MB  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
