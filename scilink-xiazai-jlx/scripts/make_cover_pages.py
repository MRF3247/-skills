"""生成教材 A4 封面页 + 封底页（HTML → Chrome PDF）"""
import base64
from pathlib import Path

LOGO = "/Users/Jin/Documents/素材/logo@3x.D7NFqAsV.png"
QR = "/Users/Jin/Documents/素材/刀客轻研小助手二维码.jpg"


def b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()


logo_uri = "data:image/png;base64," + b64(LOGO)
qr_uri = "data:image/jpeg;base64," + b64(QR)

COVER = f"""
<div class="page cover">
  <div class="cv-top">
    <img class="logo" src="{logo_uri}">
    <div class="cv-topline"></div>
  </div>

  <div class="cv-mid">
    <div class="cv-kicker">医学科研入门系列</div>
    <h1 class="cv-title">医学文献<br>检索与阅读</h1>
    <div class="cv-en">MEDICAL LITERATURE<br>RETRIEVAL &amp; READING</div>
    <div class="cv-rule"></div>
    <div class="cv-sub">面向零基础医学生 · 规培生 · 临床医生的系统教材</div>
    <div class="cv-intro">
      从「不知道查什么」到「知道该信哪个」。<br>
      五篇内容覆盖认知、检索、阅读、判断、工具，<br>
      每一章都给判断标准，不只给动作。
    </div>
  </div>

  <div class="cv-meta">
    <div class="meta-item"><b>5</b><span>篇</span></div>
    <div class="meta-sep"></div>
    <div class="meta-item"><b>15</b><span>章</span></div>
    <div class="meta-sep"></div>
    <div class="meta-item"><b>86</b><span>节</span></div>
    <div class="meta-sep"></div>
    <div class="meta-item"><b>9</b><span>幅图解</span></div>
  </div>

  <div class="cv-bottom">
    <img class="qr" src="{qr_uri}">
    <div class="cv-qrtext">
      <div class="qr-t1">扫码添加客服，立即接入最先进的科研Agent</div>
      <div class="qr-t2">添加客服，限时送Token，助你科研起飞</div>
      <div class="qr-t3"><a class="qr-url" href="https://ag.scilink.link/">ag.scilink.link</a></div>
    </div>
  </div>
</div>
"""

