#!/usr/bin/env python3
"""医学资讯多源直抓（不依赖 MedHOT / 每日医讯中间层）。

三条腿：
  1) EuropePMC REST（按 ISSN 拉最新期刊论文 + 预印本）——覆盖期刊正文，最稳
  2) RSS/Atom（Nature/NEJM/Lancet/JAMA/Cell/Science/WHO/CDC/行业媒体，22 个源）——覆盖新闻与快报
     ⚠️ 预印本（bioRxiv/medRxiv）默认不抓：无同行评议、太前沿，不适合公号内容。`--with-preprint` 可临时恢复。
  3) 中文官方源（NMPA 药品公告/动态、卫健委政策法规/解读、国自然通知）——国内政策与获批，
     被 412/JS 挡的直接走 camofox

用法：
  python3 fetch_all_sources.py --days 3 --out /tmp/news.json
  python3 fetch_all_sources.py --days 7 --only jr --out /tmp/jr.json      # 只走 EuropePMC
  python3 fetch_all_sources.py --days 3 --only rss --out /tmp/rss.json    # 只走 RSS
  python3 fetch_all_sources.py --days 10 --only cn --out /tmp/cn.json     # 只走中文官方源
  python3 fetch_all_sources.py --days 3 --dept icu                        # 按科室过滤

输出：[{source, kind, title, doi, url, published, pub_basis, issue_date, abstract}]，按 published 降序，DOI/标题双重去重。
     published 为空但 issue_date 有值的，是期刊给的“未来期次日”——不能当发布日期，需进页面核。
"""
import argparse, html as htmlmod, json, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
TODAY = datetime.now().strftime("%Y-%m-%d")

# ── EuropePMC 期刊表：显示名 -> ISSN（MED = PubMed 收录，HAS_ABSTRACT 过滤掉读者来信/更正）
JOURNALS = {
    "NEJM": "0028-4793", "JAMA": "0098-7484", "JAMA Cardiology": "2380-6583",
    "JAMA Oncology": "2374-2437", "JAMA Internal Medicine": "2168-6106",
    "The Lancet": "0140-6736", "Lancet Oncology": "1470-2045", "Lancet Infectious Diseases": "1473-3099",
    "Lancet Neurology": "1474-4422", "Lancet Diabetes & Endocrinology": "2213-8587",
    "Lancet Global Health": "2214-109X", "Nature": "0028-0836", "Nature Medicine": "1078-8956",
    "Nature Biotechnology": "1087-0156", "Nature Reviews Cancer": "1474-175X", "Cell": "0092-8674",
    "BMJ": "0959-8138", "Annals of Internal Medicine": "0003-4819", "Circulation": "0009-7322",
    "JACC": "0735-1097", "European Heart Journal": "0195-668X",
    "Diabetes Care": "0149-5992", "Blood": "0006-4971",
    "Journal of Clinical Oncology": "0732-183X", "JAMA Surgery": "2168-6254", "Brain": "0006-8950",
    "Gut": "0017-5749", "Gastroenterology": "0016-5085", "Journal of Hepatology": "0168-8278",
    "Clinical Infectious Diseases": "1058-4838", "Intensive Care Medicine": "0342-4642",
    "Critical Care": "1466-609X", "Anesthesiology": "0003-3022", "Radiology": "0033-8419",
    "European Urology": "0302-2838", "Pediatrics": "0031-4005", "PLOS Medicine": "1549-1676",
    "Signal Transduction and Targeted Therapy": "2095-9907", "Chinese Medical Journal": "0366-6999",
    # 2026-10 补：填呼吸/急诊/麻醉/肾/精神/妇产的空白
    "Lancet Respiratory Medicine": "2213-2600", "Am J Respir Crit Care Med": "1073-449X",
    "Annals of Emergency Medicine": "0196-0644", "British Journal of Anaesthesia": "0007-0912",
    "JASN": "1046-6673", "JAMA Psychiatry": "2168-622X", "BJOG": "1470-0328",
    # 急诊/重症线（2026-10 补）：Ann Emerg Med 发文節奏慢（最新条目常在前 1-2 周），
    # 窗口设 3 天时抓不到是**正常**，不是空源；要急诊内容记得把 --days 放到 10 以上。
    "Academic Emergency Medicine": "1069-6563", "Resuscitation": "0300-9572",
    "Critical Care Medicine": "0090-3493", "Emergency Medicine Journal": "1472-0205",
    "Annals of Intensive Care": "2110-5820",
}

