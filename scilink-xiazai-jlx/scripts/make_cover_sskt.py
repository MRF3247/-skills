"""生成教材 A4 封面页 + 封底页（HTML → Chrome PDF）v2"""
import base64
from pathlib import Path

LOGO = "/Users/Jin/Documents/素材/logo@3x.D7NFqAsV.png"
QR = "/Users/Jin/Documents/素材/刀客轻研小助手二维码.jpg"
SITE = "https://ag.scilink.link/"

MAIN = "扫码添加客服，立即接入最先进的科研Agent"
SUB = "添加客服，限时送Token，助你科研起飞"
CAPS = ["文献检索", "开题报告", "综述写作", "科普文章", "数据清洗",
        "统计分析", "机器学习建模", "科研制图", "论文辅助", "汇报PPT"]


def b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()


logo_uri = "data:image/png;base64," + b64(LOGO)
qr_uri = "data:image/jpeg;base64," + b64(QR)

caps_rows = (" · ".join(CAPS[:5]), " · ".join(CAPS[5:]))
site_text = SITE.replace("https://", "").rstrip("/")

COVER = f"""
<div class="page cover">
  <div class="cv-top">
    <img class="logo" src="{logo_uri}">
  </div>

  <div class="cv-mid">
    <div class="cv-kicker">医学科研进阶系列</div>
    <h1 class="cv-title">放养硕博<br>自救指南</h1>
    <div class="cv-en">FROM START<br>TO PUBLICATION</div>
    <div class="cv-rule"></div>
    <div class="cv-sub">从起步到发表 · 面向硕士与博士研究生</div>
    <div class="cv-intro">
      从选题到投稿，十五个环节一个不漏。<br>
      五篇内容覆盖起步、开题、中期、毕业、发表，<br>
      每个阶段都给出可照做的动作和判断标准。
    </div>
  </div>

  <div class="cv-bottom">
    <div class="cta-line"></div>
    <div class="cta-wrap">
      <img class="qr" src="{qr_uri}">
      <div class="cta-text">
        <div class="cta-main">{MAIN}</div>
        <div class="cta-sub">{SUB}</div>
        <a class="cta-url" href="{SITE}">{site_text}</a>
      </div>
    </div>
  </div>
</div>
"""

BACK = f"""
<div class="page back">
  <div class="bk-top"><div class="bk-line"></div></div>

  <div class="bk-mid">
    <img class="bk-qr" src="{qr_uri}">
    <div class="bk-main">{MAIN}</div>
    <div class="bk-sub">{SUB}</div>
    <a class="bk-url" href="{SITE}">{site_text}</a>
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
  a {{ text-decoration:none; }}

  /* ============ 封面 ============ */
  .cover {{ background:#fdfcfa; padding:22mm 20mm 18mm; display:flex; flex-direction:column; }}
  .cv-top {{ display:flex; justify-content:flex-end; }}
  .logo {{ height:9mm; }}

  .cv-mid {{ margin-top:30mm; }}
  .cv-kicker {{ font-size:9.5pt; letter-spacing:3pt; color:#8a96a3; font-family:"PingFang SC"; margin-bottom:7mm; }}
  .cv-title {{ font-family:"Songti SC","STSong"; font-size:46pt; font-weight:900; line-height:1.18; letter-spacing:2pt; color:#12202e; }}
  .cv-en {{ margin-top:6mm; font-size:9pt; letter-spacing:2.4pt; color:#5b6b7a; line-height:1.7; font-family:"Helvetica Neue"; }}
  .cv-rule {{ width:34mm; height:1.6pt; background:#2f5f8f; margin:9mm 0 6mm; }}
  .cv-sub {{ font-size:11pt; color:#3c4a58; letter-spacing:0.6pt; }}
  .cv-intro {{ margin-top:11mm; font-size:10pt; line-height:2.05; color:#6b7885; padding-left:4mm; border-left:1.4pt solid #e3e8ed; }}

  .cv-bottom {{ margin-top:auto; }}
  .cta-line {{ width:100%; height:0.6pt; background:#dde3e9; margin-bottom:9mm; }}
  .cta-wrap {{ display:flex; align-items:flex-start; gap:8mm; }}
  .qr {{ width:32mm; height:32mm; flex:0 0 32mm; }}
  .cta-text {{ padding-top:0.5mm; }}
  .cta-main {{ font-size:11.5pt; font-weight:700; color:#12202e; line-height:1.75; letter-spacing:0.4pt; }}
  .cta-sub {{ margin-top:3.2mm; font-size:10pt; color:#6b7885; line-height:1.75; letter-spacing:0.3pt; }}
  .cta-url {{ display:inline-block; margin-top:4mm; font-size:10pt; color:#2f5f8f; letter-spacing:1pt; border-bottom:0.8pt solid #9dbcd6; padding-bottom:0.6mm; }}

  /* ============ 封底 ============ */
  .back {{ background:#12202e; color:#e8edf2; padding:24mm 20mm 20mm; display:flex; flex-direction:column; }}
  .bk-line {{ width:100%; height:0.8pt; background:#3d5064; }}
  .bk-mid {{ flex:1; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding-bottom:6mm; }}
  .bk-qr {{ width:52mm; height:52mm; background:#fff; padding:3.5mm; border-radius:2mm; }}
  .bk-main {{ margin-top:13mm; font-family:"Songti SC","STSong"; font-size:15pt; font-weight:700; line-height:1.7; color:#fff; letter-spacing:0.6pt; }}
  .bk-sub {{ margin-top:4.5mm; font-size:11pt; line-height:1.8; color:#9fb0c1; letter-spacing:0.5pt; }}
  .bk-url {{ display:inline-block; margin-top:9mm; font-size:12pt; color:#6fa8d6; letter-spacing:1.4pt; border-bottom:0.9pt solid #3d6d94; padding-bottom:1mm; }}

  .bk-foot {{ padding-top:12mm; border-top:0.6pt solid #33455a; text-align:center; }}
  .bk-logo {{ height:7mm; opacity:0.92; }}
  .bk-brand {{ margin-top:3mm; font-size:9pt; color:#8397aa; letter-spacing:1pt; }}
  .bk-legal {{ margin-top:6mm; font-size:7.5pt; color:#5e7186; line-height:1.7; }}
</style></head>
<body>{COVER}{BACK}</body></html>"""

out = Path("/Users/Jin/Documents/Open Programs/funasr/sskt_book/book/_cover.html")
out.write_text(HTML, encoding="utf-8")
print(f"✓ {out}  ({len(HTML)//1024}KB)")