BACK = f"""
<div class="page back">
  <div class="bk-top">
    <div class="bk-line"></div>
  </div>

  <div class="bk-mid">
    <img class="bk-qr" src="{qr_uri}">
    <div class="bk-scan">扫码添加客服，立即接入最先进的科研Agent</div>
    <div class="bk-scan2">添加客服，限时送Token，助你科研起飞</div>
  </div>

  <div class="bk-sloganzone">
    <div class="bk-slogan">
      把搜文献<br>从两小时压到十分钟
    </div>
  </div>

  <div class="bk-foot">
    <img class="bk-logo" src="{logo_uri}">
    <div class="bk-brand">AI Agent 医学科研工具</div>
    <div class="bk-legal">本教材仅供学习交流使用，不构成任何医疗或科研决策建议。</div>
  </div>
</div>
"""

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
  @page {{ size: A4; margin: 0; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:"PingFang SC","Songti SC",serif; -webkit-font-smoothing:antialiased; }}
  .page {{ width:210mm; height:297mm; position:relative; overflow:hidden; page-break-after:always; }}
  .page:last-child {{ page-break-after:auto; }}

  /* ============ 封面 ============ */
  .cover {{ background:#fdfcfa; padding:22mm 20mm 18mm; display:flex; flex-direction:column; }}
  .cv-top {{ display:flex; justify-content:flex-end; }}
  .logo {{ height:9mm; }}

  .cv-mid {{ margin-top:26mm; }}
  .cv-kicker {{
    font-size:9.5pt; letter-spacing:3pt; color:#8a96a3;
    font-family:"PingFang SC"; margin-bottom:7mm;
  }}
  .cv-title {{
    font-family:"Songti SC","STSong"; font-size:46pt; font-weight:900;
    line-height:1.18; letter-spacing:2pt; color:#12202e;
  }}
  .cv-en {{
    margin-top:6mm; font-size:9pt; letter-spacing:2.4pt; color:#5b6b7a;
    line-height:1.7; font-family:"Helvetica Neue";
  }}
  .cv-rule {{
    width:34mm; height:1.6pt; background:#2f5f8f; margin:9mm 0 6mm;
  }}
  .cv-sub {{ font-size:11pt; color:#3c4a58; letter-spacing:0.6pt; }}
  .cv-intro {{
    margin-top:11mm; font-size:10pt; line-height:2.05; color:#6b7885;
    padding-left:4mm; border-left:1.4pt solid #e3e8ed;
  }}

  .cv-meta {{
    margin-top:auto; display:flex; align-items:center; gap:0;
    border-top:0.6pt solid #dde3e9; border-bottom:0.6pt solid #dde3e9;
    padding:6mm 0;
  }}
  .meta-item {{ flex:1; text-align:center; }}
  .meta-item b {{
    font-family:"Songti SC"; font-size:24pt; font-weight:900; color:#12202e;
  }}
  .meta-item span {{ font-size:9pt; color:#7b8794; margin-left:2mm; letter-spacing:1pt; }}
  .meta-sep {{ width:0.6pt; height:9mm; background:#dde3e9; }}

  .cv-bottom {{ margin-top:9mm; display:flex; align-items:center; gap:7mm; }}
  .qr {{ width:26mm; height:26mm; }}
  .qr-t1 {{ font-size:11pt; font-weight:700; color:#12202e; letter-spacing:0.5pt; line-height:1.5; }}
  .qr-t2 {{ font-size:9pt; color:#6b7885; margin-top:1.6mm; }}
  .qr-t3 {{ font-size:9pt; margin-top:1.8mm; letter-spacing:0.5pt; }}
  .qr-url {{ color:#2f5f8f; text-decoration:none; border-bottom:0.6pt solid #2f5f8f; padding-bottom:0.4mm; }}

  /* ============ 封底 ============ */
  .back {{ background:#12202e; color:#e8edf2; padding:24mm 20mm 20mm; display:flex; flex-direction:column; }}
  .bk-top {{ }}
  .bk-line {{ width:100%; height:0.8pt; background:#3d5064; }}
  .bk-mid {{ margin-top:24mm; text-align:center; }}
  .bk-qr {{ width:46mm; height:46mm; background:#fff; padding:3mm; border-radius:2mm; }}
  .bk-scan {{ margin-top:5mm; font-size:11pt; color:#d4dfe9; letter-spacing:1pt; font-weight:600; }}
  .bk-scan2 {{ margin-top:3mm; font-size:9.5pt; color:#8fa3b8; letter-spacing:0.8pt; }}

  .bk-sloganzone {{ flex:1; display:flex; align-items:center; justify-content:center; }}
  .bk-slogan {{
    font-family:"Songti SC","STSong"; font-size:33pt;
    font-weight:900; line-height:1.45; color:#fff; letter-spacing:1.5pt;
  }}
  .bk-desc {{ margin-top:12mm; font-size:10pt; line-height:2.1; color:#a8b8c8; }}

  .bk-foot {{ padding-top:12mm; border-top:0.6pt solid #33455a; }}
  .bk-logo {{ height:7mm; opacity:0.92; }}
  .bk-brand {{ margin-top:3mm; font-size:9pt; color:#8397aa; letter-spacing:1pt; }}
  .bk-legal {{ margin-top:6mm; font-size:7.5pt; color:#5e7186; line-height:1.7; }}
</style></head>
<body>{COVER}{BACK}</body></html>"""

out = Path("/Users/Jin/Documents/Open Programs/funasr/jlx_book/book/_cover.html")
out.write_text(HTML, encoding="utf-8")
print(f"✓ {out}  ({len(HTML)//1024}KB, logo+qr 已内嵌)")