# ── RSS / Atom 源：显示名 -> (url, 类型)
FEEDS = {
    "Nature": ("https://www.nature.com/nature.rss", "rss"),
    "Nature Medicine": ("https://www.nature.com/nm.rss", "rss"),
    "Nature Biotechnology": ("https://www.nature.com/nbt.rss", "rss"),
    "Nature Reviews Cancer": ("https://www.nature.com/nrc.rss", "rss"),
    "NEJM": ("https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=nejm", "rss"),
    "NEJM Evidence": ("https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=evid", "rss"),
    "The Lancet": ("https://www.thelancet.com/rssfeed/lancet_current.xml", "rss"),
    "Lancet Oncology": ("https://www.thelancet.com/rssfeed/lanonc_current.xml", "rss"),
    "Lancet Infectious Diseases": ("https://www.thelancet.com/rssfeed/laninf_current.xml", "rss"),
    "JAMA": ("https://jamanetwork.com/rss/site_3/67.xml", "rss"),
    "Cell": ("https://www.cell.com/cell/current.rss", "rss"),
    "Science": ("https://www.science.org/rss/news_current.xml", "rss"),
    "WHO": ("https://www.who.int/rss-feeds/news-english.xml", "rss"),
    "CDC": ("https://tools.cdc.gov/api/v2/resources/media/316422.rss", "rss"),
    "STAT": ("https://www.statnews.com/feed/", "news"),
    "BioPharma Dive": ("https://www.biopharmadive.com/feeds/news/", "news"),
    "Endpoints News": ("https://endpts.com/feed/", "news"),
    "MedPage Today": ("https://www.medpagetoday.com/rss/headlines.xml", "news"),
    "ScienceDaily": ("https://www.sciencedaily.com/rss/health_medicine.xml", "news"),
    "NPR Health": ("https://feeds.npr.org/1128/rss.xml", "news"),
    "Healthcare Dive": ("https://www.healthcaredive.com/feeds/news/", "news"),
    "Health Affairs": ("https://www.healthaffairs.org/action/showFeed?type=etoc&feed=rss&jc=hlthaff", "journal"),
    # ── 传播向专用源（2026-10-28 加：用户实测情绪/吃瓜类流量最好）──
    "Retraction Watch": ("https://retractionwatch.com/feed/", "news"),
    # PubPeer 官方无 RSS（/rss /feed 全 404，实测 2026-10-28）——需要时用 camofox 抓 https://pubpeer.com/
}

# ── 预印本源：默认**不抓**（2026-10-26 用户决定）。
# 理由：预印本没有同行评议、结论常反转，太前沿，不适合做面向医生的公号内容。
# 需要临时恢复时加 --with-preprint，别改这里。
PREPRINT_FEEDS = {
    "bioRxiv": ("https://connect.biorxiv.org/biorxiv_xml.php?subject=all", "preprint"),
    "medRxiv": ("https://connect.medrxiv.org/medrxiv_xml.php?subject=all", "preprint"),
}

# 已知取不到（需浏览器兜底），脚本会跳过并提示
BLOCKED = {
    "Medscape": "Cloudflare 403，curl 拿不到 → 用 camofox 打开或走 MedPage/STAT 替代",
    "FDA 新闻稿": "原 RSS 路径已 404 → 改抓 https://www.fda.gov/news-events/fda-newsroom（需 camofox）或 openFDA API",
    "Guardian Health": "国内网络直连超时（000）→ 需要时走代理",
}

