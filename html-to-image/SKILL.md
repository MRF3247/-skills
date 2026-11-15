---
name: html-to-image
description: 网页/PDF 转图：长图、3:4 截图、官方信源原样裁切。Use when 用户要图或要「按比例截图」。
---

# HTML/网页 → 图片

三种目标形态，先分清楚是哪一种（用户说"长图/整页"= 形态 1；说具体比例或分辨率如"3:4 的 2K"= 形态 2 或 3）：
- **形态 1 完整长图**：整页内容、高度自适应（实测选题详情页 1280×8472 CSS px → 2560×16944 px 2x）
- **形态 2 定尺寸图（设计卡）**：固定画布重排出一张（3:4、2K、小红书 1242×1656 等）→ 见下方「定尺寸图」节
- **形态 3 原样截图裁切**：只把真实页面/文件截下来按比例裁，不加中文标题、不排版

> **形态 2 与 3 别猜错，猜错必返工。** 用户说"给我官方信源的截图"「截图就行」「按比例给我截图」= 形态 3：交付物里除了裁切不许有你自己加的任何元素（标题、kicker、表格、图注、边框）。他明确说过"不需要你排版做图"。设计卡（形态 2）只在他说"做图卡/海报/封面"或要求"重新排版"时才做。拿不准就先交形态 3——它是形态 2 的子集，反过来不成立。

## 核心方案（Playwright + 系统 Chrome）

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=True)  # 用系统 Chrome，避免 playwright install 版本不匹配
    page = browser.new_page(viewport={"width": 1280, "height": 900},
                            device_scale_factor=2)  # 2x 高清
    page.goto(f"file://{SRC}", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)  # 等字体/图片渲染
    # 关键：解除内部滚动容器（见下）——★ 必须 overflowX=clip + overflowY=visible，见坑2
    page.evaluate("""() => {
        const els = [...document.querySelectorAll('*')].filter(e => {
            const s = getComputedStyle(e);
            return (s.overflowY === 'auto' || s.overflowY === 'scroll' || s.overflowY === 'hidden');
        });
        els.forEach(e => {
            e.style.overflowX = 'clip';
            e.style.overflowY = 'visible';
        });
        document.body.style.height = 'auto';
        document.documentElement.style.height = 'auto';
    }""")
    page.wait_for_timeout(500)
    page.screenshot(path=OUT, full_page=True)
    browser.close()
```

## 致命坑：内部滚动容器导致截图截断

**症状**：`full_page=True` 截图高度 = 视口高度（如 900px），长页面内容大量丢失；但 `document.body.scrollHeight` 却只有 900。

**原因**：SPA/后台管理页（Element UI 等）把内容放在 `overflow: auto/scroll` 的容器里（如 `<main class="el-main">`），body 高度被 CSS 锁死在视口。Playwright 的 full_page 只按 body 高度截，容器内的滚动内容（可能 8000+px）全被裁掉。

**诊断**（截图前必做）：
```python
page.evaluate("""() => {
    const els = [...document.querySelectorAll('*')].filter(e => {
        const s = getComputedStyle(e);
        return (s.overflowY === 'auto' || s.overflowY === 'scroll') && e.scrollHeight > e.clientHeight + 10;
    });
    return els.map(e => ({tag: e.tagName, cls: (e.className||'').toString().slice(0,60),
                          clientH: e.clientHeight, scrollH: e.scrollHeight}));
}""")
```
非空即存在内部滚动容器 → 必须先注入 overflow 解除（见上方代码），再全页截图。解除后 `body.scrollHeight` 应显著增大（几百 → 数千 px）。

## 坑2（最隐蔽）：overflowX 必须用 `clip`，不能设 `overflow: visible` 简写

**症状**：截图右侧出现大片空白，`scrollWidth` 被撑到远超视口宽（如 1280 视口 → 2683px）。用户反馈「右边大量空白」。

**原因**：两层机制叠加——
1. 图表库（ECharts 等）在 DOM 里留**绝对定位的离屏缓冲 canvas**（实测 `left ≈ 101177px`）。注入 `overflow: visible`（简写，X 和 Y 都放开）后这些 canvas 把文档横向撑宽。
2. CSS 规范：`overflowY: visible` 与 `overflowX: hidden/auto` 混用时，visible 会被**强制计算为 auto**（纵向仍滚动、仍截断）。所以不能只设 Y。

**修复**：`e.style.overflowX = 'clip'; e.style.overflowY = 'visible';` —— clip 可与 visible 共存，且裁剪横向溢出不撑宽文档。**不要用 `e.style.overflow = 'visible'` 简写**。

**验证**：注入后 `document.documentElement.scrollWidth` 必须仍 == 视口宽（1280），`scrollHeight` 数千 px。

## 定尺寸图：复刻某个网页的版式，出 3:4 / 2K 成图

> 要复刻的不是网页而是一张**梗图/对比图**（"参考这张图给我出一个我们的版本"）时，走技能 `meme-remake`：手绘线条、环绕文字的乱/整对比、白色 halo 层都是另一套做法，别用本节的网页模仿思路硬做。

用户给一个新闻/文章 URL，要求"重新排版成 3:4 的 2K 图片、字体配色跟原站一致"时走这套。

### 尺寸与像素比（别按最终像素设计 CSS）
以 CSS 像素设计版面，`--force-device-scale-factor=2` 出 2x：
- 3:4 的 2K = **768×1024 CSS px → 1536×2048 px 成品**（768 宽约等于平板版式，正文 16–17px 正合适）
- 不要直接把画布写成 1536 CSS px：17px 正文会被挤成蚂蚁字

### Chrome headless 直出（没装 playwright 也不用装）
```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --hide-scrollbars --virtual-time-budget=6000 \
  --screenshot=out.png --window-size=768,1024 --force-device-scale-factor=2 \
  "file:///abs/path/card.html"
