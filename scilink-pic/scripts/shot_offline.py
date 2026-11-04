#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线 P2 截图：curl 取 HTML → 清洗 + 整句/整段高亮 → 本地 Chrome headless 全页截图 → 裁 3:4。

用于 camofox 打不开、但 curl 能拿到 200 的站（例：gastro.org、部分出版社新闻页）。

用法:
  python3 shot_offline.py --url <页面> --slug pbc --anchor "Peroxisome proliferator" \
      [--mark-mode sentence|para|none] [--width 1200] [--height 4200]
输出 /tmp/shots/<slug>-offline-p2.png（1080×1440）
"""
import argparse, os, re, subprocess, sys, html as htmlmod
from PIL import Image

CHROME = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
OUT = "/tmp/shots"

INJECT = """
<style>
  header, nav, footer, aside, [role=banner], [role=navigation],
  [class*=cookie], [class*=consent], [class*=newsletter], [class*=subscribe],
  [class*=advert], [class*=ad-slot], [class*=social], [class*=share],
  [class*=related], [class*=modal], [class*=popup], [class*=breadcrumb],
  [class*=utility], [class*=site-footer], [class*=skip], #footer, #header, #nav,
a[href='#content'], a[href='#main'] {display:none !important;}
  body {background:#fff !important; margin:0 auto !important; max-width:820px !important;
        padding:24px 28px !important; font-family:Georgia,'Times New Roman',serif !important;}
  h1 {font-size:34px !important; line-height:1.25 !important; margin:6px 0 10px !important;}
  .hl-date {font:14px/1.6 -apple-system,Helvetica,Arial,sans-serif; color:#666; margin-bottom:14px;}
  p, li {font-size:19px !important; line-height:1.62 !important; color:#111 !important;}
  img {max-width:100% !important; height:auto !important;}
  .hlmark, .hlmark-span {background:rgba(255,235,59,.55) !important;}
</style>
<script>
(function(){
  var anchor = __ANCHOR__, mode = "__MODE__";
  if (!anchor || mode === 'none') return;
  var blocks = Array.prototype.slice.call(document.querySelectorAll('p,li'));
  var el = blocks.find(function(b){ return (b.textContent||'').indexOf(anchor) >= 0; });
  if (!el) return;
  if (mode === 'para') {
    var span = document.createElement('span');
    span.className = 'hlmark-span';
    while (el.firstChild) span.appendChild(el.firstChild);
    el.appendChild(span);
    return;
  }
  var re = /[^.．!？?!]+[.．!？?!]/g, txt = el.textContent, out = '', last = 0, m;
  while ((m = re.exec(txt)) !== null) {
    var seg = m[0];
    out += htmlEscape(txt.slice(last, m.index));
    out += /[0-9]/.test(seg) ? '<mark class="hlmark">' + htmlEscape(seg) + '</mark>' : htmlEscape(seg);
    last = m.index + seg.length;
  }
  out += htmlEscape(txt.slice(last));
  el.innerHTML = out;
  function htmlEscape(s){ return s.replace(/[&<>]/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
})();
</script>
"""



def mark_in_html(doc, anchor, mode):
    """Python 侧打点：不依赖浏览器 JS（内联脚本在 headless 里可能不执行）。

    同一个 anchor 在页面里常出现多次（导航/推荐位/正文），取「正文文本最长」的那个块：
    导航里的短条目先命中会让高亮落到被隐藏的区域，等于白打。
    """
    if not anchor or mode == "none":
        return doc, 0
    best = None
    for tag in ("li", "p"):
        for mo in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", doc, flags=re.S | re.I):
            body = mo.group(1)
            plain = re.sub(r"<[^>]+>", "", body)
            if anchor not in plain:
                continue
            if best is None or len(plain) > best[0]:
                best = (len(plain), mo, body, plain)
    if best is None:
        return doc, 0
    _, mo, body, plain = best
    if mode == "para":
        # 若命中项在列表里，扩到整个 <ul>/<ol>（六条推荐要一起亮，只亮一条像随手点的）
        head = doc.rfind("<ul", 0, mo.start())
        head2 = doc.rfind("<ol", 0, mo.start())
        head = max(head, head2)
        if head >= 0:
            tag_l = "ul" if doc[head:head + 3] == "<ul" else "ol"
            tail = doc.find(f"</{tag_l}>", mo.end())
            if tail >= 0 and tail - head < 12000:
                seg = doc[head:tail + 4]
                seg = seg.replace(f"<{tag_l}", f'<{tag_l} style="background:rgba(255,235,59,.45)"', 1)
                return doc[:head] + seg + doc[tail + 4:], 1
        new = f'<span class="hlmark-span" style="background:rgba(255,235,59,.55)">{body}</span>'
    else:
        parts = re.split(r"(?<=[.!?．。！？])\s+", plain)
        new = " ".join(
            f'<mark class="hlmark">{htmlmod.escape(pt)}</mark>' if re.search(r"\d", pt)
            else htmlmod.escape(pt)
            for pt in parts if pt.strip())
    return doc[:mo.start(1)] + new + doc[mo.end(1):], 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--anchor", default="")
    ap.add_argument("--mark-mode", default="none", choices=["none", "sentence", "para"])
    ap.add_argument("--masthead", default="")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=4200)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    raw = subprocess.run(["curl", "-sL", "-m", "40", "-A",
                          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126 Safari/537.36", a.url],
                         capture_output=True, text=True).stdout
    if len(raw) < 5000:
        sys.exit(f"HTML 太短，可能被拦：{len(raw)} 字节")

    # 断掉外部资源，保证本地渲染不等待网络（图一律不要，外链 CSS/JS 全删）
    doc = re.sub(r"<script\b[^>]*>.*?</script>", "", raw, flags=re.S | re.I)
    doc = re.sub(r"<script\b[^>]*/?>", "", doc, flags=re.I)
    doc = re.sub(r"<link\b[^>]*>", "", doc, flags=re.I)
    doc = re.sub(r"<img\b[^>]*>", "", doc, flags=re.I)
    doc = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", doc, flags=re.S | re.I)
    doc = re.sub(r"<style\b[^>]*>(?:(?!</style>).)*?(font-face|@import)(?:(?!</style>).)*?</style>",
                 "", doc, flags=re.S | re.I)
    # 清完外链之后再注入样式与打点脚本（顺序反了会把注入的脚本一起删掉）
    style_part, _, script_part = INJECT.partition("<script>")
    script_part = "<script>" + script_part
    style_part = style_part.replace("__ANCHOR__", repr(a.anchor)).replace("__MODE__", a.mark_mode)
    script_part = script_part.replace("__ANCHOR__", repr(a.anchor)).replace("__MODE__", a.mark_mode)
    doc = doc.replace("</head>", style_part + "</head>", 1) if "</head>" in doc else style_part + doc
    # 脚本必须放在 body 末尾，放 head 里执行时 body 还没解析，querySelectorAll 是空的
    doc = doc.replace("</body>", script_part + "</body>", 1) if "</body>" in doc else doc + script_part
    # 顶部 masthead：站点名 + 域名 + 日期，补出处信息
    mast = (f'<div class="hl-date" style="font:13px/1.7 -apple-system,Helvetica,Arial,sans-serif;'
            f'color:#888;letter-spacing:.02em">{htmlmod.escape(a.masthead)}</div>')
    body_at = doc.find("<body")
    if body_at >= 0:
        gt = doc.find(">", body_at) + 1
        doc = doc[:gt] + mast + doc[gt:]
    doc, marked = mark_in_html(doc, a.anchor, a.mark_mode)
    print(f"python-side marked={marked}")
    local = os.path.join(OUT, f"{a.slug}-offline.html")
    open(local, "w").write(doc)

    shot = os.path.join(OUT, f"{a.slug}-offline-raw.png")
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--hide-scrollbars", "--disable-dev-shm-usage",
                    "--disable-features=Translate,BackForwardCache",
                    f"--window-size={a.width},{a.height}", f"--screenshot={shot}",
                    "--virtual-time-budget=4000", "--allow-file-access-from-files",
                    "file://" + local], capture_output=True, timeout=120)
    if not os.path.exists(shot):
        sys.exit("Chrome 未产出截图")

    im = Image.open(shot).convert("RGB")
    W, H = im.size
    # 找正文左右边界：取非纯白列的包围盒
    import numpy as np
    arr = np.asarray(im)
    g = np.asarray(im.convert("L"))
    cols = np.where((g < 245).sum(axis=0) > 5)[0]
    rows = np.where((g < 245).sum(axis=1) > 5)[0]
    if len(cols) and len(rows):
        x0, x1 = max(0, cols[0] - 20), min(W, cols[-1] + 20)
        top = max(0, rows[0] - 10)
    else:
        x0, x1, top = 0, W, 0
    if x1 - x0 < 500:
        x0, x1 = 0, W
    win_h = int((x1 - x0) * 4 / 3)
    top = max(0, min(top, H - win_h))
    dst = os.path.join(OUT, f"{a.slug}-offline-p2.png")
    im.crop((x0, top, x1, top + win_h)).resize((1080, 1440), Image.LANCZOS).save(dst)
    print(f"P2 {dst} src={W}x{H} crop=({x0},{top},{x1},{top+win_h})")

    # 黄条行位置（整段高亮才会有大片黄像素）
    yellow = ((arr[:, :, 0] > 240) & (arr[:, :, 1] > 225) &
              (arr[:, :, 2] < 200) & (arr[:, :, 2] > 110))
    yrows = np.where(yellow.sum(axis=1) > 40)[0]
    if len(yrows):
        y0 = int(yrows[0])
        dup = top <= y0 < top + win_h * 0.6
        print(f"highlight rows {y0}-{int(yrows[-1])}  dup_of_p2={dup}")
        if not dup:
            ytop = max(0, min(int(y0 - win_h * 0.30), H - win_h))
            dst3 = os.path.join(OUT, f"{a.slug}-offline-p3.png")
            im.crop((x0, ytop, x1, ytop + win_h)).resize((1080, 1440), Image.LANCZOS).save(dst3)
            print(f"P3 {dst3} crop=({x0},{ytop},{x1},{ytop+win_h})")
    else:
        print("未检测到黄条行" if a.mark_mode != "none" else "无高亮模式，跳过 P3")
    print(f"{dst}  src={W}x{H} crop=({x0},{top},{x1},{top+win_h})")


if __name__ == "__main__":
    main()
