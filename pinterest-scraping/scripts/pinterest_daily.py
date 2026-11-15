#!/usr/bin/env python3
"""Pinterest 医学/医疗主题图片每日搜集脚本
用法: pinterest_daily.py [--keywords "k1,k2,..."] [--max-per-keyword N] [--force]
输出: /Users/Jin/Documents/Hermes/Pinterest素材/YYYY-MM-DD/  (图片 + 清单.md)
健壮性: 时间戳日志 / 单张失败隔离 / 断点续传(已完成跳过) / 原子写 / 图片下载超时兜底
关键: channel="chrome" 用系统 Chrome 过 Pinterest 风控(headless shell 会被登录墙截断)
"""
import argparse, asyncio, json, os, re, urllib.request
from datetime import datetime

BASE_DIR = "/Users/Jin/Documents/Hermes/Pinterest素材"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

DEFAULT_KEYWORDS = [
    "medical research poster",
    "medical illustration",
    "scientific paper infographic",
    "medical infographic",
    "research poster design",
    "anatomy art",
    "medical aesthetic",
    "health infographic",
    "lab aesthetic",
    "clinical research",
    "biology notes aesthetic",
    "doctor aesthetic",
]

def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def http_get_bytes(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

async def search_pins(page, keyword, max_pins):
    """搜索关键词，返回 [{pin_url, img, alt}]"""
    url = f"https://www.pinterest.com/search/pins/?q={keyword.replace(' ', '%20')}"
    await page.goto(url, timeout=45000, wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)
    # 一个选择器同时取 pin 链接 + 卡片内 img + alt，避免与非 pin 图片(logo等)索引错位
    pins = await page.eval_on_selector_all(
        "a[href*='/pin/']",
        "els => els.map(a => { const img = a.querySelector('img'); "
        "return {href: a.href, src: img ? img.src : '', alt: img ? img.alt : ''}; })"
    )
    seen, out = set(), []
    for pin in pins:
        m = re.search(r"/pin/(\d+)/", pin.get("href", ""))
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        item = {"pin_url": f"https://www.pinterest.com/pin/{m.group(1)}/", "alt": pin.get("alt", "")}
        if pin.get("src", "").startswith("http") and "i.pinimg.com" in pin.get("src", ""):
            item["img"] = pin["src"]
        out.append(item)
        if len(out) >= max_pins:
            break
    return [o for o in out if o.get("img")]

def dedupe(items):
    seen, out = set(), []
    for it in items:
        h = re.search(r"/(\w+)/(\w\w)/(\w\w)/([0-9a-f]+)\.", it["img"])
        key = h.group(4) if h else it["img"]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", default=None)
    ap.add_argument("--max-per-keyword", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else DEFAULT_KEYWORDS

    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(BASE_DIR, today)
    os.makedirs(out_dir, exist_ok=True)
    cache_path = os.path.join(out_dir, "cache.json")

    # 断点续传缓存
    cache = {}
    if os.path.exists(cache_path) and not args.force:
        try:
            cache = json.load(open(cache_path))
        except Exception:
            log("[缓存] 损坏，重建")

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome", args=[
            "--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = await browser.new_context(
            user_agent=UA, viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = await ctx.new_page()

        all_items, failed = [], []
        global_seen = set()  # 跨关键词去重(同一 pin 可能出现在多个关键词结果)
        for kw in keywords:
            kws = slug(kw)
            # 已完成的跳过（续传）
            done = [v for k, v in cache.items() if v.get("keyword") == kw]
            if len(done) >= args.max_per_keyword and not args.force:
                log(f"[跳过] {kw}: 已有 {len(done)} 张")
                for v in done:
                    if v["img"] not in global_seen:
                        global_seen.add(v["img"])
                        all_items.append(v)
                continue
            try:
                items = await search_pins(page, kw, args.max_per_keyword * 2)
            except Exception as e:
                log(f"[搜索失败] {kw}: {str(e)[:120]}")
                failed.append(kw)
                continue
            items = dedupe(items)[:args.max_per_keyword]
            log(f"[搜索] {kw}: 命中 {len(items)} 张")
            for it in items:
                h = re.search(r"/([0-9a-f]+)\.", it["img"])
                key = h.group(1) if h else slug(it["img"])
                if key in cache and not args.force:
                    if cache[key]["img"] not in global_seen:
                        global_seen.add(cache[key]["img"])
                        all_items.append(cache[key])
                    continue
                it["keyword"] = kw
                if it["img"] in global_seen:
                    continue
                global_seen.add(it["img"])
                # 下载原图(CDN 换尺寸段)，originals 403 时回退 736x
                data = None
                for size in ("originals", "736x"):
                    try:
                        url = it["img"].replace("60x60/", size + "/").replace("236x/", size + "/")
                        data = http_get_bytes(url, timeout=30)
                        break
                    except Exception as e:
                        log(f"[下载失败 {size}] {key}: {str(e)[:80]}")
                if data is None:
                    failed.append(kw)
                    continue
                fname = f"{slug(kw)}_{key[:8]}.jpg"
                fpath = os.path.join(out_dir, fname)
                tmp = fpath + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, fpath)  # 原子写
                it["file"] = fpath
                it["size_kb"] = len(data) // 1024
                cache[key] = it
                all_items.append(it)
                # 增量持久化
                tmpc = cache_path + ".tmp"
                with open(tmpc, "w") as f:
                    json.dump(cache, f, ensure_ascii=False)
                os.replace(tmpc, cache_path)
            # 每关键词之间停顿，降低被风控概率
            await page.wait_for_timeout(3000)
        await browser.close()

    # 写清单
    man = [f"# Pinterest 医学/医疗素材 {today}", "",
           f"- 关键词: {len(keywords)} 个 | 收集: {len(all_items)} 张 | 失败: {len(failed)}",
           f"- 快照时间: {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    for i, it in enumerate(all_items, 1):
        man.append(f"{i}. {it.get('file','?')}")
        man.append(f"   - 关键词: {it.get('keyword','?')}")
        man.append(f"   - Pin: {it['pin_url']}")
        if it.get("alt"):
            man.append(f"   - 描述: {it['alt'][:120]}")
    mp = os.path.join(out_dir, "清单.md")
    tmp = mp + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(man) + "\n")
    os.replace(tmp, mp)

    log(f"完成: {len(all_items)} 张 -> {out_dir}")
    if failed:
        log(f"失败关键词: {set(failed)}")

if __name__ == "__main__":
    asyncio.run(main())
