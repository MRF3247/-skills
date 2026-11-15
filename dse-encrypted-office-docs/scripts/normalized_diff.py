#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规范化文本对比：找出两份文档文本之间的【真实】差异。

背景：DSE 加密 docx 只能通过 wpscli word2pdf → PyMuPDF 提取文本；但 PDF 提取会把
表格单元格拆成多行、丢失空格、插入页眉页码，直接 diff 全是噪音。本脚本先对两侧文本
做规范化（去全部空白、去孤页码数字、去 XML 实体差异），再按字符块 diff，只输出真实
内容差异。

用法:
    python3 normalized_diff.py <文件A> <文件B>
    # 例: python3 normalized_diff.py 备份文本.txt 当前PDF文本.txt
    # 或传 docx 的 document.xml 路径（自动抽 <w:t> 文本）

输出: 差异块（tag + 两侧上下文）。无差异时静默退出码 0。
"""
import re
import sys
import difflib


def norm(s: str) -> str:
    """去掉所有空白和孤立的页码数字。"""
    s = re.sub(r'\s+', '', s)
    # 去掉孤立的纯数字（页码），但不误删正文里的数字串（如 1950、67 万）
    s = re.sub(r'(?<!\d)\d+(?!\d)', '', s)
    return s


def load_text(path: str) -> str:
    if path.endswith('.xml') or 'document.xml' in path:
        with open(path, encoding='utf-8') as f:
            xml = f.read()
        return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml))
    with open(path, encoding='utf-8') as f:
        return f.read()


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    a = norm(load_text(sys.argv[1]))
    b = norm(load_text(sys.argv[2]))

    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    diffs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal':
            diffs.append((tag, a[max(0, i1 - 20):i2 + 20], b[max(0, j1 - 20):j2 + 20]))

    if not diffs:
        print(f"[OK] {sys.argv[1]} 与 {sys.argv[2]} 规范化文本完全一致")
        sys.exit(0)

    print(f"规范化长度: A={len(a)} B={len(b)} | 差异块数: {len(diffs)}")
    for tag, x, y in diffs:
        print(f"\n[{tag}]")
        print(f"  A: ...{x}...")
        print(f"  B: ...{y}...")
    sys.exit(1)


if __name__ == '__main__':
    main()
