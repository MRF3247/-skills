#!/usr/bin/env python3
"""给「资讯内容选题库」的每条记录打「获取方式」标签（开放获取 / 付费墙 / 注册墙 / 待查）。

用法：
    python3 scripts/tag_access.py --base-token PCm9b6saQaJ8gmsqAxTcqWHtnVj \
        --table-id tblfAf9h81t9oVq9 --as user

逻辑：
  1. 读全表，只处理「DOI链接」列有值的记录（无 DOI 的条目没有论文，不打标签）；
  2. 用 OpenAlex（免 key）查 oa_status，按「出版社落地页能不能白读」判定：
     gold/hybrid/bronze/diamond      → 开放获取
     green（免费版在 arXiv/PMC/机构库）→ 有免费预印本
     closed                          → 按 DOI 前缀：Lancet 系 / AHA → 注册墙，其余 → 付费墙
  3. 预印本（10.64898 medRxiv / 10.1101 bioRxiv）一律开放获取；
  4. 查询失败按 付费墙 处理（保守，避免误标成免费）；
  5. 分批 update 回表，每批 50 条。

字段：获取方式 fldITOayUU（select：开放获取 Green / 有免费预印本 Wathet / 付费墙 Red / 注册墙 Orange / 待查 Gray）
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

FIELD_ID = 'fldITOayUU'
DOI_FIELD = 'DOI链接'
LANCET = re.compile(r'10\.1016/(j\.lan|s0140-6736|s2213|j\.eclinm)', re.I)
AHA = re.compile(r'10\.1161/', re.I)
PREPRINT = re.compile(r'10\.(64898|1101)/', re.I)


def lark(args):
    out = subprocess.run(['lark-cli'] + args, capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        # record-list --output 成功时 stdout 可能不是 JSON（只回 manifest 提示）
        return {'ok': out.returncode == 0, 'raw': out.stdout[:200]}


def classify(doi, oa_status, is_oa, primary_is_oa=None):
    if PREPRINT.search(doi):
        return '开放获取'
    # 出版社落地页自称付费 → 一律按付费处理（避免把 arXiv 上的稿子当成出版社免费）
    if primary_is_oa is False and oa_status in ('gold', 'hybrid', 'bronze', 'diamond'):
        return '付费墙'
    if oa_status == 'green':
        return '有免费预印本'   # 出版社页要订阅，免费的是 arXiv/PMC/机构库作者稿
    if is_oa and oa_status in ('gold', 'hybrid', 'bronze', 'diamond'):
        return '开放获取'
    if LANCET.search(doi) or AHA.search(doi):
        return '注册墙'
    return '付费墙'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-token', required=True)
    ap.add_argument('--table-id', required=True)
    ap.add_argument('--as', dest='identity', default='user')
    ap.add_argument('--force', action='store_true', help='重标全部有 DOI 的记录')
    args = ap.parse_args()

    path = '/tmp/_access_rows.ndjson'
    lark(['base', '+record-list', '--base-token', args.base_token, '--table-id', args.table_id,
          '--limit', '500', '--format', 'ndjson', '--output', path, '--overwrite', '--as', args.identity])
    rows = [json.loads(l) for l in open(path) if l.strip()]
    print(f'表内 {len(rows)} 条', flush=True)

    todo = []
    for r in rows:
        v = (r.get(DOI_FIELD) or '').strip()
        if not v:
            continue
        cur = r.get('获取方式')
        if isinstance(cur, list):
            cur = ','.join(cur)
        if cur and not args.force:
            continue
        m = re.search(r'10\.\d{4,9}/\S+', v)
        if m:
            todo.append((r['record_id'], m.group(0).rstrip('）)')))

    print(f'待打标签 {len(todo)} 条', flush=True)
    upd = {}
    for i, (rid, doi) in enumerate(todo, 1):
        try:
            req = urllib.request.Request(
                f'https://api.openalex.org/works/doi:{doi}?select=open_access,primary_location',
                headers={'User-Agent': 'Hermes/1.0 (mailto:jin@example.com)'})
            d = json.load(urllib.request.urlopen(req, timeout=20))
            oa = d.get('open_access') or {}
            pl = d.get('primary_location') or {}
            upd[rid] = {FIELD_ID: classify(doi, (oa.get('oa_status') or '').lower(), oa.get('is_oa'), pl.get('is_oa'))}
        except urllib.error.HTTPError:
            upd[rid] = {FIELD_ID: '付费墙'}
        except Exception:
            upd[rid] = {FIELD_ID: '待查'}
        time.sleep(0.25)
        if i % 50 == 0:
            print(f'  ...{i}/{len(todo)}', Counter(v[FIELD_ID] for v in upd.values()), flush=True)

    print('结果', Counter(v[FIELD_ID] for v in upd.values()))
    items = list(upd.items())
    for k in range(0, len(items), 50):
        payload = {'update_records': dict(items[k:k + 50])}
        f = f'/tmp/_access_upd_{k // 50}.json'
        json.dump(payload, open(f, 'w'), ensure_ascii=False)
        r = lark(['base', '+record-batch-update', '--base-token', args.base_token, '--table-id', args.table_id,
                  '--json', '@' + f, '--as', args.identity, '--format', 'json'])
        print(f'批{k // 50} ->', 'ok' if r.get('ok') else r.get('error', {}).get('message'))


if __name__ == '__main__':
    main()
