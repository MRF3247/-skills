#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新闻页 P2/P3 截图：1080×1440（3:4），cookie/赞助位清理、催懒加载、整句/整段高亮、重复自动去重。

用法:
  python3 shot_p2p3.py --url <URL> --slug <短名> --anchor "1,338 cases" \
      [--mark-mode sentence|para|none] [--only p2|p3|both] [--mark-in p2|p3|both]

高亮口径（用户口径，别改回「只标数字」）：
  * sentence = 把含关键数字的**整句**涂上黄条
  * para     = 把整段涂上黄条
  * none     = 不涂（P2 默认 none；P3 默认 para）

去重：P3 要截的段落如果已经完整出现在 P2 的裁切范围内，直接跳过 P3，只输出 P2
（用户原话：「p2 和 p3 的内容重复时，只保留 p2」）。

输出 /tmp/shots/<slug>-p2.png / -p3.png，stdout 打 JSON。
需要 camofox 在 :9377（GET /health）。
"""
import json, os, time, urllib.request, argparse
from PIL import Image
import numpy as np

B = "http://127.0.0.1:9377"
UID = "hermes-card"
OUT = "/tmp/shots"
VW, VH = 1200, 1600

HIDE = """
{HEADER_PART}
[role=banner], [role=navigation],
[class*=cookie], [class*=consent], [id*=onetrust], [class*=gdpr],
[class*=advert], [class*=ad-slot], [id*=google_ads], [class*=adsbygoogle],
[class*=newsletter], [class*=modal], [class*=overlay], [class*=share],
[class*=social], [class*=skip-link], [class*=comments],
[class*=usa-banner], [id*=usa-banner], [class*=rss], [id*=rss],
[class*=error], [class*=alert], [role=alert], [class*=sidebar],
[class*=article-actions], [class*=full-text-links], [class*=citation-actions],
[class*=search-bar], [class*=nav-menu], [class*=results-actions],
[class*=search-form], #search-form, [class*=navbar], [class*=top-bar]
{display:none !important;}
img {max-width:100% !important; height:auto !important;}
* {animation:none !important; transition:none !important;}
mark.hlmark {background: rgba(255,235,59,0.55) !important; color:#000 !important;
  padding:1px 2px; border-radius:2px;}
