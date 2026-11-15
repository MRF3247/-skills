#!/usr/bin/env python3
"""把 <digest_dir>/<card_id>.json 合并进 data.js 的 MEANINGS（追加书键，保留已有书）。
用法: python3 merge_book.py <digest_dir> <book_id>
digest 文件格式: {"<card_id>": {"<book_id>": {"digest": "...", "notes": {...}}}}
校验: [[术语]] 必须有 notes 键（缺失的自动摘除标记）、digest ≥180 字。
流程: python 校验+汇总 -> node eval 提取现有 MEANINGS -> 合并 -> node 重写 data.js。
（多次实战通过；勿改成 python 正则解析 JS 字面量。）
书序列表 ORDER 动态收集（扫 MEANINGS 全部书键 + 新书合并去重），加 b11/b12 无需改本脚本；重写条目时 digest/notes 之外的额外字段（如 b08 的 topics 话题表）原样序列化保留，后续合并不会把已上线的结构化维度冲掉。
部分覆盖的书（如 b10 宫廷牌仅 16 张）用环境变量 PARTIAL=1 跳过 78 张全量校验，改为只合并 digest 目录里实际存在的文件：
  PARTIAL=1 python3 merge_book.py <digest_dir> <book_id>
"""
import json, re, sys, subprocess, os

if len(sys.argv) != 3:
    sys.exit(__doc__)
DIR, BOOK = sys.argv[1], sys.argv[2]
PARTIAL = os.environ.get("PARTIAL") == "1"
DATA_JS = os.path.expanduser("~/Documents/书籍/玄学/塔罗与占星/韦特塔罗全书/js/data.js")

majors = ['the-fool', 'the-magician', 'the-high-priestess', 'the-empress', 'the-emperor',
          'the-hierophant', 'the-lovers', 'the-chariot', 'strength', 'the-hermit',
          'wheel-of-fortune', 'justice', 'the-hanged-man', 'death', 'temperance',
          'the-devil', 'the-tower', 'the-star', 'the-moon', 'the-sun', 'judgement', 'the-world']
ranks = list(range(1, 11)) + ['page', 'knight', 'queen', 'king']
all78 = majors + [f'{s}-{r}' for s in ['wands', 'cups', 'swords', 'pentacles'] for r in ranks]

book, bad = {}, []
ids = [f[:-5] for f in os.listdir(DIR) if f.endswith(".json")] if PARTIAL else all78
for cid in ids:
    try:
        with open(f"{DIR}/{cid}.json", encoding="utf-8") as f:
            e = json.load(f)[cid][BOOK]
        dg = e["digest"]
        missing = set(re.findall(r"\[\[(.+?)\]\]", dg)) - set(e.get("notes", {}))
        for t in missing:
            dg = dg.replace(f"[[{t}]]", t)
        assert len(dg) >= 180, f"digest 过短 {len(dg)}"
        book[cid] = {"digest": dg, "notes": e.get("notes", {})}
    except Exception as ex:
        bad.append((cid, str(ex)[:60]))
print(f"素材校验: {len(book)}/{len(ids)}")
if bad:
    print("问题:", bad)
    sys.exit(1)

json.dump(book, open("/tmp/_merge_book.json", "w", encoding="utf-8"), ensure_ascii=False)

js = r"""
const fs = require('fs');
const DATA_JS = process.argv[2], BOOK = process.argv[3];
const src = fs.readFileSync(DATA_JS, 'utf8');
const m = src.match(/const MEANINGS = \{[\s\S]*?\n\};/);
if (!m) { console.error('MEANINGS 块没匹配到'); process.exit(1); }
const MEANINGS = eval('(' + m[0].replace('const MEANINGS =', '').replace(/;\s*$/, '') + ')');
const add = JSON.parse(fs.readFileSync('/tmp/_merge_book.json', 'utf8'));
const orderSet = new Set(['b01','b02','b03','b04','b05','b06','b07','b08','b09','b10', BOOK]);
for (const e of Object.values(MEANINGS)) for (const k of Object.keys(e)) orderSet.add(k);
const ORDER = [...orderSet].sort();
for (const [cid, entry] of Object.entries(add)) {
  MEANINGS[cid] = MEANINGS[cid] || {};
  MEANINGS[cid][BOOK] = entry;
}
const lit = s => JSON.stringify(s);
let out = 'const MEANINGS = {\n';
for (const cid of Object.keys(MEANINGS)) {
  out += '  ' + lit(cid) + ': {\n';
  for (const bk of ORDER.filter(b => MEANINGS[cid][b])) {
    const e = MEANINGS[cid][bk];
    out += '    ' + bk + ': {\n      digest: ' + lit(e.digest) + ',\n      notes: {\n';
    for (const [t, b] of Object.entries(e.notes)) out += '        ' + lit(t) + ': ' + lit(b) + ',\n';
    out += '      },\n';
    for (const k of Object.keys(e)) if (k !== 'digest' && k !== 'notes') out += '      ' + k + ': ' + JSON.stringify(e[k]) + ',\n';
    out += '    },\n';
  }
  out += '  },\n';
}
out += '};';
fs.writeFileSync(DATA_JS, src.replace(m[0], out));
console.log('written, ' + BOOK + ' entries:', Object.values(MEANINGS).filter(e => e[BOOK]).length);
"""
with open("/tmp/_merge_book.js", "w", encoding="utf-8") as f:
    f.write(js)
r = subprocess.run(["node", "/tmp/_merge_book.js", DATA_JS, BOOK], capture_output=True, text=True)
print(r.stdout or r.stderr)
sys.exit(r.returncode)
