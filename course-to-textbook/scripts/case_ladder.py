"""
教材案例：用 NCBI E-utilities 真跑一条检索阶梯，拿到可写入正文的真实命中数
===========================================================================
用途：写“检索过程”类章节时，每一步的命中数必须是真实检索结果，不能编数量级。

用法：改 STEPS 里的检索式（别人问什么课题就换什么）→ 跑 → 输出每步命中数。
教材引用时务必带上脚本打印的检索日期。

无依赖（只用标准库）。PubMed 公开 API，不需登录。
"""

import json
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 示例案例：二甲双胍与心血管结局。步骤顺序要能演出「变少→反弹→再变少」
STEPS = [
    ("① 只输一个词", "metformin"),
    ("② 用主题词", "Metformin[MeSH Terms]"),
    ("③ 加疾病概念", "Metformin[MeSH Terms] AND Cardiovascular Diseases[MeSH Terms]"),
    ("④ 补自由词（OR，会反弹）",
     '(Metformin[MeSH Terms] OR metformin[tiab]) AND '
     '(Cardiovascular Diseases[MeSH Terms] OR cardiovascular[tiab])'),
    ("⑤ 限 RCT",
     '((Metformin[MeSH Terms] OR metformin[tiab]) AND '
     '(Cardiovascular Diseases[MeSH Terms] OR cardiovascular[tiab])) '
     'AND randomized controlled trial[pt]'),
    ("⑥ 限近五年（会切掉经典）",
     '((Metformin[MeSH Terms] OR metformin[tiab]) AND '
     '(Cardiovascular Diseases[MeSH Terms] OR cardiovascular[tiab])) '
     'AND randomized controlled trial[pt] AND 2021:2026[dp]'),
]

# 要核验并写进书里的经典文献（手工填，脚本负责查证是否存在）
CHECK_TERMS = ['UKPDS 34[ti]']

UDE = {"User-Agent": "Mozilla/5.0 (textbook-research)"}


def _get(url):
    req = urllib.request.Request(url, headers=UDE)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def esearch(term, retmax=5):
    u = (f"{BASE}/esearch.fcgi?db=pubmed&retmode=json&retmax={retmax}"
         f"&term={urllib.parse.quote(term)}")
    d = _get(u)["esearchresult"]
    return d.get("count"), d.get("idlist", [])


def esummary(pmid):
    u = f"{BASE}/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    r = _get(u)["result"][pmid]
    doi = next((a["value"] for a in r.get("articleids", []) if a["idtype"] == "doi"), "")
    return {"pmid": pmid, "title": r.get("title", ""),
            "journal": r.get("fulljournalname") or r.get("source", ""),
            "date": r.get("pubdate", ""), "doi": doi}


if __name__ == "__main__":
    today = date.today().isoformat()
    print(f"检索日期：{today}（教材引用必须标这个日期，命中数会随数据库更新而变）\n")
    rows = []
    for label, term in STEPS:
        cnt, ids = esearch(term)
        cnt = int(cnt or 0)
        rows.append({"step": label, "term": term, "count": cnt})
        print(f"{label:24} {cnt:>10,} 条   示例 PMID: {', '.join(ids[:3])}")

    print("\n=== 经典文献核验 ===")
    for term in CHECK_TERMS:
        cnt, ids = esearch(term)
        print(f"{term} → {cnt} 条")
        if ids:
            info = esummary(ids[0])
            print(f"  {info['title'][:100]}\n  {info['journal']} | {info['date']} | "
                  f"PMID {info['pmid']} | DOI {info['doi'] or '(旧文献常无 DOI)'}")
            rows.append({"check": term, **info})

    out = {"verified_at": today, "steps": rows,
           "note": "命中数会随 PubMed 更新变化；教材正文需标注检索日期"}
    with open("case_ladder.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n已存 case_ladder.json")