"""

CLEAN_JS = r"""(()=>{let n=0;
  document.querySelectorAll('div,section,aside,figure').forEach(e=>{
    const t=(e.textContent||'').trim();
    if(t && t.length<200 && /sponsor message|become an npr sponsor|advertisement/i.test(t)){
      const box=e.closest('aside,div,section')||e.parentElement;
      if(box){box.remove();n++;}
    }
  });
  document.querySelectorAll('img').forEach(i=>{
    i.loading='eager';
    const ds=i.getAttribute('data-src')||i.getAttribute('data-lazy-src');
    if(ds && (!i.src || i.src.startsWith('data:'))) i.src=ds;
  });
  return n;})()"""

DEAD_IMG_JS = r"""(()=>{let n=0;
  document.querySelectorAll('img').forEach(i=>{
    if(i.complete && i.naturalWidth===0){
      const box=i.closest('figure,div')||i;
      box.style.display='none'; n++;
    }
  });
  return n;})()"""

# 只改文本节点，避免正则把 href / data-* 里的数字一起替换（会撕出裸代码）
MARK_JS = r"""(()=>{const anchor=%s, mode=%s;
  const ps=Array.from(document.querySelectorAll('p'));
  const el=ps.find(p=>(p.textContent||'').includes(anchor));
  if(!el) return 'no-anchor';
  const markNode=(node)=>{const m=document.createElement('mark');m.className='hlmark';
    node.parentNode.insertBefore(m,node);m.appendChild(node);};
  if(mode==='para'){
    // 整段高亮：包一层 inline span 刷背景，不能用 mark 包块级元素（会变成两条竖线）
    const span=document.createElement('span');
    span.className='hlmark-span';
    span.style.cssText='background:rgba(255,235,59,0.55);border-radius:2px;';
    while(el.firstChild) span.appendChild(el.firstChild);
    el.appendChild(span);
    return 'para';
  }
  const walker=document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const nodes=[]; let n; while(n=walker.nextNode()) nodes.push(n);
  let buf=[], cnt=0;
  const flush=()=>{ if(!buf.length) return; const joined=buf.map(x=>x.nodeValue).join('');
    if(/[0-9]/.test(joined)){ buf.forEach(markNode); cnt++; } buf=[]; };
  nodes.forEach(t=>{ if(/[.．!？?!]\s*$/.test(t.nodeValue)){ buf.push(t); flush(); }
    else if(/[0-9]/.test(t.nodeValue)||buf.length){ buf.push(t); } });
  flush();
  return cnt;})()"""


def post(path, body, timeout=180):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def ev(tid, expr):
    try:
        return post(f"/tabs/{tid}/evaluate", {"userId": UID, "expression": expr}).get("result")
    except Exception as ex:
        return "ERR:" + str(ex)[:80]


def close(tid):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{B}/tabs/{tid}?userId={UID}", method="DELETE"), timeout=10)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--anchor", default=None, help="关键结果段里独有的短句（用于定位 P3 段）")
    ap.add_argument("--mark-mode", default="sentence", choices=["sentence", "para", "none"])
    ap.add_argument("--only", default="both", choices=["p2", "p3", "both"])
    ap.add_argument("--mark-in", default="p3", choices=["p2", "p3", "both"])
    ap.add_argument("--keep-header", action="store_true", help="保留 <header>/<nav>/<footer>（PubMed 等把标题作者放在 header 里的站必须开）")
    ap.add_argument("--masthead", default="", help="截图顶部追加一行出处（站点·PMID·期刊·日期），补页面本身缺失的题录")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    tid = post("/tabs", {"userId": UID, "sessionKey": "p2p3"})["tabId"]
    res = {"slug": a.slug}
    try:
        for _ in range(3):
            r = post(f"/tabs/{tid}/navigate", {"userId": UID, "url": a.url})
            if (r.get("httpStatus") or 500) < 400:
                break
            time.sleep(4)
        res["http"] = r.get("httpStatus")
        time.sleep(5)
        ev(tid, "document.querySelectorAll('video').forEach(v=>{v.muted=true;v.pause()})")
        ev(tid, r"""(()=>{let n=0;
          document.querySelectorAll('button,a').forEach(b=>{
            const t=((b.getAttribute('aria-label')||'')+' '+(b.textContent||'')).trim();
            if(/close|dismiss|accept all|got it|no thanks/i.test(t)){try{b.click();n++;}catch(e){}}});
          return n;})()""")
        hide_css = HIDE.replace("{HEADER_PART}", "" if a.keep_header else "header, nav, footer,")
        ev(tid, "(()=>{const s=document.createElement('style');s.textContent=%s;document.head.appendChild(s);return 1;})()" % json.dumps(hide_css))
        post(f"/tabs/{tid}/viewport", {"userId": UID, "width": VW, "height": VH})
        ev(tid, r"""(()=>{let y=0;const t=setInterval(()=>{window.scrollBy(0,800);y+=800;
          if(y>document.body.scrollHeight+1600){clearInterval(t);window.scrollTo(0,0);}},60);return 1;})()""")
        time.sleep(9)
        res["clean"] = ev(tid, CLEAN_JS)
        time.sleep(2)
        res["deadimg"] = ev(tid, DEAD_IMG_JS)
        if a.masthead:
            ev(tid, """(()=>{const d=document.createElement('div');
              d.textContent=%s;
              d.style.cssText='font:13px/1.7 -apple-system,Helvetica,Arial,sans-serif;color:#888;padding:10px 0 4px';
              document.body.insertBefore(d, document.body.firstChild);return 1;})()""" % json.dumps(a.masthead))

        # P3 段落的纵向位置（先量，用于去重判断与裁切）
        y_para = None
        if a.anchor:
            y_para = ev(tid, r"""(()=>{const anchor=%s;
              const el=Array.from(document.querySelectorAll('p')).find(p=>(p.textContent||'').includes(anchor));
              if(!el) return null; const b=el.getBoundingClientRect();
              return Math.round(b.top+window.scrollY);})()""" % json.dumps(a.anchor))
            res["y_para"] = y_para

        if a.mark_mode != "none" and a.anchor:
            do_mark = (a.mark_in == "both") or (a.mark_in == "p2" and a.only == "p2") or (a.mark_in == "p3" and a.only != "p2")
            if do_mark:
                res["mark"] = ev(tid, MARK_JS % (json.dumps(a.anchor), json.dumps(a.mark_mode)))

        res["box"] = ev(tid, r"""(()=>{const ps=Array.from(document.querySelectorAll('p')).filter(p=>(p.textContent||'').trim().length>40);
          if(!ps.length) return null;
          let l=1e9,r=0;ps.forEach(p=>{const b=p.getBoundingClientRect();l=Math.min(l,b.left);r=Math.max(r,b.right);});
          return JSON.stringify([Math.round(l),Math.round(r)]);})()""")
        res["vp"] = ev(tid, "[window.innerWidth, document.body.scrollHeight]")
        time.sleep(1.5)
        data = urllib.request.urlopen(f"{B}/tabs/{tid}/screenshot?userId={UID}&fullPage=true", timeout=300).read()
        full = os.path.join(OUT, a.slug + "-full.png")
        open(full, "wb").write(data)
        im = Image.open(full).convert("RGB")
        W, H = im.size
        res["full"] = [W, H]

        try:
            l, r_ = json.loads(res.get("box") or "[0, 0]")
        except Exception:
            l, r_ = 0, 0
        if not (r_ > l):
            l, r_ = 0, W
        x0, x1 = max(0, int(l) - 24), min(W, int(r_) + 24)
        cw = x1 - x0
        win_h = int(cw * 4 / 3)
        res["crop_x"] = [x0, x1, win_h]

        g = np.asarray(im.convert("L"))
        ink = np.where(g.min(axis=1) < 245)[0]
        top = int(ink[0]) if len(ink) else 0
        top = max(0, min(top, H - win_h))

        # 去重：P3 段落起点已在 P2 范围内 → 不出 P3
        dup = y_para is not None and top <= int(y_para) < top + win_h * 0.62
        res["p3_dup_of_p2"] = bool(dup)

        if a.only in ("both", "p2"):
            im.crop((x0, top, x1, top + win_h)).resize((1080, 1440), Image.LANCZOS).save(
                os.path.join(OUT, a.slug + "-p2.png"))
            res["p2"] = f"{OUT}/{a.slug}-p2.png"

        if a.only in ("both", "p3") and not dup and y_para is not None:
            scale = W / float((res.get("vp") or [VW, H])[0]) or 1.0
            y0 = int(y_para * scale)
            ytop = max(0, min(int(y0 - win_h * 0.16), H - win_h))
            im.crop((x0, ytop, x1, ytop + win_h)).resize((1080, 1440), Image.LANCZOS).save(
                os.path.join(OUT, a.slug + "-p3.png"))
            res["p3"] = f"{OUT}/{a.slug}-p3.png"
            res["y3"] = ytop
    finally:
        close(tid)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