```
- `--virtual-time-budget=6000` 等远程图片/字体加载完再截，否则截到半张图
- 日志里的 `CVDisplayLinkCreateWithCGDisplay failed`、`Trying to load the allocator multiple times` 是**无害噪音**；判成功只看产物像素尺寸
- 固定尺寸图：`html,body{width:768px;height:1024px;overflow:hidden}`；CSS 与图片走相对路径放同目录，`file://` 直接能加载

### 形态 3：官方信源要精确比例 → 先找官方 PDF，网页截图只是备选

企业/机构 newsroom 的新闻稿几乎都另发一份 PDF，它比网页截图好得多：无 cookie 墙、无 "Welcome to X.com" 弹窗、无侧栏广告、字号与排版就是印刷体，且首页通常就把核心数据排完了。

1. **找 PDF 链接**：页面上 "Save / PDF / Download" 按钮的 href（常见于 `s2.q4cdn.com`、`s1.q4cdn.com`、`businesswire`），或页面 `<a href="...pdf">`。
2. **下载**：`curl -sL --max-time 60 -A 'Mozilla/5.0' -o out.pdf '<url>'`，再用 `file out.pdf` 确认是 "PDF document" 而不是登录页；页数也应合理（企业稿常 30+ 页含免责声明）。
3. **渲染**：PyMuPDF，dpi=200（必须 `env -u PYTHONPATH /usr/bin/python3`，见下方 PYTHONPATH 坑）。Letter 页 612×792 pt → 1700×2200 px，比例 1.294，**离 3:4 只差左右一点**。
4. **裁成目标比例**（整页保留，不动内容）：
```python
nw = int(h*3/4); left = (w-nw)//2
Image.open(f"{k}_p1.png").crop((left,0,left+nw,h)).save(f"{k}_3x4.png")
```
5. **选哪一页/哪一份稿**：优先选首页就含核心数字的那份。企业常就同一条数据发**两轮稿**（首次顶线 / 会议当天详解），详解稿首页往往自带 HR、95%CI、p 值和绝对率，顶线稿则只有"达标"二字。
6. **核验**：看图通道问三件事——标题、日期、目标数字段是否都完整；或先 `page.get_text()` 程序化确认关键词在首页（PDF 版日期常写成 `2026-10-22` 而不是 `October 22, 2026`，用文献里的写法去找会误判）。
7. 成品不加任何中文、不重排；文件名带来源与日期：`<来源>_<日期>_<主题>_3x4.png`。

