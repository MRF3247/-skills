#!/usr/bin/env python3
"""IEP 词条翻译·父代理核验脚本：对比 scratch/iep-backups 原件与成品。

用法:
  python3 verify.py                 # 核验全部已含署名标记的文件
  python3 verify.py 关键词1 关键词2  # 只核验文件名含关键词的文件（如 'Aristotle Logic'）

检查项（全过才 [OK]）:
  1 原非空行 100% 按原序保留在成品中（子序列校验）
  2 translator: GLM 5.3 Flash 位于 frontmatter 结束 --- 之前
  3 署名标记「全部中文译文由 GLM 5.3 Flash 翻译」存在
  4 「> **译**」译块数 > 0
  5 成品无双重 \r
  6 防爆稿: 成品总行数 < 原行数×3+500
  7 顺序抽查: 每条「> **译**」译行的前一行不得仍是译行（译文必须紧跟原文之后）
退出码: 全过 0，有异常 1。
"""
import sys
from pathlib import Path

VAULT = Path("/Users/Jin/Documents/Obsidian Vault/哲学百科/IEP词条/原文存档")
BAK = Path("/Users/Jin/.hermes/cache/scratch/iep-backups")
FM_MARK = "translator: GLM 5.3 Flash"
SIGN = "全部中文译文由 GLM 5.3 Flash 翻译"


def is_subsequence(orig, new):
    cursor = 0
    for l in orig:
        try:
            i = new.index(l, cursor)
        except ValueError:
            return False
        cursor = i + 1
    return True


def check(path):
    raw = path.read_bytes().decode("utf-8", errors="replace")
    new = raw.splitlines()
    bak = BAK / path.name
    if not bak.exists():
        return False, "无备份原件"
    old = bak.read_text(encoding="utf-8", errors="replace").splitlines()
    orig = [l for l in old if l.strip()]
    kept = sum(1 for l in orig if l in new)
    if kept != len(orig):
        return False, f"原文被改: 保留 {kept}/{len(orig)}"
    if not is_subsequence(orig, new):
        return False, "原文行顺序被打乱"
    fm_end = new.index("---", 1) if len(new) > 1 and new[0].strip() == "---" else -1
    if fm_end < 0 or not any(FM_MARK in l for l in new[:fm_end]):
        return False, "translator 行不在 frontmatter 内"
    if SIGN not in raw:
        return False, "缺署名标记"
    para = sum(1 for l in new if l.startswith("> **译**"))
    if para == 0:
        return False, "无译块"
    if "\\r\\r" in repr(raw):
        return False, "存在双重 \\r"
    if len(new) >= len(old) * 3 + 500:
        return False, f"行数异常(疑似爆稿): {len(new)} vs 原 {len(old)}"
    bad_order = sum(
        1
        for i, l in enumerate(new)
        if l.startswith("> **译**")
        and i > 0
        and (new[i - 1].startswith("> **译**") or new[i - 1].startswith("**译**"))
    )
    if bad_order:
        return False, f"顺序异常: {bad_order} 条译行紧跟另一译行"
    return True, f"原非空 {len(orig)}｜译块 {para}｜行数 {len(new)}/{len(old)}"


def main():
    args = sys.argv[1:]
    if args:
        targets = [p for p in sorted(VAULT.glob("*.md")) if any(k in p.name for k in args)]
    else:
        targets = [
            p
            for p in sorted(VAULT.glob("*.md"))
            if SIGN in p.read_text(encoding="utf-8", errors="replace")
        ]
    if not targets:
        print("没有匹配的文件")
        return 1
    all_ok = True
    for p in targets:
        ok, msg = check(p)
        all_ok &= ok
        print(f"{'[OK]  ' if ok else '[异常]'} {p.name}: {msg}")
    total_files = list(VAULT.glob("*.md"))
    done = sum(1 for p in total_files if SIGN in p.read_text(encoding="utf-8", errors="replace"))
    print(f"\n进度: {done}/{len(total_files)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