# ── 中文官方源（国内政策 / 获批 / 基金口径，英文源一条都覆盖不到）
# curl 直连成功率：NMPA 与卫健委列表页多为 412（WAF 要 cookie/JS），一律 curl 先试、失败落 camofox。
CN_SITES = {
    "NMPA药品公告": "https://www.nmpa.gov.cn/yaopin/ypggtg/index.html",
    "NMPA药品动态": "https://www.nmpa.gov.cn/yaopin/ypjgdt/index.html",
    "卫健委政策法规": "http://www.nhc.gov.cn/wjw/zcfg/list.shtml",
    "卫健委工作通知": "http://www.nhc.gov.cn/wjw/gztz/list.shtml",
    "卫健委征求意见": "http://www.nhc.gov.cn/wjw/zqyj/list.shtml",
    "国自然通知公告": "https://www.nsfc.gov.cn/p1/2828/2831/tzgg11.html",
}

# 中文源里明确不要的噪声：时政通稿、领导活动、纯导航
CN_DROP = ("习近平", "李强", "政治局", "新华社", "求是", "党中央", "常委会", "二十大", "全会",
           "会见", "率团", "调研", "座谈", "看望", "出席会议")

CAMOFOX = "http://127.0.0.1:9377"

DEPT_KW = {
    "cardio": ["heart", "cardiac", "cardio", "coronary", "arrhythm", "atrial", "stroke", "hypertens", "atheroscle", "心", "冠", "房颤", "心衰", "血压", "动脉"],
    "resp": ["lung", "pulmonary", "respirat", "copd", "asthma", "ventilat", "肺", "呼吸", "哮喘", "通气"],
    "icu": ["intensive care", "critical", "sepsis", "septic", "shock", "icu", "ventilat", "weaning", "脓毒", "重症", "休克", "撤机", "复苏"],
    "anes": ["anesthes", "anaesthes", "anesthe", "analges", "opioid", "pain", "sedation", "麻醉", "镇痛", "疼痛", "阿片"],
    "radio": ["radiolog", "imaging", "mri", "ct ", "pet/", "ultrasound", "mammograph", "影像", "放射", "超声", "造影"],
    "onc": ["cancer", "tumor", "tumour", "oncolog", "carcinoma", "lymphoma", "leukemia", "癌", "肿瘤", "淋巴"],
}


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read()


def fetch_epmc(name, issn, cutoff, page_size=50):
    q = f"ISSN:{issn} AND SRC:MED AND HAS_ABSTRACT:Y"
    url = (f"{EPMC}?query={urllib.parse.quote(q)}&format=json&pageSize={page_size}"
           f"&sort=FIRST_PDATE_D+desc&resultType=core")
    out = []
    try:
        d = json.loads(http_get(url).decode("utf-8", "ignore"))
    except Exception as e:
        print(f"  [EPMC FAIL] {name}: {e}", file=sys.stderr)
        return out
    for it in d.get("resultList", {}).get("result", []):
        # 优先电子版上线日；firstPublicationDate 对很多刊是“期次日期”，会出现未来日期（如 2027-09），
        # 直接用它排序会把排在未来的期次顶到最前。
        online = it.get("electronicPublicationDate") or ""
        first = it.get("firstPublicationDate") or ""
        pub = online or first
        basis = "online" if online else ("first" if first else "")
        # Lancet 系、部分 Elsevier 刊的“日期”实际是**未来期次日**（实测出过 2027-09）。
        # 超过今天的一律不当作发布日期：清空 published，原值落到 issue_date 供人工核。
        issue_date = ""
        if pub and pub > TODAY:
            issue_date, pub, basis = pub, "", "issue(future)"
        if pub and pub < cutoff:
            continue
        doi = it.get("doi") or ""
        out.append({
            "source": name, "kind": "journal",
            "title": (it.get("title") or "").rstrip("."),
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else (it.get("url") or ""),
            "published": pub,
            "pub_basis": basis,
            "issue_date": issue_date,
            "abstract": re.sub(r"<[^>]+>", " ", it.get("abstractText") or "")[:1200],
        })
    return out


def _local(tag):
    return tag.split("}")[-1].lower() if isinstance(tag, str) else ""