### 形态 3b：要「高亮重点段落」的证据图

用户从「给我官方截图」追加「再来几张把重点段落高亮」时，做的是 **PDF 原文框选**，不是自己画框、也不是重排版。

1. **先量正文栏 x 范围**：`min(b[0] for b in page.get_text("blocks"))` / `max(b[2])`。Letter 612pt 页正文常落在 x≈43–568。**clip 宽度必须完整覆盖这个区间**；按「页面居中裁 480pt」看着聚焦，实际每行首尾各切一截，整批要重做。居中裁用 `x0=(612-W)/2` 且 `W ≥ 正文宽 + 30`。
2. **定位段落**：`page.search_for("42% (HR=0.58")` 拿 rect；要高亮整段就取该关键词所在 `blocks` 的 bbox，多个关键词用矩形并集（`r |= other`），再外扩 2pt。只高亮关键词本身会漏掉同段里的对照值。
3. **高亮叠色**：渲染后 PIL 画半透明矩形，`fill=(255,221,51,110)`（alpha 再大就盖住字），坐标换算 `(pt - clip.x0) * dpi/72`。
4. **段落跨页**：末行在页底、续句在下一页时，两页各 `get_pixmap(clip=...)` 后竖拼：上段裁到该行下沿 +6pt，下段从正文首行上方 ~15pt 起，**页码行必须排除在 clip 之外**，否则拼缝中间插一个「3」加一大块空白。拼好后的接缝应只有一行行距。
5. **比例精确化**：出图后 `w = int(h*3/4)` 再 crop。1557×2073 这种 0.7511 的偏差，用户会按「3:4」量出来。
6. **文件名写清高亮的是哪段**（`<来源>_<日期>_高亮_p3_绝对率_3x4.png`）——用户按内容挑图，不给语义就得逐张点开。
7. **同一段落别出两张图**：用户会用「这两张一样吧，合成一张不就行了」打回。同页多段要一起高亮时，直接出一张合图（见下节），不要分别出 p3/p4。

### 形态 3c：新闻网页截图 + 荧光笔高亮（源头是网页不是 PDF）

用户要「把新闻原链接截两张图：一张带标题、一张带关键段落，关键段落用马克笔高亮」时走这条。和 3b 的区别是源头是 HTML 页面，没有 PDF 可用。

1. **先用浏览器工具打开页面，再在 DOM 里造一个干净版**：`browser_navigate` → `browser_console` 里克隆 `<article>`、把 `document.body.innerHTML` 换成它，并删掉 `.sharedaddy/.jp-relatedposts/aside/footer/nav/form/iframe`：
```js
const art = document.querySelector('article').cloneNode(true);
art.querySelectorAll('.sharedaddy, .jp-relatedposts, .comments, aside, footer, .ad, iframe, nav, form, .related-posts').forEach(e => e.remove());
document.body.innerHTML = '';
document.body.style.cssText = 'margin:0;padding:36px 44px;background:#fff;width:1000px;box-sizing:border-box;font-family:Georgia,serif;color:#1a1a1a';
document.body.appendChild(art);
art.querySelectorAll('p').forEach(p => p.style.cssText = 'font-size:19px;line-height:1.62;margin:0 0 20px');
```
站点名/日期被我一起删掉了 → 再插一条 masthead 条（站名 + 域名 + 日期）放在 `h1` 前面，截图才有出处感：日期**从 URL 路径里取**（`/2026/10/19/`），别从正文推断。
2. **两张图分别定机位再截**：带标题那张 `window.scrollTo(0,0)`；高亮那张 `window.scrollTo(0, p.getBoundingClientRect().top + scrollY - 300)`。`browser_vision` 每次返回的 `screenshot_path` 就是一张 PNG。
3. **裁到内容栏**：视口可能远宽于内容（`innerWidth` 3440 / body 1000），PIL `crop((0,0,1100,H))` 即可，别按视口宽保留右侧空白。两张裁成同一宽高，并列在文档里才齐。
4. **高亮位置用 DOM 行 rect，不靠估**：CSS 的 `background-image` 高亮做出来是**规整色块**，模型和用户都会指出「像数字高亮不像马克笔」。改成 PIL 逐行画：先用 `Range.getClientRects()` 拿到每行矩形，**同一 y 的多个 rect 必须合并成 min(x)..max(x+w)**（斜体/链接会把一行拆成 4-5 个 rect）：
```js
const r = document.createRange(); r.selectNodeContents(p);
[...r.getClientRects()].filter(x => x.width > 5).map(x => ({y: Math.round(x.top), x1: Math.round(x.left), x2: Math.round(x.left + x.width)}))
```
5. **画真笔迹**（直接跑 `scripts/marker_highlight.py`）：逐列上下边缘随机游走（±2px）+ 整行 0.035 倾斜 + 每行随机重涂一块加深 + 首尾 9px 渐弱 + `gaussian_filter(sigma≈0.55)` + 极轻噪点，最后用 multiply 叠色（`out = arr*(1-a) + arr*YELLOW/255*a`）而不是直接盖半透明色。整体 alpha 下限 0.6，低了就像选区。
6. **自检**：放大 2 倍裁一块给 `vision_analyze` 看（整图缩放看不出笔迹质感）；同时确认三段文字**完整覆盖**（跨行断词处最容易漏半行）。

