#!/usr/bin/env python3
"""Kimi K3 (k3-256k) 润色：把 DS 初稿重写成小红书可直接发布的文案。

用法：
  python3 polish_kimi.py --items /tmp/daily/items.json [--keys a,b,c] [--field DS建议正文] [--out Kimi润色正文]

items.json = [{ "key": "slug", "DS建议正文": "...", ... }, ...]，脚本原地写回 --out 字段。

坑（都实测过）：
  · endpoint 是 api.kimi.com/coding/v1（moonshot 域名用这把 key 回 401，api.kimi.com/v1 回 404）
  · temperature 只接受 1：传 0.6 直接 400 invalid temperature
  · k3 是推理模型：max_tokens 给小了 content 会是空串、只有 reasoning_content → 给 4000
"""
import argparse, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

KEYFILE = '/Users/Jin/Documents/Hermes/APIs/kimicode API.rtf'
URL = 'https://api.kimi.com/coding/v1/chat/completions'
MODEL = 'k3-256k'

SYS = """你是小红书医学科研内容编辑。把作者的初稿重写成可直接发布的文案，硬性要求：
1. 事实、数字、DOI、出处一律照抄，不得新增、夸大或删改；初稿没有的结论绝不补。
2. 去AI味：禁止"首先/其次/综上所述/在这个时代/让我们一起/不难发现/值得注意的是"这类腔调；禁止每段都排比。
3. 句子短，一句一个意思。第一句就抓人（痛点或反差切入），不铺垫背景。
4. 专业术语第一次出现时紧跟着用一句大白话解释，优先生活化比喻，用"（……）"或破折号带出。
5. 保留初稿的 emoji 位置与结构骨架，但可以更口语。
6. 正文里不写出处：不写期刊名+日期、不写"来源：X"、不写 DOI——出处统一放在表格的 DOI 列。
7. 结尾不写免责声明（用户已删除"⚠️仅为医学科研资讯分享……"这一族）；⚠️ 行只留初稿里的实质口径（研究限制、未获批等）。
8. 全文 ≤1000 字（含结尾 3-6 个 #话题标签）。
9. 直接输出正文，不要解释、不要标题、不要 markdown 代码块。"""


def api_key():
    raw = open(KEYFILE, encoding='utf-8', errors='ignore').read()
    m = re.search(r'sk-[A-Za-z0-9_\-]{10,}', raw)
    if not m:
        sys.exit('key not found in ' + KEYFILE)
    return m.group(0)


def call(prompt, max_tokens=4000):
    body = json.dumps({'model': MODEL, 'messages': [
        {'role': 'system', 'content': SYS},
        {'role': 'user', 'content': prompt}], 'max_tokens': max_tokens}).encode()
    last = None
    for _ in range(3):
        req = urllib.request.Request(URL, data=body, headers={
            'Authorization': 'Bearer ' + api_key(), 'Content-Type': 'application/json'})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=180).read())
            c = (d['choices'][0]['message'].get('content') or '').strip()
            if c:
                return c, None
            last = 'empty content: ' + str(d)[:150]
        except Exception as e:
            last = str(e)[:150]
        time.sleep(4)
    return None, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--items', required=True)
    ap.add_argument('--keys', default='')
    ap.add_argument('--field', default='DS建议正文')
    ap.add_argument('--out', default='Kimi润色正文')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    items = json.load(open(a.items))
    want = {k for k in a.keys.split(',') if k}
    todo = [i for i in items if (not want or i.get('key') in want)]

    def run(it):
        p = f"标题（{it.get('图文建议标题','')}）\n\n初稿：\n{it[a.field]}"
        out, err = call(p)
        return it.get('key'), out, err

    fails = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for key, out, err in ex.map(run, todo):
            if out:
                for it in items:
                    if it.get('key') == key:
                        it[a.out] = out
                print(key, 'OK', len(out), 'chars')
            else:
                fails += 1
                print(key, 'FAIL', err)
    json.dump(items, open(a.items, 'w'), ensure_ascii=False, indent=1)
    # 润色稿必须人工对差：模型爱自己补一句 hook，带出初稿没有的断言要删
    print(f'done {len(todo) - fails}/{len(todo)} → {a.items}（逐句对差后再入表）')


if __name__ == '__main__':
    main()