def fetch_feed(name, url, kind, cutoff):
    out = []
    try:
        raw = http_get(url, timeout=35)
    except Exception as e:
        print(f"  [RSS FAIL] {name}: {e}", file=sys.stderr)
        return out
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"  [RSS PARSE FAIL] {name}: {e}", file=sys.stderr)
        return out
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        rec = {}
        for ch in node:
            t = _local(ch.tag)
            if t == "title":
                rec["title"] = (ch.text or "").strip()
            elif t == "link":
                rec.setdefault("url", (ch.text or ch.attrib.get("href") or "").strip())
            elif t in ("pubdate", "published", "updated", "date"):
                rec.setdefault("date_raw", (ch.text or "").strip())
            elif t in ("description", "summary"):
                rec.setdefault("abstract", re.sub(r"<[^>]+>", " ", ch.text or "")[:1200])
            elif t in ("doi", "identifier"):
                v = (ch.text or "").strip()
                if v.lower().startswith("10."):
                    rec["doi"] = v
        if not rec.get("title"):
            continue
        pub = ""
        dr = rec.get("date_raw", "")
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                pub = datetime.strptime(dr.strip(), fmt).strftime("%Y-%m-%d")
                break
            except Exception:
                continue
        if pub and pub < cutoff:
            continue
        out.append({"source": name, "kind": kind, "title": rec["title"], "doi": rec.get("doi", ""),
                    "url": rec.get("url", ""), "published": pub, "abstract": rec.get("abstract", "")})
    return out


# ────────────────────────── 中文官方源 ──────────────────────────

def _cf(path, payload, timeout=90, method="POST"):
    """camofox REST 调用。POST /tabs 创建 tab 偶发 500（浏览器唤醒竞态），由调用方重试。"""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{CAMOFOX}{path}", data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())


def camofox_html(url, warm="https://www.nmpa.gov.cn/", wait=6, uid="hermes-scout"):
    """用 camofox 取真实渲染后的 outerHTML。

    实测坑：① 直接用目标 URL 建 tab，目标返回 412 时 camofox 直接 500 → 先用 warm 页建 tab 再 navigate；
    ② 建 tab 本身也会偶发 500 → 重试 3 次；③ 每条 URL 用完关 tab，否则 activeTabs 堆积后全部 400/500。
    """
    tab = None
    for attempt in range(3):
        try:
            tab = _cf("/tabs", {"url": warm, "userId": uid, "sessionKey": f"cn{attempt}"})["tabId"]
            break
        except Exception:
            time.sleep(3)
    if not tab:
        raise RuntimeError("camofox 建 tab 失败（检查 /health 的 browserRunning / activeTabs）")
    try:
        for _ in range(2):
            try:
                nav = _cf(f"/tabs/{tab}/navigate", {"userId": uid, "url": url})
                if nav.get("navigationOk"):
                    break
            except Exception:
                pass
            time.sleep(3)
        time.sleep(wait)
        r = _cf(f"/tabs/{tab}/evaluate",
                {"userId": uid, "expression": "document.documentElement.outerHTML"})
        res = r.get("result")
        return res if isinstance(res, str) else json.dumps(res)
    finally:
        try:
            _cf(f"/tabs/{tab}?userId={uid}", None, timeout=20, method="DELETE")
        except Exception:
            pass


def parse_cn(html_text, base):
    """从中文政府站列表页抽 (标题, 绝对链接, 日期)。

    政府站两种结构都覆盖：
      A. <li><a href title>标题</a><span class="ml">2026-09-22</span></li>   （NMPA / 卫健委）
      B. <a href><li>…<div class="item-right-content">标题</div>…<div class="date">2026-09-02</div></li></a>（国自然）
    做法：按「日期」定位，往前找最近的 <a>，标题优先取 title 属性、否则取 <a> 之后到日期之间的纯文本。
    """
    out, seen = [], set()
    for m in re.finditer(r"(20\d{2}-\d{2}-\d{2})", html_text):
        tail = html_text[max(0, m.start() - 1500):m.start()]
        am = None
        for am in re.finditer(r"<a\b[^>]*>", tail):
            pass
        if am is None:
            continue
        atag = am.group(0)
        hm = re.search(r'href="([^"]+)"', atag)
        if not hm or hm.group(1).startswith(("javascript:", "#")):
            continue
        tm = re.search(r'title="([^"]+)"', atag)
        if tm:
            title = htmlmod.unescape(tm.group(1)).strip()
        else:
            title = re.sub(r"<[^>]+>", " ", tail[am.end():])
            title = htmlmod.unescape(re.sub(r"\s+", " ", title)).strip()
        title = re.sub(r"\s+", " ", title)
        if len(title) < 8 or title in seen or any(k in title for k in CN_DROP):
            continue
        seen.add(title)
        out.append((title, urllib.parse.urljoin(base, hm.group(1)), m.group(1)))
    return out