### 高亮图合并 / 二次加高亮（把「pA 高亮X段」「pB 高亮Y段」合成一张）

同一份 PDF 出的两张高亮图**通常不是同一裁切**（滚动/裁剪位置差几十到上百 px），直接叠合必错位。做法：选内容覆盖最全的那张作底图，在它上面补画缺的那段高亮。

1. **先 diff 判断关系**：`np.abs(na-nb).sum(axis=2)>20` 取行分组。差异遍布全页 = 两张是同页不同偏移（不能叠加，只能补画）；差异集中在两条带 = 同裁切不同高亮（可直接合成）。
2. **量原高亮的几何**：黄色蒙版 `(|r-255|<12)&(|g-240|<14)&(|b-167|<40)` → 行分组得各条带的 y 范围。高亮是**全宽矩形**（x 从 0 到图宽），纵向从该段首行顶到最后一行底，**行间空隙也染黄**（整段一块，不是逐行条带）。
3. **反推原叠色配方**，不要自己调透明度——色不一致一眼看得出。设叠加色 C、透明度 a，纯白底叠后得 `bg`、正文深色 T 叠后得 `text`：`bg = aC+(1-a)*255`、`text = aC+(1-a)T`，两式相减消掉 C 即得 `a = (255-bg_luma)/(255-T_luma)`，再逐通道解 C。实测配方 `a≈0.437, C=(255,221,53)`：白底 → (255,240,167)，#868686 正文 → (187,172,99)。
4. **应用**：`out = a*C + (1-a)*src`，逐通道整块矩形；抗锯齿灰阶会跟着自动变化，不必单独描字。
5. **验证两项**：新区域最常见色/最深文字色与原高亮区一致（差 ≤1）；行分组确认没多染下一段小标题或 About 段。
6. 文件名写清两段内容（`..._高亮_疗效+安全性_合并_3x4.png`），原图保留不覆盖。

### 真实网页截图做素材卡（用户说"数据截图/网页截图"时）

用户要的是**页面真实截屏**，不是自己画的复刻版；复刻版只用于出"设计卡"。走这条：

1. **截远程网页用浏览器工具，不要用 Chrome headless 直开 URL**：`browser_navigate` → `browser_console` 清遮挡 → `browser_vision`，它返回的 `screenshot_path` 就是 PNG。headless 直开远程站容易卡在代理/反爬上迟迟不返回；本地 `file://` 渲染才用 headless。
   ⚠️ **PNG 像素尺寸 ≠ JS 里的视口尺寸**：JS 报 `innerWidth/innerHeight` 1920×917 时，截回来的 PNG 可能是 1710×938。所以**裁剪坐标必须先 `Image.open(png).size` 读实际像素，再在像素坐标系里定位**；拿 `getBoundingClientRect()` 的 CSS 值乘一个"缩放比"去算必错，且两个方向的比例还不一样。
