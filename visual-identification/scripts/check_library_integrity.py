#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""素材库台账核对：README.md 条目 <-> 实体素材文件 双向比对（只读，不改任何文件）。

用法:
    python3 check_library_integrity.py [素材库根目录]
默认根目录: ~/Documents/素材/表情包

输出三类问题:
  A. README 有登记、目录里没有文件（条目悬空）
  B. 目录里有文件、README 没有登记（登记缺漏）
  C. README 内重复条目（同 ID 重复入库会这样）

发现错位只报告，不自行配对改名——名字像 != 同一张。要实锤就用完整签名 URL 拉源文件比 md5
（短链会超时），或让用户给对应关系。
"""
import datetime
import os
import re
import sys
import unicodedata

BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/素材/表情包")
ENTRY_DIR = "GIF动图"          # README 条目前缀里的子目录名
README = os.path.join(BASE, "README.md")


def nfc(s):
    # macOS 磁盘上的中文名多为 NFD，README 文本是 NFC；不归一化会把同一文件虚报成两条错位
    return unicodedata.normalize("NFC", s)


def main():
    readme = open(README, encoding="utf-8").read()
    entries = [nfc(e) for e in re.findall(r"^- \*\*" + ENTRY_DIR + r"/([^*]+)\*\*", readme, flags=re.M)]
    # 只收目标后缀，顺带滤掉 .DS_Store 等非素材文件
    files = {nfc(f) for f in os.listdir(os.path.join(BASE, ENTRY_DIR))
             if f.lower().endswith((".gif", ".png", ".jpg", ".mp3"))}

    dupes = sorted({e for e in entries if entries.count(e) > 1})
    orphan_entries = [e for e in entries if e not in files]
    orphan_files = sorted(files - set(entries))

    print("库根目录: %s" % BASE)
    print("README 条目 %d 条 | %s/ 素材 %d 个" % (len(entries), ENTRY_DIR, len(files)))

    if dupes:
        print("\n[C] README 内重复条目:")
        for d in dupes:
            print("   ", d)

    print("\n[A] README 有登记、目录无文件:")
    for e in orphan_entries or ["(无)"]:
        line_no = next((i for i, l in enumerate(readme.splitlines(), 1) if e in nfc(l)), "?")
        print("   L%s  %s" % (line_no, e))

    print("\n[B] 目录有文件、README 无登记:")
    for f in orphan_files or ["(无)"]:
        p = os.path.join(BASE, ENTRY_DIR, f)
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(p))
        print("    %s  %.1fMB  改动于 %s" % (f, os.path.getsize(p) / 1e6, mt.strftime("%Y-%m-%d %H:%M")))

    if orphan_entries or orphan_files or dupes:
        print("\n注意：不要自行配对改名。先让用户确认对应关系（或拉源文件比 md5）再改台账。")
        print("      B 类里「改动于」很近的多半是用户当天自己拖进来的，可优先问问是不是漏登记。")
    else:
        print("\n台账与实物一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
