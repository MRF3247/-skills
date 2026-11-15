#!/usr/bin/env python3
"""把一个站（本机生产 web）的页面抓成静态快照，供 GitHub Pages 等静态托管使用。

用法:
  # 有界（默认）：固定页 + 榜单/列表里挖到的详情页
  python3 snapshot.py --base http://127.0.0.1:3100 --prefix /medhot --out /tmp/site
  # 全量：sitemap 清单 + 列表分页里挖出全部条目页
  python3 snapshot.py --base http://127.0.0.1:3100 --prefix /medhot --out /tmp/site --sitemap --deep-all

做什么:
  1. 页面清单：sitemap（全量）/ 固定页 + 挖详情页（有界）；--deep-all 再顺着 /all 的分页把全部条目页挖出来
  2. 下载页面引用的本站资源（/assets、/og、图标、/api/img-proxy 签名图片）—— 签名图会过期，必须落地成本地文件
  3. 根绝对路径改写成子路径（/medhot/...）；查询型 URL 映射成目录（/all?page=3 → /all/p3/）
  4. 输出 index.html / <route>/index.html；sitemap.xml、robots.txt 里的域名换成托管地址

推之前务必本地验：把产物放进以 prefix 命名的父目录，再 python3 -m http.server 打开。
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, hashlib, json, os, re, sys, time, urllib.parse, urllib.request

UA = "Site-Snapshot/1.0"

def get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.status, dict(r.headers)

def norm(u: str) -> str:
    """HTML 属性里是 &amp;、SSR 载荷里是 \\u0026，查资源表前都要还原成 &。"""
    return u.replace("\\u0026", "&").replace("&amp;", "&").replace("&quot;", '"')

# 匹配「站内绝对路径」，尾巴上可能跟一串 JSON 转义反斜杠（SSR 载荷里）。
# ⚠️ 字符类必须排除 <> ：否则自闭合标签的 "/>" 会被当成路径 "/>" 再前置一层前缀，
# 变成 "/medhot/>" 塞满整站（head 里看不见，body 里会变成可见的垃圾文本）。
URL_RE = re.compile(r'(["\'(])(/(?!/)[^"\')\s<>]*?)(\\*)(?=["\')\s<]|$)')

def iter_refs(text: str):
    for m in URL_RE.finditer(text):
        yield m.group(1), norm(m.group(2)), m.group(3)

def ext_of(src: str) -> str:
    ext = os.path.splitext(urllib.parse.urlsplit(src).path)[1].lower()
    return ext if ext in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico") else ".png"

SKIP_PREFIX = ("/admin", "/api/", "/starred", "/feedback", "/settings", "/auth")

def route_out(route: str) -> str:
    """路由（可带 query）→ 静态站上的路径（以 / 开头、以 / 结尾）。
    /all?page=3 → /all/p3/ ；/all?category=x → /all/c/x/ ；/?category=x → /c/x/"""
    sp = urllib.parse.urlsplit(route)
    q = urllib.parse.parse_qs(sp.query)
    p = sp.path.rstrip("/")
    if q.get("category"):
        c = q["category"][0]
        return f"{p}/c/{c}/" if p else f"/c/{c}/"
    if q.get("page"):
        n = q["page"][0]
        if n in ("1", "0"):
            return (p or "") + "/"
        return f"{p or ''}/p{n}/"
    return (p or "") + "/"

def route_to_path(route: str) -> str:
    r = route_out(route).strip("/")
    return "index.html" if not r else f"{r}/index.html"

def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="本地生产 web 地址，例如 http://127.0.0.1:3100")
    ap.add_argument("--prefix", required=True, help="静态托管的子路径，例如 /medhot")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sitemap", action="store_true", help="用 /sitemap.xml 做全量清单")
    ap.add_argument("--deep-all", action="store_true", help="顺着列表页分页把全部条目页挖出来")
    ap.add_argument("--max-list-pages", type=int, default=80, help="--deep-all 时最多翻多少页列表")
    ap.add_argument("--max-pages", type=int, default=4000, help="总页数上限（防跑飞）")
    ap.add_argument("--max-stories", type=int, default=40)
    ap.add_argument("--max-items", type=int, default=25)
    ap.add_argument("--max-dailies", type=int, default=6)
    ap.add_argument("--routes", default="/,/hot,/daily,/all,/topics,/preprints,/agent,/about,/changelog")
    ap.add_argument("--pages-url", default="")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()

    base = a.base.rstrip("/")
    prefix = "/" + a.prefix.strip("/")
    pages_url = (a.pages_url or "https://mrf3247.github.io" + prefix).rstrip("/")

    def fetch(route: str):
        try:
            body, _, hdrs = get(base + route)
            return route, body.decode("utf-8", "replace"), hdrs
        except Exception as e:
            return route, None, {"error": str(e)}

    # ---- 1. 页面清单 ----
    fixed: list[str] = [r for r in a.routes.split(",") if r]
    sitemap_xml: str | None = None
    if a.sitemap:
        try:
            sitemap_xml = get(base + "/sitemap.xml")[0].decode("utf-8", "replace")
            paths = []
            for u in re.findall(r"<loc>([^<]+)</loc>", sitemap_xml):
                p = re.sub(r"^https?://[^/]+", "", u.strip()) or "/"
                if any(p.startswith(s) for s in SKIP_PREFIX):
                    continue
                paths.append(p if p.startswith("/") else "/" + p)
            fixed = sorted(set(paths) | set(fixed))
            print(f"  sitemap 清单 → 去重后 {len(fixed)} 个页面")
        except Exception as e:
            print(f"  ✗ 取 sitemap 失败（{e}），退回有界模式")

    pages: dict[str, str] = {}
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for route, html, hdrs in ex.map(fetch, fixed):
            if html is None:
                print(f"  ✗ {route}: {hdrs.get('error')}")
            else:
                pages[route] = html
    print(f"  清单页 {len(pages)} 个（{time.time()-t0:.0f}s）")

    def harvest_items(html: str) -> set[str]:
        return set(re.findall(r'href="(/items/[a-z0-9]{16,40})"', html)) | \
               set(re.findall(r'href="(/story/[0-9a-f-]{36})"', html))

    # ---- 2. 挖详情页 ----
    if a.deep_all:
        listing = pages.get("/all", "")
        m = re.search(r'pageCount\\?",\s*(\d+)', listing)
        page_count = min(int(m.group(1)) if m else 1, a.max_list_pages)
        print(f"  列表共 {page_count} 页，开始翻页挖条目…")
        extra_routes = [f"/all?page={n}" for n in range(2, page_count + 1)]
        extra_routes += [r for r in ("/all?category=research", "/all?category=clinical", "/all?category=industry",
                                     "/all?category=policy", "/all?category=public-health", "/all?category=opinion",
                                     "/all?category=explainer", "/all?channel=firstParty")]
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for route, html, hdrs in ex.map(fetch, extra_routes):
                if html is None:
                    print(f"  ✗ {route}: {hdrs.get('error')}")
                else:
                    pages[route] = html
        print(f"  列表页合计 {len([r for r in pages if r.startswith('/all')])} 个（{time.time()-t0:.0f}s）")

    detail = set()
    for html in pages.values():
        detail |= harvest_items(html)
    detail = {d for d in detail if d not in pages}
    detail = sorted(detail)[: max(0, a.max_pages - len(pages))]
    print(f"  待抓详情页 {len(detail)} 个")
    if detail:
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for route, html, hdrs in ex.map(fetch, detail):
                if html is None:
                    print(f"  ✗ {route}: {hdrs.get('error')}")
                else:
                    pages[route] = html
    print(f"  合计 {len(pages)} 个页面（{time.time()-t0:.0f}s）")

    if not pages:
        print("一个页面都没抓到：检查本地生产 web 是否在跑"); return 1

    # ---- 3. 收集资源 ----
    assets: dict[str, str] = {}
    def want(u: str) -> str | None:
        u = norm(u)
        if u.startswith("/assets/"):
            return u.lstrip("/")
        if u.startswith("/api/img-proxy"):
            # 用「原图 URL」而不是整条签名 URL 命名：签名每次渲染都变，按签名命名会导致
            # 每次快照都换一批文件名（页面引用与已下载文件对不上 → 图全裂）。
            src = urllib.parse.parse_qs(urllib.parse.urlsplit(u).query).get("u", [""])[0] or u
            return "avatars/" + hashlib.sha1(src.encode()).hexdigest()[:16] + ext_of(src)
        if u.startswith("/og/") or u in ("/favicon.ico", "/apple-icon.png", "/icon.png", "/icon.svg",
                                         "/manifest.webmanifest", "/sitemap.xml"):
            return u.lstrip("/")
        return None

    for html in pages.values():
        for _, u, _esc in iter_refs(html):
            sp = urllib.parse.urlsplit(u)
            dst = want(sp.path + (("?" + sp.query) if sp.query else ""))
            if dst:
                assets[u] = dst
        for m in re.finditer(re.escape(pages_url) + r'(/[^"\')\s\\]*)', html):
            p = m.group(1)
            if p.startswith("/assets/") or p.startswith("/og/") or "." in os.path.basename(p):
                d = want(p)
                if d:
                    assets[p] = d
    for u in list(assets):
        if u.endswith(".css"):
            try:
                css = get(base + u)[0].decode("utf-8", "replace")
            except Exception:
                continue
            for _, cu, _e in iter_refs(css):
                d2 = want(cu)
                if d2:
                    assets[cu] = d2

    ok = 0
    def dl(item):
        u, dst = item
        p = os.path.join(a.out, dst)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        try:
            body, _, _ = get(base + u)
            open(p, "wb").write(body)
            return True, u, None
        except Exception as e:
            return False, u, str(e)
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for good, u, err in ex.map(dl, list(assets.items())):
            if good:
                ok += 1
            else:
                print(f"  ✗ 资源 {u}: {err}")
    print(f"  资源 {ok}/{len(assets)} 下载成功（{time.time()-t0:.0f}s）")

    for extra in ("/favicon.ico", "/apple-icon.png", "/manifest.webmanifest"):
        if extra in assets:
            continue
        try:
            body, code, _ = get(base + extra)
            if code == 200 and body:
                p = os.path.join(a.out, extra.lstrip("/"))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "wb").write(body)
        except Exception:
            pass

    # ---- 4. 改写 + 落盘 ----
    routes_norm = {r.rstrip("/") for r in pages if r != "/"}
    def rewrite(u: str) -> str:
        u = norm(u)   # 不归一化会查不到已下载的文件（属性 &amp; vs 载荷 \u0026）
        sp = urllib.parse.urlsplit(u)
        path, query = sp.path, sp.query
        if path.startswith("/api/img-proxy"):
            return prefix + "/" + assets.get(u, want(u) or "avatars/missing.png")
        if path.startswith("/assets/") or path.startswith("/og/") or "." in os.path.basename(path):
            return prefix + path + (("?" + query) if query else "")
        if u in pages:                       # 抓过的查询型 URL（/all?page=3、/all?category=x）
            return prefix + route_out(u)
        if u.rstrip("/") in routes_norm:
            return prefix + route_out(path) + (("?" + query) if query else "")
        if path == "/" and query:            # /?category=x 这类首页筛选
            return prefix + route_out(u)
        return prefix + path + (("?" + query) if query else "")

    def sub(text: str) -> str:
        return URL_RE.sub(lambda m: m.group(1) + rewrite(m.group(2)) + m.group(3), text)

    for route, html in pages.items():
        p = os.path.join(a.out, route_to_path(route))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(sub(html))
    for u, dst in assets.items():
        if not dst.endswith(".css"):
            continue
        p = os.path.join(a.out, dst)
        try:
            css = open(p, encoding="utf-8").read()
        except Exception:
            continue
        css2 = sub(css)
        if css2 != css:
            open(p, "w", encoding="utf-8").write(css2)

    if sitemap_xml:
        sm = re.sub(r"https?://[^/\"'<>]+", pages_url, sitemap_xml)
        sm = URL_RE.sub(lambda m: m.group(1) + rewrite(m.group(2)) + m.group(3), sm)
        open(os.path.join(a.out, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    try:
        rb, code, _ = get(base + "/robots.txt")
        if code == 200 and rb:
            rtxt = re.sub(r"https?://[^/\s]+", pages_url, rb.decode("utf-8", "replace"))
            rtxt = URL_RE.sub(lambda m: m.group(1) + rewrite(m.group(2)) + m.group(3), rtxt)
            open(os.path.join(a.out, "robots.txt"), "w", encoding="utf-8").write(rtxt)
    except Exception:
        pass

    bad_api = 0
    for route in pages:
        t = open(os.path.join(a.out, route_to_path(route)), encoding="utf-8").read()
        bad_api += len(re.findall(r'"/api/', t))
    open(os.path.join(a.out, ".nojekyll"), "w").close()
    json.dump({"pages": sorted(pages), "count": len(pages), "assets": len(assets), "prefix": prefix,
               "leftover_api_refs": bad_api, "seconds": round(time.time() - t0, 1)},
              open(os.path.join(a.out, "snapshot.json"), "w"), ensure_ascii=False, indent=1)
    print(f"✅ 快照完成：{len(pages)} 页 / {ok} 资源 → {a.out}（残留 /api 引用 {bad_api} 处，用时 {time.time()-t0:.0f}s）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
