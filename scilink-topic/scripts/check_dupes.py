#!/usr/bin/env python3
"""扫描选题库重复记录：同 DOI，或标题高度相似（bigram Jaccard）。

用法：
  python3 scripts/check_dupes.py --in /tmp/lib.ndjson
  python3 scripts/check_dupes.py --in /tmp/lib.ndjson --delete --as user

判据：DOI 字符串相等（最硬）；否则标题去标点后 bigram Jaccard >= --thr（默认 0.42）。
保留「话题度」高的一条；同分保留「原文发布日期」更新的。
--delete 走 `lark-cli base +record-delete --record-id <recX> --yes`，删低分那条。
默认只报告，不动数据。
"""
import argparse
import itertools
import json
import re
import subprocess
import sys

DOI_RE = re.compile(r'10\.\d{4,9}/[^\s，。]+')


def doi_of(row):
    v = row.get('DOI链接') or row.get('DOI') or ''
    m = DOI_RE.search(str(v))
    return m.group(0).rstrip(').,').lower() if m else ''


def norm(t):
    return re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', t or '')


def bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)}


def scan(rows, thr):
    groups, seen = [], set()
    for a, b in itertools.combinations(rows, 2):
        ta = norm(a.get('内容标题'))
        tb = norm(b.get('内容标题'))
        if len(ta) < 8 or len(tb) < 8:
            continue
        da, db = doi_of(a), doi_of(b)
        same = bool(da) and da == db
        ba, bb = bigrams(ta), bigrams(tb)
        union = len(ba | bb)
        sim = (len(ba & bb) / union) if union else 0.0
        if not (same or sim >= thr):
            continue
        pair = tuple(sorted([a.get('record_id'), b.get('record_id')]))
        if pair in seen:
            continue
        seen.add(pair)
        groups.append((same, round(sim, 2), a, b))
    return groups


def pick(keep_first, other):
    s1 = keep_first.get('话题度') or 0
    s2 = other.get('话题度') or 0
    if s1 != s2:
        return (keep_first, other) if s1 > s2 else (other, keep_first)
    d1 = str(keep_first.get('原文发布日期') or '')
    d2 = str(other.get('原文发布日期') or '')
    return (keep_first, other) if d1 >= d2 else (other, keep_first)


def delete(rec_id, base, table, as_identity):
    cmd = ['lark-cli', 'base', '+record-delete', '--base-token', base,
           '--table-id', table, '--record-id', rec_id, '--yes', '--as', as_identity]
    p = subprocess.run(cmd, capture_output=True, text=True)
    ok = p.returncode == 0 and '"ok": true' in (p.stdout or '').replace('\n', ' ')
    return ok, (p.stdout or p.stderr or '')[:160]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True, help='record-list --format ndjson 的输出')
    ap.add_argument('--thr', type=float, default=0.42, help='标题相似度阈值')
    ap.add_argument('--delete', action='store_true', help='真的删低分那条（默认只报告）')
    ap.add_argument('--base-token', default='PCm9b6saQaJ8gmsqAxTcqWHtnVj')
    ap.add_argument('--table-id', default='tblfAf9h81t9oVq9')
    ap.add_argument('--as', dest='as_identity', default='user')
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.inp, encoding='utf-8') if l.strip()]
    groups = scan(rows, args.thr)
    print(f'表内 {len(rows)} 条 | 疑似重复 {len(groups)} 组')
    if not groups:
        return
    for same, sim, a, b in groups:
        keep, drop = pick(a, b)
        tag = 'DOI相同' if same else f'标题相似 {sim}'
        print(f"\n[{tag}] 保留 {keep.get('话题度')} 分 {keep.get('record_id')} {(keep.get('内容标题') or '')[:46]}")
        print(f"           删掉 {drop.get('话题度')} 分 {drop.get('record_id')} {(drop.get('内容标题') or '')[:46]}")
        if args.delete:
            ok, msg = delete(drop.get('record_id'), args.base_token, args.table_id, args.as_identity)
            print('           ->', 'deleted' if ok else f'FAILED {msg}')
    if not args.delete:
        print('\n（只报告模式。确认无误后加 --delete 真正删除低分那条）')


if __name__ == '__main__':
    main()
