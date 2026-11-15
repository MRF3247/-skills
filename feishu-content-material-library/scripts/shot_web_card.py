#!/usr/bin/env python3
"""Render a web page (via camofox, to get past bot walls) into 1080x1440 (3:4) cards.

P2 = top of page (title + date + lead), P3 = key-results paragraph with yellow marks.
Outputs /tmp/shots/<slug>-p2.png and -p3.png, prints JSON with http/marks/y2/y3.

Usage:
  python3 shot_web_card.py --url URL --slug SLUG --kw "63.1%,53.5%,1.30" \
      [--selector p] [--skip-p2] [--skip-p3]

Requires: camofox on :9377 (GET /health), PIL, numpy.
See references/p2-p3-web-card-screenshot.md for the decision table and pitfalls.
"""
import argparse, json, os, time, urllib.request
from PIL import Image
import numpy as np

B = "http://127.0.0.1:9377"
UID = "hermes-card"
OUT = "/tmp/shots"
VW, VH = 1200, 1600

HIDE_CSS = """
header, nav, footer, [role=banner], [role=navigation], [class*=site-header], [class*=global-nav],
[class*=cookie], [class*=consent], [class*=subscribe], [class*=newsletter-signup],
[class*=modal], [class*=overlay], [class*=popup], [class*=onesignal], [id*=onesignal],
[class*=advert], [id*=advert], [class*=ad-slot], [id*=google_ads], [class*=adsbygoogle],
[class*=related], [class*=recommend], [class*=share], [class*=social], [class*=toolbar],
[class*=breadcrumb], [class*=skip-link], [class*=trc_related], [class*=footer]
{display:none !important;}
mark.hlmark {background: rgba(255,235,59,0.55) !important; color:#000 !important;
  padding:2px 3px; border-radius:2px;}
img {max-width:100% !important; height:auto !important;}
*{animation:none !important; transition:none !important;}
"""
# NOTE: never match [class*=paywall] / [class*=sticky] / [class*=article-] here --
# publisher article containers carry those names and you will delete the article body.

# Unwrap internal scroll containers so the document actually grows.
FIX_JS = """(()=>{let n=0;document.querySelectorAll('div,section,main,article').forEach(e=>{
  if(e.scrollHeight>e.clientHeight+100){const cs=getComputedStyle(e);
    if(['hidden','auto','scroll'].includes(cs.overflowY)||['hidden','auto','scroll'].includes(cs.overflow)){
      e.style.setProperty('overflow','visible','important');
      e.style.setProperty('height','auto','important');
      e.style.setProperty('max-height','none','important');n++;}}});
  return n;})()"""

AD_RE = ("ADVERTISEMENT|CLICK HERE|Accept all|We use cookies|Continue without|"
         "send you notifications|Notifications can be turned|unlock more Medscape|"
         "Log in or register for free|接受所有 cookie|Accept Only Essential|Cookie 设置|"
         "我来说两句|24小时热文|推荐阅读|Dismiss")