2. **截图前必须清遮挡**，否则整张被盖住：
   - 商业媒体站的 cookie 框（osano 一类）：`[...document.querySelectorAll('button,a')].find(e=>/^\s*Reject All\s*$/i.test(e.innerText))?.click()`。整块 `remove()` 的节点常被重新渲染，点准按钮更稳。
   - 药企/品牌站的欢迎页（"Welcome to X.com" + Continue）：同样按按钮文字点 `Continue`。
3. **裁掉页面两侧大片空白**：`document.querySelector('h1').getBoundingClientRect()` 取正文栏 `x`/`width`，PIL 裁 `(x-20, 0, x+width+20, H)`。同站点栏位恒定，量一次即可复用。
4. **要让截图停在某句数据上**：先滚动再截——
   `[...document.querySelectorAll('p')].find(p=>/目标句/.test(p.innerText))?.scrollIntoView({block:'center'})`
5. **裁切终点选在段末/日期行之后、下一个块之前**。切进半行文字一眼看得出裁坏；宁可少截。同页多个元素要一次量全（如标题 `h1` 底部、日期段 `top`），否则会像这次一样把日期行裁掉、返工重截。

卡片侧三个坑：
- `.shot{margin-top:auto}` 负责把截图压到卡片底部；**HTML 里别再写 inline `margin-top:30px`**——inline 覆盖 auto，底部空一大块，得回头改文件重渲染。
- 截图按 `width:100%` 放进 660–700px 栏宽；**先算高度**（原图高 × 目标宽 ÷ 原宽）再排标题与图注，否则 1024px 画布装不下。
- 表格卡底部留白大时，加一行有信息量的真实数据（如绝对发生率 + "未公布"）比调行距更补版；但**列头必须能唯一对应**，两组数值别挤进同一格（"联合 72.4%/单药 49.1%" 要分行写）。

**版权**：外媒主图多为 Getty/图库授权图，截图里带进去要主动提示商用风险，并给"裁掉/换自家配图"的选项。

### 复刻原站风格：先取材，别凭记忆画
用浏览器 + `browser_console` 跑 JS 取**实测值**：
1. **品牌 logo**：取页面内联 SVG 的 `outerHTML`（如 `.brand-logo__icon`）**整个 path 粘进自己的 HTML**，不要自己画近似形状；填充色用 CSS 控制
2. **配色字号**：`getComputedStyle` 取标题 fontFamily/size/weight/letterSpacing、正文色、图注色、分隔线色，原样搬进 CSS 变量
3. **配图抬分辨率**：改用图床 URL 参数，别用页面里那张 800px 缩略图（例 `?q=w_2048,c_fill` → 2048×1152）。同一 URL 换参数可能回同一张，逐档试 `w_1600 / w_2048 / c=original` 并**读实际像素尺寸**确认
4. **字体**：原站用授权字体（CNN Sans 这类）时用系统近似体（英文 Helvetica Neue，中文苹方/冬青黑体），交付时**如实说明是近似替代**，不要说"完全还原"

### 版式取舍
- **只复刻品牌与内容元素**：logo、分类 kicker、标题、作者行、主图、图注、正文、来源行；**删掉原站的功能控件**（搜索图标、登录/注册、多余导航项）—— 图是用来发的不是用来点的，用户会明确要求清掉
- 外媒文章页的辨识三点：主图 16:9、图注用衷线小字灰（`#6e6e6e`）、日期行大写 + 字距
- 中文版：标题/正文/图注/日期全译，作者保留英文原名 + 中文角色说明，kicker 与"阅读 X 分钟"也要译

### 交付前自检（两关都要过）
1. **程序化查溢出**（比目测可靠）：
```python
from PIL import Image; import numpy as np
a = np.array(Image.open("card.png").convert("L"))
rows = np.where(a.min(axis=1) < 200)[0]
print("最后有内容的行:", rows.max(), "/", a.shape[0])   # 贴到最底 = 版式溢出被裁
```
2. **视觉只查底部**：`vision_analyze(region=[0, 高*0.7, 宽, 高])` 读正文最后一句 + 页脚是否完整（整图缩放看不清半行被裁）

### 成品落地
成品 `cp` 到 `~/Downloads/`，文件名带语义：`<主题>_<语种>_3x4_2K.png`。工程放临时目录时要告知路径，并提醒 `/tmp` 重启会清。

