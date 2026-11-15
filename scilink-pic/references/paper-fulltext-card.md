# 论文速读卡 · 全文中文译文版（N 页）

用户说「用论文速读卡的形式做，全文都用中文译文放进去」时走这条线。默认 2 页版（作者主张／临床问题＋摘要＋局限）在这条线里只当 P1 的骨架，后面按正文章节续页。

## 0. 素材（先核，再翻）

- 全文：`curl -sL -A "Mozilla/5.0" "https://doi.org/<DOI>"`（Ovid/LWW 的 `10.1097/…` 直接 200）。把 HTML 去标签后按行找章节名：`Introduction / Methods / Results / Discussion / References`，表格在 `<table>` 里、图注在 `Figure N` 附近。
- Europe PMC 返回空 `resultList` 不代表拿不到全文（新 DOI 常见）；**PDF 链接是伪 200**（回 HTML），别存。
- 原文图：HTML 里抓 `/image-api/imgsrv[^"' ]+`，`figure1..4` 各取 `width/1200.png` 下载 → 1200px 宽原图。用到的图在 caption 写「原文 Figure N｜说明」。
- 表格：原文 Table 1/2 只抄**点估计 + 关键列**（如 ASIR/ASMR/ASDR/死亡数），标题注明「原文 Table N，95% UI／CI 见原文」；**不做换算、不补缺失**。
- 明确不译的部分（参考文献、基金、数据可用性）在交付里说明一句，不要静默丢掉。

## 1. 页序（实测 7 页，按内容量增减）

| 页 | 放什么 |
|---|---|
| P1 | 徽标 + 中文标题（大字）/ 英文原标题（小字灰）+ 右上 logo 关键词 → 粗线 → 作者主张｜临床问题 两卡 → Abstract 摘要 → 背景／方法／结果／结论 四段全译 |
| P2 | 引言（3 段）+ 方法（数据来源／估算模型／SDI／风险因素／统计分析，各带小标题） |
| P3 | 结果·亚区层面（发病／死亡／DALY 三段）+ 原文 Figure 1 |
| P4 | 结果·国家层面 + 表 1（标化率、绝对数，中国行标黄）+ 表 2（EAPC） |
| P5 | 结果·经济水平/性别/年龄 + 风险归因 + 原文 Figure 3 |
| P6 | 结果·死亡数分解 + 原文 Figure 4 + 讨论前两段 |
| P7 | 讨论（风险因素／性别）+ 局限框（作者承认）+ 读者观察框（读者补充） |

续页天头只要「右上 logo + 那行关键词」，左侧空、不加粗线、不写「续」。

## 2. 排版键值（照抄）

- 字体 MiSans（`/Users/Jin/Library/Fonts/MiSans-*.ttf`，`@font-face` 五档），品牌蓝 `#006EBB`，蓝条页脚 `#004E86` 不用，页脚用品牌蓝 64px。
- `.sheet{width:1080px;height:1440px;overflow:hidden;padding:42px 52px 0}`；内容底线 **≤1354**（页脚 1376 上沿再留 22px）。
- 正文 `p`：19.5px / `line-height:1.72` / `text-align:justify`；段距 `calc(11px + var(--grow))`。
- 章节标题 `h3`：22px/800，中文 + `· English`（英文小号灰蓝）；小标题 `.sub` 17px 品牌蓝。
- 三线表：`thead th` 品牌蓝 800、上下 2px/1px 深灰；`tbody tr.hl` 浅蓝底加粗（用来标中国行/关键行）。
- 局限/读者观察框：浅蓝 `#F3F8FD` 圆角 8px，条目带品牌蓝圆点。

## 3. 自动分页（量一次、切一次、调两轮）

1. **探测页测量**：把每个块包进 `<div class="mi" data-k="i">` 放进一张 `height:auto` 的长 sheet，`document.fonts.ready` 后把每块高度写进 `data-mm`，用 `chrome --headless=new --dump-dom --force-device-scale-factor=1 --window-size=1080,20000` 读回来。
   - **必须 `.mi{display:flow-root}`**：不加时子元素 `margin-top` 会与包裹层折叠到外面，量出来的高度少 11–26px/块，一页十块就差 200px，排完必然溢出。
2. **分页规则**：段落是原子单位（每段单独一块，不要一段多块混装）；`h3/sub` 落页尾时整块下移，避免孤行标题；图放不下就**缩到本页余高**（宽 ≥560px）填页，而不是留半页白。
3. **不要用「收窄每页容量」去均分**（shrink）：先靠缩小容量看起来均分，但页数一旦多出一页，容量又变小 → 页数继续膨胀（实测一路到 11 页）。要么不 shrink，要么 shrink 只允许「页数不变」时才生效。
4. **余量摊成段距**（最后一公里）：逐页 `grow = clamp((1354 − content_bottom)/块数, 0, 15)`，写进 `--grow` 后重测；有图且仍空>120 的页先把图放大（+18%）再摊间距。溢出（content_bottom > 1376）时按 `grow + 负余量/块数` 回退，迭代 3–4 轮。
5. 验收：每页 content_bottom 落在 **1280–1350**（gap 13–79px 实测通过），且 P1 的 gap 最小也没关系。

## 4. 出图与落飞书

- 渲染：一次 `--window-size=1080,1440*N` + `--force-device-scale-factor=2`，再按 `i*2880` 裁页；每页 2160×2880。
- 逐页 `vision_analyze` 查：徽标/logo/关键词在位、图未裁、表头与数字对齐、两个框条目圆点对齐、无压页脚。
- 落飞书：7 张分两组 grid（4 栏 `width-ratio=0.25` + 3 栏 `0.333333`），第一组插 `--block-id 0`，第二组插在**第一组的 grid block id** 之后（`+fetch --detail with-ids` 取）；每张 `name` 编号打头、`caption` 写清这页讲什么 +（1080×1440）。
- 回读核对：`grid/column/img` 计数＝2/7/7，逐张 `width×height = 960×1280`。服务端会把 `src` 换成新 token 但一般保留 `width/height`，以回读为准。

## 5. 交付口径

报：页数、每页讲什么（表格列出）、译文范围（哪几节译了、哪几节没译）、图是不是原文图、哪些数字是换算而来（放在「读者观察」框里）、本地副本目录（`~/Downloads/<主题>_论文速读卡/`，文件名与文档内 `name` 一致）。
