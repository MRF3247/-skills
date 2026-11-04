# 论文速读卡详规（三线表 1080×1440）

配 `scripts/compose_paper_card.py` 使用。SKILL.md 里是口径，这里是可以照抄的几何、命令与验收。

## 1. 调用模板

```bash
python3 <skill>/scripts/compose_paper_card.py --out card.png \
  --section Abstract --section-cn 摘要 \
  --paper-title "<中文译名>" --paper-title-en "<英文原标题>" \
  --block "Background · 背景|<英文段>|<中文段>|" \
  --block "Findings · 结果|<英文段>|<中文段>|/tmp/shots/fig_x.png" \
  --block "PAGEBREAK|||" \
  --block "Methods · 方法|<英文段>|<中文段>|" \
  --block "Interpretation · 解读|<英文段>|<中文段>|" \
  --source "PubMed · The Lancet · <日期> · PMID <pmid> · DOI <doi>" \
  --fs-en 19 --fs-cn 22 --fs-t-en 21 --fs-t-cn 44 --fs-sec 36
# 输出 card-1.png … card-N.png，stdout 每个文件带 page n/N 与 y_end
# 可选（用户点名才用）：--block "Bottom line · 一句话总结||<中文>|"、"Limitation · 局限||<中文>|"、
#   "Keywords · 关键词||<中文>|"、--page-tags "① 结论先行|② 方法与解读"
```

出完图直接落到选题库子文档：`docs +fetch --doc <token> --doc-format xml` 取现稿 → 在封面 grid 之后插一节（`<h1>论文速读卡：Abstract 摘要 · 中英对照</h1>` + `<blockquote>` 写版式与“配图非原图” → 两列 `<grid>`，每列 `width-ratio="0.5"` 放 `card-1.png`／`card-2.png`）→ `docs +update --command overwrite` → 回读核 `imgs` 计数与原节仍在。

> **回写前必须重新 fetch 当前 XML，不要复用上一轮缓存**：overwrite 是整篇替换，拿「插卡之前」抓的 XML 去覆盖，刚插进去的卡片图会被整段抹掉（实测 7 张图 → 5 张，且 `result: success` 不报错）。顺序固定：插卡 → fetch → 改正文 → **再 fetch** → 覆盖；每次覆盖后都回读 `imgs` 计数。