## docx/Office 文档首页截图（要真页面，不要重绘）

用户要「把 N 份 Word 模板的首页截图排进封面」时，截图必须来自真实渲染：

1. **`qlmanage -t` 只能用来快速预览，不能当交付素材**：macOS Quick Look 对用空格/制表符对齐的封面表格渲染错位（字段被拆成竖排单字），对表格版反而正常——同一批文档有的崩有的不崩，肉眼抽查两张看不出。
2. **正解是 LibreOffice headless**：`soffice --headless --convert-to pdf --outdir <dir> */*.docx`（一次传多个文件，10 份约 30 秒），再用 PyMuPDF `get_pixmap(dpi=160)` 渲染第 1 页。
3. **首次 headless 必踩：中文全变豆腐块**。LO 默认 profile 在 mac 上找不到中文，PDF 字体表里全是 DejaVuSans / LinuxLibertine，`get_text()` 正常但画面是 □。修法（实测一次成功）：
   ```bash
   rm -rf /tmp/lo_profile
   "…/LibreOffice.app/Contents/MacOS/soffice" -env:UserInstallation=file:///tmp/lo_profile --headless --convert-to pdf … # 先跑一次建 profile
   mkdir -p /tmp/lo_profile/user/fonts
   cp "/System/Library/Fonts/Supplemental/Songti.ttc" "/System/Library/Fonts/STHeiti Light.ttc" ~/Library/Fonts/AlibabaPuHuiTi-3-55-Regular.otf /tmp/lo_profile/user/fonts/
   # 再跑转换；验证：fitz page.get_fonts() 里要出现 STSongti / AlibabaPuHuiTi
   ```
4. **验收看字体表而不是肉眼**：`page.get_fonts()` 无任何中文字体 = 一定全是方块。
5. 无 brew 时装 LO：直接 curl 官方 dmg（`https://download.documentfoundation.org/libreoffice/stable/<ver>/mac/aarch64/LibreOffice_<ver>_MacOS_aarch64.dmg`，约 300MB）→ `hdiutil attach -nobrowse` → `cp -R` 到工具目录 → `hdiutil detach`。`curl -sI` 的 content-length 可校验下载完整性。
6. 快速判断结构：`zipfile` 读 `word/document.xml`，看 `<w:tbl>` 数量与 `<w:tab/>` —— 封面表格若靠空格对齐，不同字体度量下都会崩，这是文档本身的问题，不是渲染器。

## 多份文档/截图整齐拼图（用户要「并排拼在一起」时）

用户说「把这 N 份模板的首页并排拼成一张图」「整整齐齐拼图」时，这是**形态 3 的拼版**，不是设计卡：

> 直接跑 `scripts/doc_pages_grid.py`（PDF 或 PNG 列表 → 网格图，支持 `--trim` 裁白边、`--canvas 3:4|fit`、`--single` 单页铺满、`--ratio` 锁死卡片比例）：
> ```bash
> env -u PYTHONPATH /usr/bin/python3 scripts/doc_pages_grid.py --pdf a.pdf --pages 2-5 \
>     --cols 2 --canvas 3:4 --trim --ratio 0.68 --out out.png
> ```

