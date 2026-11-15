# 出书环节技术细节

合并 md → 正文 PDF → 目录 → 合并 → 书签跳转 → 体检。

本文件只讲出书，不讲写作。写作规矩见 SKILL.md 阶段 10，质量闸门见 `quality-gates.md`。

---

## 分页规则

```
篇标题（h1） → 与本篇第一章同页
章标题（h2） → 每章另起一页
```

篇标题单独占一页，全页只有一行字、下半页空着，难看。篇标题下面直接接本篇章标题。

「紧凑」这个词用户只用来形容**目录**，不形容正文。正文要松，每章另起页。

`md2pdf.py` 用 `H2_BREAK=1` 环境变量开启，默认关闭（避免影响已出书的版式）：

```python
if os.environ.get("H2_BREAK"):
    CSS += """
h1 { page-break-before: always; break-before: page; }
h1:first-of-type { page-break-before: auto; break-before: auto; }
h2 { page-break-before: always; break-before: page; margin-top: 0; }
h1 + h2 { page-break-before: avoid; break-before: avoid; margin-top: 20pt; }
"""
```

第四行是关键。`h1 + h2` 选中的是紧跟篇标题的那个章，只取消它的分页；少了这行，篇标题仍单独占页。

### 篇标题下不要写导语

篇标题和本篇章标题之间不能插东西：不写导语段落，也不放 `---` 分隔线。

两个后果：导语会把章标题挤到下一页，篇标题又变成单独占一页（用户明确嫌过这种版面）；`---` 会生成 `<hr>`，`h1 + h2` 失去相邻关系，分页规则直接失效。

写完 md 先自查：篇标题下一行必须就是 `## 第X章`。

```python
t = re.sub(r'(^# 第[一-龥]+篇 [^\n]+\n)\n[^\n#][^\n]*\n\n---\n', r'\1\n', t, flags=re.M)
```

删导语后页数明显下降（实测 60 → 55 页，五个篇各省一页）。

效果核验：查各章起始页，间隔应 ≥ 2 页。

```python
chs = [(t, pg) for lv, t, pg in doc.get_toc() if lv == 2]
gaps = [chs[i+1][1] - chs[i][1] for i in range(len(chs)-1)]
assert all(g >= 2 for g in gaps), '有章没另起页'
```

---

## 目录：Python 加权装箱

不用 CSS 多栏。`column-count` 与 `break-inside` / `break-after` 在分页边界互相冲突，实测同一份内容会抖成 19 行 / 91 行 / 54 行 / 23 行。JS 精确定高在分页边界不可靠，还容易写成死循环。

做法：Python 侧算权重 → 吐出静态 HTML 多栏。

### 容量判断用条数，不用权重和

```python
W = {"part": 1.9, "ch": 1.65, "sec": 1.0}
HEAD = 2.8
n_cols = 2 if len(entries) <= 95 else 4      # 按条数
per_col = (sum(W[k] for k, _ in entries) + HEAD) / n_cols
```

用 `total + HEAD <= 90` 判断会误判：66 节的权重和是 88.2，卡在线上，被分进 4 栏，结果第 2 页只有 6% 内容。权重是相对值，不对应实际行高，判断容量必须用条数。

### 均衡靠视觉行高均分，不靠权重累计

累计权重装箱（装满一栏再换下一栏）会让前几栏挤满、后几栏留空。实测 110 条分 4 栏时，左栏只到第四章开头，右栏排到第八章，两栏差一半。

改成按相对行高分：

```python
H = {"part": 1.55, "ch": 1.45, "sec": 1.0}
per = (sum(H[k] for k, _ in entries) + 1.6) / n_cols   # 1.6 是页头
cols, cur, acc = [], [], 1.6
for item in entries:
    h = H[item[0]]
    if cur and acc + h > per + 0.55:      # 0.55 是容差
        cols.append(cur); cur, acc = [], 0.0
    cur.append(item); acc += h
```

改完两栏填充率接近（实测左右各 78%）。条目多、页数多时字号不用压缩，直接放大到每栏 78-85% 更匀称。

### 两条收尾规则

