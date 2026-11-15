# 目录排版与 PDF 跳转

成书后期的两件事：把 A4 目录排成不空不碎的双栏，以及让目录条能点、书签能到节。

## 一、双栏装箱（不要用 CSS column-count）

CSS 多栏的分页断点由浏览器决定：篇标题落到栏底会把整段推到下一页，前一页下半留半页空白，末页只剩二十行。改用**先算后写**——按条目重量分配好栏，输出静态 HTML，浏览器只负责渲染。

### 权重

| 类型 | 权重 | 说明 |
|---|---|---|
| 篇（黑底横条） | 2.0 | 含 padding/margin 后约为节的两倍高 |
| 章（左竖线粗体） | 1.7 | |
| 节（编号） | 1.0 | 基准 |
| 子标题 | 0.92 | 略小于节 |

权重按**渲染后的实际高度**标定。第一版给的是 3.0 / 2.35（凭 padding 累加估的），结果前几栏分得太少、后栏溢出，改成 2.0 / 1.7 才平。改字号后必须重新标定，否则分配全乱。

### 容量公式（这里有一个死循环陷阱）

```python
total = sum(W[k] for k, _ in flat)
HEAD  = 2.8                      # 首页表头占高（单位同权重）
n_cols = 4                       # 2 页 × 2 栏
per_col = (total + HEAD) / n_cols   # ← 必须把 HEAD 加进分子
caps = [per_col] * n_cols
caps[0] = per_col - HEAD            # 首页第一栏让出表头
```

写成 `per_col = total / n_cols` 再让 `caps[0] -= HEAD`，则 `sum(caps) = total - HEAD < total`，`while sum(caps) < total: n_cols += 2` 永远不收敛——脚本挂死到一个 300 秒超时，没有任何报错。

### 防孤立标题

```python
for i in range(n_cols - 1):          # 末栏不处理
    while cols[i] and cols[i][-1][0] in ("part", "ch") and len(cols[i]) > 1:
        cols[i + 1].insert(0, cols[i].pop())
```

循环上界写 `n_cols - 1`。写成 `n_cols` 并在末栏 `cols.append([last])` 会无限增长，浏览器渲染直接卡死。

### 防孤尾栏（末页只剩一条）

加权装箱最后常剩一两条落进新栏，于是末页只有一行、其余全白——用户会原话抱怨「最后一部分直接新开了一页，只在开头有一点」。光靠调权重消不掉，装箱收尾时强制合并：

```python
while len(cols) >= 2 and sum(W[x[0]] for x in cols[-1]) < 6:
    cols[-2].extend(cols.pop())
```

阈值 6 ≈ 五六个节，取「明显撑不满一页」的量级即可。并进去会让前一栏变高，所以合并前那一栏的实测填充率要留出余量（<80%）；已经 88% 还并，内容会溢出到下一页。

### 权重标定：扫几组、量填充率、取最优

权重不能一次猜准（篇/章的实际渲染高度随 padding 与字号浮动）。字号一定，跑 2–3 组权重，每组渲染后测左右填充率，选「两页都在 78–88% 且左右差最小」的那组：

```bash
for w in "1.5 1.45" "1.7 1.55" "1.9 1.65"; do
  set -- $w   # 改 make_toc.py 里的 W = {"part": $1, "ch": $2, "sec": 1.0}
  # 生成 → 渲染 → 用下面的校验脚本打印 p1/p2 的 L/R%
done
```

实测 1.5/1.45 与 1.7/1.55 结果几乎相同（说明该段是平台区），1.9/1.65 左右差最小。每组都只差几百分点时，选差距最小的，别继续调。

### 版面参数（实测两页填满 85%，左右栏差 <1%）

```css
@page { size:A4; margin:13mm 12mm; }
.head h1      { font-size:20pt; letter-spacing:3pt; }
.head .meta   { font-size:8.6pt; }
.part  { font-size:11pt; padding:1.5mm 2.6mm; margin:3mm 0 1.8mm; }
.ch    { font-size:10pt; margin:2.4mm 0 1mm; border-left:2.2pt solid #2f5f8f; }
.sec   { font-size:8.9pt; margin:1.1mm 0 0.4mm; line-height:1.35; }
.sub   { font-size:8.1pt; margin:0 0 0.3mm 3.6mm; line-height:1.32; }
.cols  { display:flex; gap:6.5mm; align-items:flex-start; }
```

首页表头要**横跨两栏**：`.page` 是纵向流，表头 div 在前、`.cols`（flex row）在后。把表头塞进第一栏会让两栏起点不齐。

### 校验：测，不靠看

```python
import pymupdf
d = pymupdf.open("/tmp/toc.pdf")
for i, page in enumerate(d, 1):
    w, h = page.rect.width, page.rect.height
    L = R = 0
    for b in page.get_text("blocks"):
        if b[0] < w/2 - 6:  L = max(L, b[3])
        elif b[0] > w/2 + 6: R = max(R, b[3])
    print(f"p{i}: 左 {L/h*100:.1f}%  右 {R/h*100:.1f}%")
```

用 `max(b[3])` 而不是 block 数量：数量对不代表高度对。健康区间 80–90%，左右差 <2%。低于 70% 说明字号还有放大空间（字小反而更该放大，别用行距去凑）。

vision 看图会误判「左栏下半空着」——它把左栏内容结束当成了栏短，实际两栏底部是齐的。以这个测量为准。

## 二、目录可点 + 书签到节