- **「整整齐齐拼图」＝一个装饰都不加**：不要衬板、投影、旋转、编号标签、kicker、logo、色块。用户会直接打回「设计感太重了，就整整齐齐拼图给我」。极简白底 + 均匀间距就是他要的成品。
- **但用户要「密集 / 有收获感 / 收集感」是另一条口径**：这时要加顶部标题条、把空格用**真实正文页**填满——留白在这类图里就是缺陷，用户要的是“满”。**绝不要用自制数据块（「248 页 · 57 章」）或四本书封面合图去补空格**，用户会直接打回「莫名其妙来了一页 248 页的页面很奇怪」「封面合集也不对」：这类图的说服力来自每一格都是书里真有的页。体量想表达就写进标题条文字。两种口径先分清再动手。完整配方（目录页定位、九宫格与页图同宽、`get_drawings()` 挑图表密集页、像素级对称验收）见 `references/dense-page-grid.md`。
- **用 PIL 直接网格拼，不要绕 HTML + Chrome**：读图 → `resize((CARD_W, CARD_H), Image.LANCZOS)` → 按 `(COLS, ROWS)` 粘贴。HTML 方案要多一轮 headless 截图且容易出现半像素错位，纯拼图没有任何理由走它。
- **1px 极淡描边是必要的**：白底页粘在白画布上，留白多的封面版会看不出边界。`ImageDraw.rectangle(outline=(226,232,240))` 不算设计。
- **算术先算再动手**：`CARD_W = (1080 - 2*MARGIN - (COLS-1)*GAP) // COLS`，`CARD_H = CARD_W * 页高/页宽`。实测 1080 宽 5 列、MARGIN=22、GAP=14 → 卡片 196×277，两行网格总高 568。
- **A4 页放不进 3:4 画布，先算清楚再决定交什么**：卡片比例锁死（A4 = 0.707），列数决定卡宽、卡宽决定行高，所以 3:4 里**永远凑不出整数填满**，只能选“留白多”还是“张数少”。实测 1080×1440、MARGIN=20、GAP=14：

  | 张数 | 网格 | 卡宽 | 占高 |
  |---|---|---|---|
  | 10 | 5×2 | 196 | 45% |
  | 12 | 4×3 | 249 | 75% |
  | 9 | 3×3 | 323 | 97% |

  用户问“10 张排不下能排几张”时直接给这张表：想饱满就 **9 张（3×3）或 12 张（4×3）**，10 张只能 5×2 且上下各空一大块。交图时默认给“紧贴内容的横版”（画布高 = 网格高 + 2×MARGIN）+ 一张 3:4 版并说明留白原因，不要只交一张让用户自己猜。
- **按宽度算完必须再按高度反算一次**：`cw_h = (H - 2*margin - (rows-1)*gap) / (页高比 * rows)`，取 `cw = min(cw_w, cw_h)`。只按宽度算，3×3 会得到 337px 卡宽、三行 1459px 直接溢出画布被裁。加一行 `assert grid_h <= H - 2*margin` 兜底。
- **用户要“文字占版面大一些”＝裁掉纸张白边**，不是放大画布。按渲染图的非白像素包围盒裁：`mask = gray < 246; rows/cols = np.where(mask.any(axis=...))[0]`，外扩 10px 保护边。A4 页实测横向利用率 76%、纵向 79%，裁完文字面积约放大 1.65 倍。
- **裁边后各页比例会不一致（封面页可能 1.11，正文页 0.66-0.68），对齐必须用“补白”不是“缩小”**：先取各页裁后宽高比的中位数作为统一比例，比它宽的上下补白、比它窄的左右补白（用画布底色填），再统一 `resize` 到格子尺寸。用 `min(cw/w, ch/h)` 缩放（contain）会让内容少的封面页整块明显偏小，用户一眼看出“四格大小不一致”。
- **含封面的四页永远比纯正文四页空**：封面本质只有标题+题目。同一套模板出两张——`p1-p4`（含封面）和 `p2-p5`（纯正文）——让用户挑，主推纯正文版。
- 交付前必查：每页四边完整未裁切（`paste` 坐标 + 卡片尺寸对得上即成立）、间距一致、无倾斜。

- **「左上角必须是第 1 页」＝从左上第一格顺序填充**：页数少时用 **2 列 1 行**，别用 1 列 2 行居中——格子水平居中后左上角是空白，用户会当场指出「左上角不是第一页」。
- **格子尺寸写死，别让它随每套模板的中位比例浮动**：让卡片比例跟着内容走，同一批图版式就各不相同（实测出现过 513×190 与 513×718 两种卡片并存）。
- **单套内容少的模板（大纲版/框架版）只放第 1 页、等比铺满整张画布**：`k=min((W-2m)/w,(H-2m)/h)`。这类文档常只有 2 页且第 2 页只剩小半屏，双页拼图右格必然大片留白，用户会要求改成单页铺满。
- **交付自检用程序，不靠肉眼**：算每格「墨占比」+ 内容 bbox 四边留白，一次查出「某格几乎空白」和「页被裁掉一截」；vision 会把补白读成「这格更小」，对四格是否等大经常判错。