```python
# 1. 末栏太空就并回前一栏
while len(cols) >= 2 and sum(W[x[0]] for x in cols[-1]) < 6:
    cols[-2].extend(cols.pop())

# 2. 栏末不能是篇/章标题，否则标题孤悬栏底
for i in range(len(cols) - 1):
    while len(cols[i]) > 1 and cols[i][-1][0] in ("part", "ch"):
        cols[i+1].insert(0, cols[i].pop())
```

### 篇号必须用全局计数器

```python
counter = {"pi": 0}          # 在 render 外

def render(col):
    for k, t in col:
        if k == "part":
            counter["pi"] += 1
            ip = counter["pi"]              # 先赋值
            out.append(f'<span>PART {ip}</span>')
```

计数器写在 `render()` 里，每栏都从 PART 1 重新数，第三篇会显示成 PART 1。

### 压进一页的实测参数

66 节 / 10 章 / 3 篇，从 2 页压到 1 页的收敛过程：

| 项 | 起始 | 终点 |
|---|---|---|
| part | 14pt / margin 4.6-2.6mm | 12pt / 3.4-2mm |
| ch | 12.5pt / 3.5-1.4mm | 9.6pt / 2-0.8mm |
| sec | 11.4pt / 1.8-0.7mm | 8.6pt / 0.7-0.25mm |

每轮改完必须重新量两栏实际填充率（`max(block[3]) / page_height`），目标左 85% 上下、右 90% 上下。只缩字号不看填充率，会出现「看着小了但还是溢出」。

---

## 书签与跳转

### 层级不能跳级

PDF 书签要求逐级递进。某个篇标题定位失败时，书签会从 L1 直跳 L3，`set_toc` 抛 `bad hierarchy level in row 2`，整个 PDF 打不开书签面板。

```python
LVL = {"part": 1, "ch": 2, "sec": 3}
cur_max = 1
for kind, text in entries:
    if text not in loc:          # 定位失败就跳过，不要塞空位
        continue
    lvl = min(LVL[kind], cur_max + 1)
    toc.append([lvl, text, loc[text] + 1])
    cur_max = lvl
```

注意 `entries` 存的是 `(kind字符串, text)`，不是 `(层级数字, text)`。写成 `min(lvl, cur_max+1)` 而 `lvl` 是字符串，会报类型错误。

### 跳转验证要反查目标页

不能只数链接个数。逐个取链接覆盖的文字，到目标页文本里找，确认对得上：

```python
for pi in range(toc_start, toc_end):
    page = doc[pi]
    for l in page.get_links():
        if l["kind"] != pymupdf.LINK_GOTO: continue
        label = page.get_textbox(l["from"]).strip()[:10]
        target = re.sub(r"\s", "", doc[l["page"]].get_text())
        assert re.sub(r"\s", "", label) in target, f"错跳 p{pi+1} → p{l['page']+1}"
```

**`label` 也要去空白再比。** 标题在 PDF 里可能被换行拆成两段，`"3.3 八步里前三步"` 实际取到的是 `"3.3 八步里前三\n步"`，不去空白就匹配不上，误报错跳。

### 封面链接不要手动加

HTML 里写 `<a href>`，Chrome 打印成 PDF 时**自动生成 LINK_URI 注解**。再手动 `insert_link` 就是两条。核对时数一下：封面 URI 应该是 1 个。

---

## 改了正文必须重跑目录

目录是从 md 解析出来的静态 HTML，不是实时渲染。改了节标题、加了内容、动过结构，都要重跑 toc：

```bash
python build.py combine      # 合并 md
python md2pdf.py ...          # 正文
# Chrome 打印
python build.py toc          # ← 这步最容易漏
# Chrome 打印
python build.py merge
python build.py links
```

漏了这步的表现：PDF 目录里还是旧标题，跳转数少 1 个，反查报错跳。看目录文字最快：

```python
[x for x in doc[1].get_text().splitlines() if '3.3' in x]
```

---

## 改名要同步五处

书改名时，改封面标题只完成了一半：