### 标签收集

解析章节 md 时按行首标记记层级：`# `→L1（篇）、`## `→L2（章）、`### `→L3（节）。**章数统计要排除非章级 H2**：「全书结语」「本篇小结」「前言」「附录」「后记」都是 `##`，按 `##` 全计数会多算（实测 15 章算成 19 章，页头写错、用户一翻就发现）。判据是标题含这些词就只进目录、不进计数。

**篇标题渲染要剥掉自带编号**。md 的 H1 通常已写成 `# 第一篇 先搞清楚：……`，渲染时若再加一个「第一篇」标签，出来就是「第一篇 第一篇 先搞清楚」。两种解法：正则剥掉前缀 `re.sub(r"^第[一二三四五六七八九十]+篇\s*", "", title)`，或标签位改印 `PART 1`。后者更清楚，也顺手给了英文视觉层次。

### 定位与写书签

**目录页数不能写死。** 目录从 6 页压成 2 页后，加链接脚本里遗留的 `N_TOC = 6` 会让 `body_start` 偏移四页，封面/目录页被当成正文搜索，书签全指错位置且不报错。从书签表反推：

```python
book   = doc.get_toc()
_toc   = next(p for l, t, p in book if t == "目录")
_first = next(p for l, t, p in book if l == 1 and t.startswith("第一篇"))
body_start = _first - 1          # 0-based
N_TOC      = body_start - 1
```

合并脚本改了目录页数、加链接脚本忘了跟，是这套流水线最常见的错位来源。

```python
doc = pymupdf.open(pdf)
for lvl, text in heads:
    key = text[:14]
    for i in range(body_start, doc.page_count):
        if doc[i].search_for(key):
            loc[text] = i
            break
doc.set_toc([[1,"封面",1], [1,"目录",2]] + [[lvl, t, loc[t]+1] for lvl,t in heads if t in loc] + [[1,"封底",doc.page_count]])
```

`search_for` 用前 14 字就够（标题唯一），全串匹配反而因断行失败。

### 目录条目加链接

```python
for pi in range(n_cover, body_start):     # 只扫目录页
    page = doc[pi]
    for lvl, text in heads:
        target = loc.get(text)
        if target is None: continue
        for r in page.search_for(text[:12]):
            page.insert_link({"kind": pymupdf.LINK_GOTO, "from": r,
                              "page": target, "to": pymupdf.Point(0, 0)})
            break
doc.saveIncr()
```

`"to": Point(0,0)` 落到目标页顶端；`zoom` 参数可省。

### 「不能点 → 再跑一次」是错的：insert_link 不幂等

`insert_link` 是**追加**，同一个脚本跑两遍，每个条目就有两条重叠注解（105 条变 210 条，功能上看不出来，但页数/文件大小悄悄变、日后无法区分真假）。三个必守：

1. **链接步骤只能跑一次**。写进 `build.sh` 就不要再手动补跑；实测「build 里有一次 + 手敲一次」直接翻倍。要么把这一步从 build.sh 摘出去单独跑，要么只在 build.sh 里跑。
2. **验证判据是「等于预期条数」**，不是「大于 0」：`sum(1 for pi in range(1,3) for l in doc[pi].get_links() if l["kind"] == pymupdf.LINK_GOTO)` 应等于标题数，翻倍就是跑了两次。
3. **封面这类 `<a href>` 链接先查再补**。Chrome `--print-to-pdf` 已经把 `<a href>` 转成原生 link annotation，再手动 `insert_link(LINK_URI)` 就重复。正确顺序是先 `[l["uri"] for l in doc[0].get_links() if l["kind"] == pymupdf.LINK_URI]`，为空才补；读到 2 条且矩形几乎重合，就是「Chrome 一条 + 你加一条」。

### 核对（必做）

数量对不等于跳对——同一个短前缀可能在目录页命中多处，全连到同一目标。逐条回读：

```python
ok = bad = 0
for pi in range(1, 3):
    page = doc[pi]
    for l in page.get_links():
        if l["kind"] != pymupdf.LINK_GOTO: continue
        label = page.get_textbox(l["from"]).strip()
        tgt = doc[l["page"]].get_text().replace(" ", "")
        if label[:10].replace(" ", "") in tgt: ok += 1
        else: bad += 1
print(ok, bad)      # 期望 bad == 0
```

**不要用「目标页是否含『第/章/篇』」当判据**——大多数节标题页不含这些字，会报出一堆假可疑（实测 135 个链接误报 83 个）。判据只能是「目标页文本包含条目自身的文字」。

## 四、四种会说谎的中间信号

- **合并统计变好看**：字数/章数翻倍 = 把输出文件也读进去了，不是内容写多了。
- **`grep -c ERROR` 非零**：Chrome headless 在 macOS 上固定刷 `task_policy_set` / `CVDisplayLinkCreateWithCGDisplay failed`，是噪声；判成功看 `N bytes written` 和产物页数。
- **vision 说栏空**：目视会误判双栏底部对齐，以 `max(b[3])` 测量为准。
- **grep 成品 PDF 说“没改到”**：`get_text()` 按版面断行，一个词会被拆到两行（“北京大学医学部” → “北京大\n学医学部”），`t.count("北京大学医学部")` 返回 0 并不代表没改。核验时先 `t.replace("\n","")`，或只查 3–5 字的短片段（“医学部”、“邢晓辉”）。同一句话里数字命中、词不命中，基本就是断行而非漏改。