def fetch_cn(name, url, cutoff):
    """中文源：curl 先试（快），非 200 或内容里没日期就落 camofox。"""
    out, html_text, engine = [], "", "curl"
    try:
        raw = http_get(url, timeout=25).decode("utf-8", "ignore")
        if len(raw) > 5000 and re.search(r"20\d{2}-\d{2}-\d{2}", raw):
            html_text = raw
    except Exception:
        pass
    if not html_text:
        engine = "camofox"
        try:
            html_text = camofox_html(url, warm=urllib.parse.urlsplit(url)._replace(path="/").geturl())
        except Exception as e:
            print(f"  [CN FAIL] {name}: camofox 也拿不到 {e}", file=sys.stderr)
            return out
    for title, link, pub in parse_cn(html_text, url):
        if pub < cutoff:
            continue
        out.append({"source": name, "kind": "cn_policy", "title": title, "doi": "",
                    "url": link, "published": pub, "pub_basis": engine, "issue_date": "",
                    "abstract": ""})
    if not out:
        print(f"  [CN EMPTY] {name}: 抓到页面但窗口内无条目（政府站节奏慢，试放大 --days）", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="回看天数（按今天往前推）")
    ap.add_argument("--only", choices=["all", "jr", "rss", "cn"], default="all")
    ap.add_argument("--with-preprint", action="store_true",
                    help="临时恢复抓 bioRxiv/medRxiv（默认排除：无同行评议，不适合公号内容）")
    ap.add_argument("--dept", choices=list(DEPT_KW), help="按科室关键词过滤（cardio/resp/icu/anes/radio/onc）")
    ap.add_argument("--out", default="/tmp/medical_news.json")
    args = ap.parse_args()

    cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    print(f"窗口 >= {cutoff}")

    jobs = []
    if args.only in ("all", "jr"):
        for name, issn in JOURNALS.items():
            jobs.append(("epmc", name, issn))
    if args.only in ("all", "rss"):
        for name, (url, kind) in FEEDS.items():
            jobs.append(("rss", name, url))
        if args.with_preprint:
            for name, (url, kind) in PREPRINT_FEEDS.items():
                jobs.append(("rss", name, url))

    results = []
    def work(job):
        typ, name, arg = job
        if typ == "epmc":
            return fetch_epmc(name, arg, cutoff)
        kind = (FEEDS.get(name) or PREPRINT_FEEDS.get(name) or (None, "news"))[1]
        return fetch_feed(name, arg, kind, cutoff)

    with ThreadPoolExecutor(max_workers=6) as ex:
        for chunk in ex.map(work, jobs):
            results.extend(chunk)

    # 中文源串行跑：camofox 并发多了会 400/500，且每条要等渲染
    if args.only in ("all", "cn"):
        for name, url in CN_SITES.items():
            print(f"  [CN] {name} …", file=sys.stderr)
            results.extend(fetch_cn(name, url, cutoff))
            time.sleep(2)

    # 去重：DOI 优先，无 DOI 用规范化标题
    seen, dedup = set(), []
    for r in results:
        key = r["doi"].lower() if r.get("doi") else re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", r["title"].lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    if args.dept:
        kws = [k.lower() for k in DEPT_KW[args.dept]]
        dedup = [r for r in dedup if any(k in (r["title"] + " " + r.get("abstract", "")).lower() for k in kws)]

    dedup.sort(key=lambda r: r.get("published", ""), reverse=True)
    with open(args.out, "w") as f:
        json.dump(dedup, f, ensure_ascii=False, indent=1)

    by_src = {}
    for r in dedup:
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    print(f"抓取 {len(dedup)} 条 → {args.out}")
    for k, v in sorted(by_src.items(), key=lambda x: -x[1]):
        print(f"  {k:32} {v}")
    if BLOCKED and args.only != "jr":
        print("\n需浏览器兜底的源（本脚本不抓）：")
        for k, v in BLOCKED.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