| 位置 | 文件 |
|---|---|
| 封面主标题 | `make_cover_XX.py` 的 `<h1 class="cv-title">` |
| 封面副标题行 | 同一个文件里的 `cv-title-sub`（书名为「主标——副标」时） |
| 输出路径 | `build_bookXX.py` 的 `PDF_OUT` |
| 体检脚本 | `check_bookXX.py` 的 `P` |
| 送审/读取清单 | `make_review_packXX.py` 的 `OUT` 与 `ITEMS`（若还在用） |

全改完再重建，并删掉旧文件名的 PDF——否则 `00_成书/` 里会同时躺着新旧两份，审方和自己下一次都会拿错。

批量替换：

```bash
sed -i '' 's/旧书名/新书名/g' build_bookXX.py check_bookXX.py make_cover_XX.py
```

### 改完先看成品文件名落在哪

不是所有 build 脚本都输出到项目 `00_成书/`。旧脚本（如 `merge_sskt.py`）可能直接写到桌面，重建后归档目录里还是旧版，时间戳不一样。

```bash
ls -lh "<项目>/00_成书/" "$HOME/Desktop/"*书名* 2>/dev/null
```

两边都有就 `cp` 回项目，再确认 `00_成书/` 只剩一份。

### 书名为「主标——副标」时的封面写法

主标题保持原有两行大字，副标题另起一行小字号，不要塞进 `<h1>` 里（会把主标题挤变小）：

```html
<h1 class="cv-title">放养硕博<br>自救指南</h1>
<div class="cv-title-sub">——从起步到发表</div>
```

```css
.cv-title-sub { margin-top:4mm; font-family:"Songti SC"; font-size:20pt;
                font-weight:400; letter-spacing:1.5pt; color:#3c4a58; }
```

20pt 约为 46pt 主标题的 43%，层级介于主标与英文副标之间。英文副标顺势下移 1mm 即可，不挤。

**加了副标题就要查下方说明行是否重复。** 原来的 `cv-sub` 若写着「从起步到发表 · 面向硕士与博士研究生」，会把副标再说一遍，删成「面向硕士与博士研究生」。

---

## 从旧脚本派生新书脚本：先清硬编码路径

复制上一本的 build 脚本改书名，最容易漏的是**临时文件路径**和**篇名**。

实测：`build_book06.py` 从 `build_book03.py` 派生，`merge` 里还留着 `/tmp/book03_body.pdf`，结果生成的 PDF 装的是**上一本的正文**，页数和书签看着都正常，只有翻内容才能发现。

派生后先全文搜一遍：

```bash
grep -n "book0[0-9]\|/tmp/\|第.篇 \|PDF_OUT" build_bookXX.py
```

必改清单：

| 位置 | 改什么 |
|---|---|
| `BOOK` / `PDF_OUT` | 本项目路径与书名 |
| `FILES` | 本篇章 md 列表 |
| merge 里 `/tmp/book0X_cover.pdf` | 换成 bookXX |
| merge 里 `/tmp/book0X_toc.pdf` | 同上 |
| merge 里 `/tmp/book0X_body.pdf` | 同上 |
| merge 里 `bk.append([1, "第一篇 …"])` | 本篇首章标题 |

**验证方法：出书后先看正文首章那一页的文字**，确认是本项目内容，再继续做书签。不先验这一步，后面书签定位会全部失败（`定位 0/110`），而错误信息看不出根因。


---

## 成品体检

一条命令跑完，全 ✓ 才算过：

```bash
.venv/bin/python check_book.py 00_成书/xxx.pdf
```

查这几项：

1. 页数 / 书签数
2. 目录跳转数 + 逐个反查 0 错跳
3. 封面 URI = 1 个，指向正确
4. 质量闸门（品牌痕迹 / AI 表达 / 提示性冒号 / 命令式记住）
5. 审稿整改项是否都落地
6. 各章起始页与间隔（每章独立成页）

**所有文本比对先去空白**：`re.sub(r"\s", "", text)`。PDF 提取会按版面断行，`"共同主要终点"` 可能变成 `"共同主要\n终点"`，用 `in` 判断就查不到，误以为改动没生效。