> **合规改写后位图文字不跟着变**：正文按合规意见改了标题/副标，封面上压的字是位图，不会自动同步；用 `add_cover_text.py` 重压一版（零算力），并在交付里说明「图上的字需重压，已给新版/要不要重压」。
```

`--block` 四段：`子标题|英文|中文|图片路径`（第四段可省；只写中文的块英文段留空）。子标题统一写「英文 · 中文」，中间是空格+间隔号+空格。

## 2. 几何（改字号先看这张表）

| 元素 | 取值 |
|---|---|
| 画布 / 版心 | 1080×1440；`X0=52, X1=1028`（版心 976） |
| 天头基线 `top` | 40 |
| logo | 高 34，右边缘贴 `X1` |
| 关键词 | 16–17px `MUTED(#7A8492)`，`y = top+34+8`，右对齐 |
| 中文标题 | 字号 `fs_t_cn`=44，heavy，品牌蓝，左对齐 `X0`，宽 `X1-X0-lw-40`，行高 1.30 |
| 英文标题 | 字号 `fs_t_en`=21，heavy，`(70,80,94)`，**整行宽** `X1-X0`，行高 1.40 |
| 天头下粗线 | 5px，`RULE(32,38,46)`，**仅 P1** |
| 章节标题 | `Abstract`（`fs_sec`=36 黑）+ 品牌蓝 `摘要`，同一行 |
| 栏目细线 | 1px，`(170,178,188)`，长 = 版心 × **0.42** |
| 正文 | 英文 `fs_en` 19–20 行高 1.46；中文 `fs_cn` 22–23 行高 1.50，左侧 4px 蓝竖条+20px 缩进 |
| 页脚 | 蓝条 66px 满宽，出处白字 + 页码 `n/m` |

**阶梯关系（不要破坏）**：中文标题 44 > 章节标题 36 > 子标题 > 正文；栏目细线比天头粗线**更细且更短**。

## 3. 默认页序：结论先行（用户定稿，覆盖摘要原顺序）

| 页 | 块序 |
|---|---|
| **P1** | `Background · 背景`（中文段末带一行方法注脚）→ `Findings · 结果`（配图） |
| **P2** | `Methods · 方法` → `Interpretation · 解读` |

- **为什么**：首页给核心数字（刷到即拿到结论）、有图更满；方法＋解读合起来正好铺满第二页。
- **方法注脚**：只一行、写在 Background 中文段末尾括号里（例「（3 期、开放标签、1:1 随机；主要终点为盲法独立评审的 PFS 与 OS）」），解决“P1 看到 HR 却不知道终点定义”。
- **只这四个块**：`--page-tags` 的「① 结论先行｜② 方法与解读」、`Bottom line · 一句话总结`、`Limitation · 局限`、`Keywords · 关键词` 全部试过并被用户删掉（「先这么跑着试试」）。脚本能力保留，默认不传；用户点名再加。
- **不要用补块来填空白**：改成两段后 P2 只剩 Methods＋Interpretation，正确处理是**竖向居中**（见 §4「竖向居中」），不是塞 Limitation/Keywords 回去。

## 4. 分页规则

- **强制断页**：`--block "PAGEBREAK|||"`，脚本见子标题等于 `PAGEBREAK` 就换页。结论先行的两页必须显式断，自动分页按高度算会把结论页拆散。
- **自动分页**：`n_pages = ceil(total_h / (avail*0.96))`，`target = total_h / n_pages`；`hsum+bh > avail` 或 `> target*1.06` 换页。
- **续页可用高度必须按本页实际表头重算**：`page_avail = (H - 脚注条 66 - 40) - 本页表头结束 y`。P1 有中英标题＋粗线、续页只有 logo，拿 P1 的 `avail` 摊余量会把续页空白算少（实测续页仍留 40% 空白）。
- 余量摊进段距上限 **150px**（原来 72px 铺不开）；`leftover > 40` 才摊。
- **竖向居中**：摊完段距还剩 `rest = leftover − extra*n_blocks`，`rest > 60` 时把 `rest//2` 加进起始 `y`，让上下留白对称。只有两三个块时不做这步，半页空白会全堆在底部。
- **续页不重画任何标题与线**，直接从下一个子标题开始。

## 5. 配图块（文字左、图右）

- 块内有图时：文字栏宽 = `X1-X0-图宽-28`，图右对齐 `X1`、与文字块顶部对齐，块高取文字与图的较大者。
- `fig_w` 默认 300（约 1/3 版心）。图再大就压正文行宽，用户会嫌“挤”。
- 一篇只需要 1–2 张图，放在**有数据的那个块**（通常是 Findings），不要每块都配。

## 6. 配图从哪来

1. **原文图（最优）**：先查 Europe PMC
   ```bash
   curl -s "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:<PMID>&resultType=core&format=json" \
     | python3 -c "import sys,json;r=json.load(sys.stdin)['resultList']['result'][0];print(r.get('isOpenAccess'),r.get('inPMC'),r.get('pmcid'))"
   ```
   `isOpenAccess: N` / 无 PMCID ⇒ 正文图基本拿不到（Lancet、Elsevier、NEJM 站点 `curl` 直接 403），不要反复试抓、也不要用别的文章的图凑。
2. **自绘数据图**：只用该文报告过的数字（比例、率、HR、亚组值），柱状/点图即可。**必须加脚注**「数据取自本文摘要；图为刀客轻研绘制」。不要画没有原文数据支撑的 KM 曲线。
3. **用户提供的 PDF/截图**：裁切后使用，crop 时保留图注。

交付时必须说明配图来源（原文图 / 自绘 / 用户提供）——取不到原文图就直说取不到。

## 7. 自绘图配方（matplotlib + 中文）

execute_code 的 kernel 可能没装 matplotlib；写成脚本用 terminal 的 `python3` 跑。**不注册中文字体必出豆腐块**：

```python
import matplotlib; matplotlib.use("Agg")
from matplotlib import font_manager
matplotlib.rcParams["font.family"] = "MiSans"
for f in ("/Users/Jin/Library/Fonts/MiSans-Medium.ttf",
          "/Users/Jin/Library/Fonts/MiSans-Regular.ttf"):
    try: font_manager.fontManager.addfont(f)
    except Exception: pass
matplotlib.rcParams["axes.unicode_minus"] = False
```

图表口径：`figsize=(4.0,3.1) dpi=200`（840×620，缩到 300px 宽仍清楚）；去 top/right spine、y 方向浅灰网格 `#E7EBF1`；品牌蓝 `#006EBB` 对浅灰 `#C9D2DE`；柱顶标数值；标题 11px、刻度 9px、脚注 7.5px。

## 8. 验收（逐条核，不要只看缩略图）

- [ ] P1：第一行中文标题在左、logo+关键词在右同一行；第二行英文标题整行且明显更小；再往下才是 `Abstract 摘要`
- [ ] P1：栏目细线 1px 且长度约 42% 版心，肉眼比天头粗线短；**页脚上方没有粗黑线**
- [ ] P2 起：只有右上 logo+关键词，**无标题、无「（续）」、无粗线**，直接从子标题开始
- [ ] 页序是结论先行：P1 只有 Background＋Findings（带图），P2 只有 Methods＋Interpretation
- [ ] 没有 `①/②` 页标签、没有 Bottom line／Limitation／Keywords（用户默认删掉了，除非他点名）
- [ ] 有图块：文字左、图右、互不重叠，图宽约 1/3 版心，自绘图带来源脚注「数据取自本文摘要；图为刀客轻研绘制」
- [ ] 页码 `n/N` 与出处白字落在蓝条内，`y_end` 未溢出（< 1440-66）
- [ ] 内容块竖向居中：上下留白大致对称，底部没有半页空白（有就说明没走「竖向居中」）
- [ ] 交付时说明配图来源（原文图／自绘／用户提供）；原文图取不到要直说
