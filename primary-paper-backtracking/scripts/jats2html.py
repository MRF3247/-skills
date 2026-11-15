#!/usr/bin/env python3
"""JATS XML (Europe PMC fullTextXML) -> 干净 HTML，供 Chrome headless 打印成 PDF。

用法：
    curl -s -A "Mozilla/5.0" \
      "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/fullTextXML" -o fulltext.xml
    # 1) 从 PMC 文章页取图（browser_console 读 img.currentSrc），存到 figs/ 下，按内容重命名
    # 2) 改 FIGMAP 成该论文的图片文件名 -> 本地文件
    python3 jats2html.py fulltext.xml paper.html
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "$CHROME" --headless=new --disable-gpu --no-sandbox --virtual-time-budget=20000 \
      --no-pdf-header-footer --print-to-pdf=out.pdf "file://$PWD/paper.html"

验收：
    python3 -c "import fitz;d=fitz.open('out.pdf');print(d.page_count, sum(len(p.get_images(full=True)) for p in d))"
    页数合理（同类论文约 13-22 页）、内嵌图数 == 图张数、关键数字与每个 FIG 标签各出现 1 次。

坑（都踩过）：
  * 为了让 ElementTree 解析而删掉 xmlns 声明 -> 报 unbound prefix（xlink: 前缀失去声明）。
    正确做法：只把 xlink:href 改名为 href，保留 xmlns 声明。
  * 在线附录的图/表挂在 back/app-group/app 下，只遍历 body/sec 会漏掉
    （BICR 独立评审曲线、亚组森林图往往正在这里）。
"""
import re, sys, html
import xml.etree.ElementTree as ET

SRC = sys.argv[1] if len(sys.argv) > 1 else 'fulltext.xml'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'paper.html'

raw = open(SRC, encoding='utf-8').read()
# 只把 xlink:href 属性改名为 href（保留 xmlns 声明，避免 unbound prefix）；元素本身无默认命名空间
raw = raw.replace('xlink:href', 'href')
root = ET.fromstring(raw)

# 按该论文实际的文件名改这张表；左值来自 JATS 里的 graphic/@href，右值是本地已下载的图
FIGMAP = {'jco-44-1597-g001.jpg': 'figs/fig1.jpg', 'jco-44-1597-g002.jpg': 'figs/fig2.jpg',
          'jco-44-1597-g003.jpg': 'figs/fig3.jpg', 'jco-44-1597-g004.jpg': 'figs/figA1.jpg',
          'jco-44-1597-g005.jpg': 'figs/figA2.jpg', 'jco-44-1597-g006.jpg': 'figs/figA3.jpg'}
INLINE_OK = {'italic': 'i', 'bold': 'b', 'sup': 'sup', 'sub': 'sub', 'monospace': 'code',
             'underline': 'u', 'strike': 's', 'sc': 'span'}


def esc(t):
    return html.escape(t or '')


def inline(el):
    """把元素内容（含 text/tail）转成 HTML 字符串。"""
    parts = [esc(el.text)]
    for ch in list(el):
        tag = ch.tag
        if tag in INLINE_OK:
            parts.append('<%s>%s</%s>' % (INLINE_OK[tag], inline(ch), INLINE_OK[tag]))
        elif tag in ('xref', 'fn', 'target', 'ext-link', 'uri'):
            parts.append(inline(ch))
        elif tag == 'graphic':
            href = (ch.get('href') or '').split('/')[-1]
            src = FIGMAP.get(href, '')
            parts.append('<img src="%s">' % src if src else '')
        else:
            parts.append(inline(ch))
        parts.append(esc(ch.tail))
    return ''.join(p for p in parts if p)


def table_html(tw):
    out = []
    cap = tw.find('caption')
    if cap is not None:
        out.append('<p class="cap"><b>%s</b> %s</p>' % (esc(tw.findtext('label') or ''), inline(cap).strip()))
    t = tw.find('table')
    if t is not None:
        out.append('<table>')
        for part in ('thead', 'tbody'):
            node = t.find(part)
            rows = node.findall('tr') if node is not None else (t.findall('tr') if part == 'tbody' else [])
            for tr in rows:
                cells = tr.findall('th') + tr.findall('td')
                out.append('<tr>' + ''.join('<%s>%s</%s>' % (
                    'th' if c.tag == 'th' else 'td', inline(c), 'th' if c.tag == 'th' else 'td') for c in cells) + '</tr>')
        out.append('</table>')
    for fn in tw.findall('table-wrap-foot/fn') + tw.findall('table-wrap-foot/p'):
        out.append('<p class="fn">%s</p>' % inline(fn))
    return '\n'.join(out)


def fig_html(fig):
    label = fig.findtext('label') or ''
    cap = fig.find('caption')
    g = fig.find('graphic')
    src = FIGMAP.get((g.get('href') or '').split('/')[-1], '') if g is not None else ''
    if not src:
        return ''
    return ('<figure><img src="%s">\n<figcaption><b>%s.</b> %s</figcaption></figure>'
            % (src, esc(label), inline(cap).strip() if cap is not None else ''))