def post(path, body, timeout=150):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def ev(tid, expr):
    try:
        return post(f"/tabs/{tid}/evaluate", {"userId": UID, "expression": expr}).get("result")
    except Exception as ex:
        return "ERR:" + str(ex)[:70]


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
    ap.add_argument("--kw", default="", help="comma separated numbers/words to mark")
    ap.add_argument("--selector", default="p", help="CSS selector for highlight targets")
    ap.add_argument("--skip-p2", action="store_true")
    ap.add_argument("--skip-p3", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    kws = [k.strip() for k in a.kw.split(",") if k.strip()]
    tid = post("/tabs", {"userId": UID, "sessionKey": "daily"})["tabId"]
    res = {"slug": a.slug}
    try:
        r = None
        for _ in range(3):
            try:
                r = post(f"/tabs/{tid}/navigate", {"userId": UID, "url": a.url}, timeout=150)
                if (r.get("httpStatus") or 500) < 400:
                    break
                time.sleep(4)
            except Exception:
                time.sleep(4)
        res["http"] = r.get("httpStatus") if isinstance(r, dict) else str(r)
        time.sleep(5)
        ev(tid, "document.querySelectorAll('video').forEach(v=>{v.muted=true;v.pause()})")
        ev(tid, "(()=>{const s=document.createElement('style');s.textContent=%s;document.head.appendChild(s);return 1;})()" % json.dumps(HIDE_CSS))
        post(f"/tabs/{tid}/viewport", {"userId": UID, "width": VW, "height": VH})
        time.sleep(2)
        res["removed"] = ev(tid, """(()=>{let n=0;document.querySelectorAll('div,section,aside,iframe,dialog').forEach(e=>{
            const t=(e.textContent||'').trim();
            if(t.length<250 && /%s/i.test(t)){e.remove();n++;}});return n;})()""" % AD_RE)
        res["unwrapped"] = ev(tid, FIX_JS)
        time.sleep(1.5)
        if kws:
            res["hl"] = ev(tid, """(()=>{const kws=%s;let done=0;
              Array.from(document.querySelectorAll(%s)).forEach(function(el){
                if(done>=2) return; if(el.querySelector('mark.hlmark')) return;
                const t=el.textContent||''; if(t.length<30||t.length>1600) return;
                if(!kws.some(k=>t.toLowerCase().includes(k.toLowerCase()))) return;
                let h=el.innerHTML;
                kws.forEach(function(k){const re=new RegExp('('+k.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&')+')','gi');
                  h=h.replace(re,'<mark class="hlmark">$1</mark>');});
                el.innerHTML=h;done++;});
              return done;})()""" % (json.dumps(kws, ensure_ascii=False), json.dumps(a.selector)))
            res["marks"] = ev(tid, """(()=>{const m=Array.from(document.querySelectorAll('mark.hlmark'));
              return JSON.stringify(m.map(x=>({y:Math.round(x.getBoundingClientRect().top+window.scrollY),
              t:(x.textContent||'').slice(0,40)})));})()""")
            res["viewport"] = ev(tid, "[window.innerWidth, document.body.scrollHeight]")
        time.sleep(1)
        data = urllib.request.urlopen(
            f"{B}/tabs/{tid}/screenshot?userId={UID}&fullPage=true", timeout=300).read()
        full = os.path.join(OUT, a.slug + "-full.png")
        open(full, "wb").write(data)
        im = Image.open(full).convert("RGB")
        W, H = im.size
        res["full"] = [W, H]
        win_h = int(W * 4 / 3)
        g = np.asarray(im.convert("L"))
        ink = np.where(g.min(axis=1) < 245)[0]
        top = int(ink[0]) if len(ink) else 0
        top = max(0, min(top, H - win_h))
        if not a.skip_p2:
            im.crop((0, top, W, top + win_h)).resize((1080, 1440), Image.LANCZOS).save(
                os.path.join(OUT, a.slug + "-p2.png"))
            res["p2"] = f"{OUT}/{a.slug}-p2.png"
        if not a.skip_p3:
            try:
                marks = json.loads(res.get("marks") or "[]")
            except Exception:
                marks = []
            vpw = res.get("viewport") or [VW, H]
            scale = W / float(vpw[0]) if vpw and vpw[0] else 1.0
            if marks:
                y0 = int(min(m["y"] for m in marks) * scale)
                ytop = int(y0 - win_h * 0.30)
            else:
                arr = np.asarray(im)
                yellow = (arr[:, :, 0] > 240) & (arr[:, :, 1] > 225) & (arr[:, :, 2] < 190) & (arr[:, :, 2] > 110)
                rows = np.where(yellow.sum(axis=1) > 40)[0]
                ytop = int(rows[0] - win_h * 0.35) if len(rows) else int(H * 0.4)
                res["p3_by_pixels"] = True
            ytop = max(0, min(ytop, H - win_h))
            im.crop((0, ytop, W, ytop + win_h)).resize((1080, 1440), Image.LANCZOS).save(
                os.path.join(OUT, a.slug + "-p3.png"))
            res["p3"] = f"{OUT}/{a.slug}-p3.png"
            res["y3"] = ytop
    finally:
        close(tid)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
