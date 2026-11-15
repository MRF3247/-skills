#!/usr/bin/env bash
# Hermes 技能库体检：断链 / 归档 / 索引成本 / 疑似重复族
# 用法: bash skill_library_health_check.sh [skills_dir]
set -uo pipefail
SK="${1:-$HOME/.hermes/skills}"

if [ ! -d "$SK" ]; then echo "目录不存在: $SK"; exit 1; fi

echo "== 1) 断链（软链指向已失效 = 实际没装）=="
n=0
for f in "$SK"/*; do
  if [ -L "$f" ] && [ ! -e "$f" ]; then
    echo "  BROKEN $(basename "$f") -> $(readlink "$f")"
    n=$((n + 1))
  fi
done
echo "  合计 $n 条（清理前先留档，见 SKILL.md）"

echo
echo "== 2) 归档目录 .archive（隐藏目录，Hermes 不扫描 = 不可用）=="
if [ -d "$SK/.archive" ]; then
  find "$SK/.archive" -maxdepth 2 -name SKILL.md | wc -l | awk '{print "  归档技能 " $1 " 个"}'
else
  echo "  无 .archive"
fi

echo
echo "== 3) 索引成本 + 4) 疑似重复族 =="
python3 - "$SK" <<'PY'
import collections
import os
import re
import sys

SK = sys.argv[1]
rows = []
for root, dirs, files in os.walk(SK):
    if 'SKILL.md' not in files:
        continue
    t = open(os.path.join(root, 'SKILL.md'), encoding='utf-8', errors='replace').read()
    fm = t.split('---')[1] if t.startswith('---') else ''
    name = re.search(r'^name:\s*(.+)$', fm, re.M)
    desc = re.search(r'^description:\s*(.+)$', fm, re.M)
    rows.append((
        (name.group(1).strip().strip('"\'') if name else os.path.basename(root)),
        (desc.group(1).strip() if desc else ''),
    ))

total = sum(len(n) + len(d) + 6 for n, d in rows)
per = total / max(len(rows), 1) / 3.5
print(f"  技能数 {len(rows)}；索引约 {total} 字符 ≈ {total / 3.5:.0f} tokens/轮（每轮固定带）")
print(f"  平均每技能 ≈ {per:.0f} tokens → 删 100 个约省 {per * 100:.0f} tokens/轮")

fam = collections.Counter(n.split('-')[0] for n, _ in rows if '-' in n)
big = [(k, v) for k, v in fam.most_common() if v >= 3]
print("  疑似重复族（同前缀 >=3，多为多轮会话各写一次，合并前先比差异）:")
for k, v in big:
    members = sorted(n for n, _ in rows if n.startswith(k + '-'))
    shown = ', '.join(members[:8]) + (' ...' if v > 8 else '')
    print(f"    {k:22s} {v:3d} 个: {shown}")
PY