def sec_html(sec, depth=2):
    out = []
    title = sec.find('title')
    lvl = min(depth, 4)
    if title is not None and inline(title).strip():
        out.append('<h%d>%s</h%d>' % (lvl, inline(title).strip(), lvl))
    for ch in list(sec):
        tag = ch.tag
        if tag == 'title':
            continue
        if tag in ('sec', 'boxed-text'):
            out.append(sec_html(ch, depth + 1))
        elif tag == 'p':
            out.append('<p>%s</p>' % inline(ch).strip())
        elif tag == 'list':
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(li).strip() for li in ch.findall('list-item')))
        elif tag == 'table-wrap':
            out.append(table_html(ch))
        elif tag == 'fig':
            out.append(fig_html(ch))
        else:
            txt = inline(ch).strip()
            if txt:
                out.append('<p>%s</p>' % txt)
    return '\n'.join(out)


# ---- 题录 ----
title = root.findtext('.//title-group/article-title') or ''
authors = []
for c in root.findall('.//contrib-group/contrib'):
    nm = c.find('name')
    if nm is not None:
        authors.append(('%s %s' % (nm.findtext('given-names') or '', nm.findtext('surname') or '')).strip())
pub = root.findtext('.//journal-meta/journal-title-group/journal-title') or ''
year = root.findtext('.//pub-date/year') or ''
vol, iss = root.findtext('.//volume') or '', root.findtext('.//issue') or ''
pg, lpg = root.findtext('.//fpage') or '', root.findtext('.//lpage') or ''
doi = next((a.text.strip() for a in root.findall('.//article-id') if a.get('pub-id-type') == 'doi'), '')
abstract, body, refs = root.find('.//abstract'), root.find('.//body'), root.find('.//ref-list')

H = ['<html><head><meta charset="utf-8"><style>', '''
@page { size: A4; margin: 16mm 15mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color:#111; }
h1 { font-size: 17pt; line-height:1.3; margin: 0 0 6px; }
h2 { font-size: 13pt; margin: 18px 0 6px; border-bottom:1px solid #ccc; padding-bottom:3px; }
h3 { font-size: 11.5pt; margin: 12px 0 4px; }
h4, h5 { font-size: 10.8pt; margin: 10px 0 3px; }
p { margin: 0 0 7px; text-align: justify; }
.authors { font-size: 10pt; margin: 2px 0 8px; }
.citebox { border:1px solid #bbb; background:#f7f7f7; padding:8px 10px; font-size:9.5pt; margin:10px 0 14px; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 6px 0 12px; }
th, td { border: 0.5pt solid #999; padding: 3px 4px; text-align: left; vertical-align: top; }
th { background: #eee; }
.cap { font-size: 9pt; margin: 8px 0 3px; }
.fn { font-size: 8.4pt; color:#333; margin: 2px 0; }
figure { margin: 10px 0 14px; page-break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 8.8pt; color:#333; margin-top: 4px; }
ul { margin: 0 0 8px 18px; padding: 0; } li { margin-bottom: 3px; }
.refs p { font-size: 8.6pt; margin-bottom: 4px; text-indent: -14px; padding-left: 14px; }
sup { font-size: 7.5pt; }
h2, h3 { page-break-after: avoid; }
''', '</style></head><body>']
H += ['<h1>%s</h1>' % esc(title), '<div class="authors">%s</div>' % esc(', '.join(authors))]
if abstract is not None:
    ab_title = abstract.find('title')
    H.append('<div class="citebox"><b>%s</b><br>%s · %s;%s(%s):%s<br>DOI: %s</div>'
             % (esc(ab_title.text if ab_title is not None else 'Abstract'), esc(pub), esc(year), esc(vol), esc(iss),
                esc(pg if lpg else pg or ''), esc(doi)))
    H.append('<h2>Abstract</h2>')
    for ch in list(abstract):
        if ch.tag == 'sec':
            H.append(sec_html(ch, 3))
        elif ch.tag in ('p', 'abstracttext'):
            H.append('<p>%s</p>' % inline(ch).strip())
if body is not None:
    for sec in body.findall('sec'):
        H.append('<div class="sec">%s</div>' % sec_html(sec, 2))
if refs is not None:
    back = root.find('.//back')
    if back is not None:
        apps = back.findall('app-group/app') + back.findall('app')
        if apps:
            H.append('<h2>在线附录（Appendix）</h2>')
            for a in apps:
                H.append('<div class="sec">%s</div>' % sec_html(a, 3))
    H.append('<h2>References</h2><div class="refs">')
    for ref in refs.findall('ref'):
        txt = re.sub(r'\s+', ' ', inline(ref).strip())
        if txt:
            H.append('<p>%s</p>' % txt)
    H.append('</div>')
H.append('<hr><p class="fn">本文由 PMC 开放获取全文按原始 JATS XML 本地排版导出，仅用于个人学习研究；版权归原作者与期刊所有，请勿再分发。</p>')
H.append('</body></html>')

open(OUT, 'w', encoding='utf-8').write('\n'.join(H))
print('写出', OUT, '|', len(authors), '作者 | refs:', len(refs.findall('ref')) if refs is not None else 0)