### 改 docx 内容后再出图（年份、列宽这类修正）

用户看图发现错处时说「文档和图片都要改」＝**原始 .docx 也要改**，不能只改图。

1. **先备份**：`shutil.copy2` 到同级 `_备份_改年份前/`，交付时把备份路径报出来。
2. **只改 `w:t` 文本节点、只做精确整串匹配**：`for t in root.iter(wname("t")): t.text = t.text.replace("（2025版）", "（2026版）")`。**绝不全局 replace `2025`**——参考文献的出版年份（`2025, 104(11)`）是真实数据，改了就是造假；同理别动 `w:id`/样式里的数字。
3. **改完重写 zip 时逐条复制其余部件**，只替换 `word/document.xml`，写临时文件再 `os.replace` 回原路径（原地改会把文档留在半成品状态）。
4. **改完必须重渲染再出图**：`soffice --headless --convert-to pdf` 覆盖同名 PDF → 重新拼图，否则图片还是旧内容。
5. **表格左栏目名列宽得离谱（近 50:50）是 docx 自身的 bug，不是渲染器**：`<w:tblGrid>` 里 `gridCol` 写成 `100/100`（各 50%），而单元格 `<w:tcW>` 其实是 `2200/6826`（24:76），又缺 `<w:tblLayout w:type="fixed"/>`，渲染器就按 tblGrid 均分。修法：把 `w:gridCol@w` 改成与首行各 `tcW` 一致，并给 `tblPr` 追加 `tblLayout type=fixed`（注意 OOXML 里它要排在 `tblBorders` 之后）。
6. **先扫再改，别整批套用**：正则取每份 docx 的 `<w:tblGrid>` 中 `gridCol` 宽度与占比，就能看出哪几份中招（同批里常常只有一两份是 100/100，其余是 1100/1900 这类正常多列）。

## 验证（交付前必做）

1. 打印截图前后 `scrollHeight`/`scrollWidth` 对比：高度已展开且**宽度未变宽**。
2. `page.screenshot` 后检查产物大小（2x 长图通常数 MB；只有几百 KB 且高度≈视口 → 多半截断了）。
3. 用 vision 检查长图：顶部/底部都有内容、中间无空白条带/断裂/重复、**右侧无大片空白**。只看 body 高度就对截图完整性下结论是错的——必须确认无内部滚动容器，且宽度无撑宽。

## PDF 原样拼接长图（素材场景 — 用户纠正过）

用户说「把 PDF 拼成一张长图/图片」时，**默认 = 把 PDF 每页渲染后纵向拼接成一张图**，不要重新设计成知识卡片/信息图（2026-08 用户明确纠正：只想要原页拼接；先给原样结果，用户要设计版再另做）。

直接复用脚本：`scripts/pdf_to_long_image.py`（PyMuPDF 渲染 ~180 DPI + PIL 纵向拼接）。

⚠️ **本机坑**：terminal 会话全局 PYTHONPATH 指向 hermes venv（py3.11 site-packages），直接跑 `/usr/bin/python3` 或 `python3` 会加载 venv 里 3.11 编译的 PIL，报 `ImportError: cannot import name '_imaging'`。必须用：
```bash
env -u PYTHONPATH /usr/bin/python3 scripts/pdf_to_long_image.py in.pdf out.png 2.5
```
系统 Python 3.9 自带 fitz + PIL，清掉 PYTHONPATH 即可正常 import。

## 环境要点

- 系统 Chrome 路径：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`（macOS）。Playwright 自带 chromium 版本若缺失会报 `Executable doesn't exist at ~/Library/Caches/ms-playwright/...`，此时显式传 `executable_path` 指向系统 Chrome 即可，无需 `playwright install`。
- 中文/特殊字符文件名：脚本里直接写绝对路径字符串，避免 shell 转义问题。
- 输出建议放用户 Downloads 目录，文件名用「原标题_长图.png」。
- 完整可改脚本：`scripts/html_to_image.py`（含宽度断言防撑宽回归）；`scripts/marker_highlight.py`（截图逐行荧光笔高亮，输入 `[{y,x1,x2}]` JSON）。
