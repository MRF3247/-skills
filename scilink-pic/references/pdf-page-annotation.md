# PDF 原件关键页抽取 + 红色下划线标注

政策/文件/指南类内容要「把附件里的重点截出来给读者看」时用这条路。

## 零、先判断：实质在哪一页

政策文件的正文页往往只有「现发布……请各培养单位加快推进实施」两三句，**实质全在附件**。用户会直接问「这个通知其实没什么明确信息，好像都在附件里」。所以：

1. 先逐页取首行定位章节，别从头往尾翻：
   ```python
   import fitz, re
   d = fitz.open('/tmp/doc.pdf')
   for i, p in enumerate(d):
       t = re.sub(r'\s+', ' ', p.get_text().strip())
       print(f'P{i+1:02d} | {t[:90]}')
   ```
2. 用二级标题正则扫全篇，确认每一块的范围：`re.finditer(r'（[一二三四五]）[^\n，。、（）]{2,12}', t)`
3. **顺手核一下附件之间的差异**（这份文件里博士版只有两种实践成果形式、硕士版有三种），差异本身就是可写的点，比通读正文有价值。

## 一、选页：挑「标题开头」的页，不挑续页

- 好页：以 `三、申请学位实践成果基本要求` 这类标题开头的页。
- 差页：以残表行（`逻辑结构与论证`）或半句（`有明确的临床医学应用价值`）开头的页——那是上一页的续页，截出来顶部就是残缺表格。
- 续页不得不用时，用标题坐标把顶部切掉（见第三节）。

## 二、渲染与裁边

```python
pix = d[n-1].get_pixmap(dpi=180)          # 180dpi 足够清晰，字不糊
pix.save(f'/tmp/p{n}.png')
```

裁边用「深色像素包围盒 + 留白」，不要拍脑袋写死页边距：

```python
from PIL import Image
import numpy as np
im = Image.open(f'/tmp/p{n}.png')
a = np.array(im.convert('L'))
rows = (a < 200).sum(1); cols = (a < 200).sum(0)
ys = [i for i, v in enumerate(rows) if v > 3]
xs = [i for i, v in enumerate(cols) if v > 3]
box = (max(0, xs[0]-25), max(0, ys[0]-30), min(im.width, xs[-1]+30), min(im.height, ys[-1]+30))
im.crop(box).save(f'/tmp/p{n}_c.png')
```

结果约 1080–1130 宽 × 1550–2050 高，单栏插进文档字仍然清楚。

## 三、续页切掉顶部残表

```python
r = p.search_for('三、申请学位实践成果基本要求')      # 或本页第一句正文
y = int(r[0].y0 * 180 / 72) - 14                      # pt → px，再上留 14px
im.crop((100, y, im.width-100, im.height-55))
```

`search_for` 返回 pt 坐标，`get_pixmap(dpi=180)` 的像素坐标是 `pt × 180 / 72`——**不换算会切错行**。

## 四、红色下划线标注（核心）

用 `draw_line` 在文字基线下方画粗线，**不要用 `add_underline_annot`**：annot 线宽默认 1pt，渲到 180dpi 后细得看不清，用户会说「不够醒目」。

```python
targets = {3: ['两者均可用于申请学位'], 7: ['三、申请学位实践成果基本要求']}
for pno, phrases in targets.items():
    page = d[pno-1]
    for ph in phrases:
        rs = page.search_for(ph)
        print(f'P{pno} hit={len(rs)} {ph}')          # 每次都打印命中数
        for r in rs:
            page.draw_line(fitz.Point(r.x0, r.y1+1.6),
                           fitz.Point(r.x1, r.y1+1.6),
                           color=(1, 0, 0), width=3.2)   # 纯红 + 3.2pt 才醒目
d.save('/tmp/doc_marked.pdf')      # 存副本，绝不覆盖原件
```

**命中 0 的处理**：
- 长句常跨行，`search_for` 整句归零 → **缩短到 8–12 字的关键词**（`案例分析报告应直接来源于临床医学专业实践领域的一手真实案例` → `案例分析报告应直接来源于`）。
- 表格里的文字命中率低（PDF 表格文字带制表符/分列），只能标最短的列名（`实践价值`），标不到整句就将就。
- 关键词太短会命中多处（`答辩` 在一页里命中 5 次），全部标上也合理——只要每处都确实相关；不相关就换成更长的串。

**划线数量报告**：跑完统计 `tot`，报告里写「共 N 处」，别只说「已标注」。

## 五、插进文档：一行分栏装全部图，不要散插、不要多行

用户口径：「这些截图要用分栏**装起来**，按照顺序放进分栏，而不是插入文中」，随后又强调「**是一行分栏里把所有图片按顺序排进去，只有一行分栏**」。先按单栏散插、或拆成 3 组两栏 grid，都会被返工。

**定稿形态：一个 `<grid>`、一行、N 个 `<column>` 横排**（封面 + 各附件页一起排，封面排第一）：

```xml
<grid>
  <column width-ratio="0.1429"><img src="<封面 tok>"/><p><b>封面</b><br/>一句话说明</p></column>
  <column width-ratio="0.1429"><img src="<tok1>"/><p><b>① 第3页</b><br/>这页说什么</p></column>
  <!-- 共 7 栏，width-ratio 合计≈1；每栏图 + 一行 caption -->
</grid>
```

- 7 栏时每栏只有版心 1/7，附件页正文小字**必须点开才能读**——这是用户明确接受的取舍，**不要因为「字小」擅自改回两栏**；但要在交付里点一句，把选择权交回。
- 换装法首选 **`block_replace`**：把一个已有的 `<img>` 块整块换成上面这段 `<grid>`，比「先删旧 grid 再 append」少一步、也不会打乱章节顺序。
- **`block_delete` 跨 grid 的范围会失败**：`--start-block-id <h2> --end-block-id <最后一个 img>` 若中间夹着 `<grid>`，命令回 FAIL。拆成多次：先删 h2 与其下 p（连续两块的 start/end），再**每个 grid 各删一次**（`--block-id <grid id>`）。
- 图片先 `media-upload` 拿 `file_token` 再写进 XML（`<img src="token">`）。
- 插完回读校验 `grid` / `column` / `img` 三个计数（7 张一行应为 1 / 7 / 7），并确认旧的散图 / 旧 grid 已删净（全文 `img` 计数等于应有的张数）。

「有几张出几张」是用户的原话——6 页以内都给，不要自己砍到 3 张。

## 四之二、按批注划「从某句到某句」的整段（跨行）

批注常写「这个范围内都划线」「整段都要划上」「把这句删掉、那整段划」，不是单个短语。做法是**逐行取 bbox、逐行画**，不要指望 `search_for` 一次命中跨行句：

```python
def line_rects(page, start_phrase, end_phrase=None):
    r0 = page.search_for(start_phrase)[0]
    hits1 = page.search_for(end_phrase) if end_phrase else [r0]
    after = [h for h in hits1 if h.y0 >= r0.y0 - 4]
    r1 = after[0] if after else hits1[-1]        # ★ 取第一个，不是最后一个
    lines = [(fitz.Rect(l['bbox'])) for b in page.get_text('dict')['blocks'] for l in b.get('lines', [])]
    picked = sorted([lr for lr in lines if lr.y1 >= r0.y0 - 2 and lr.y0 <= r1.y1 + 2], key=lambda r: r.y0)
    out = []
    for lr in picked:
        x0 = r0.x0 if abs(lr.y0 - r0.y0) < 4 else lr.x0   # 首行贴起词左缘
        x1 = r1.x1 if abs(lr.y0 - r1.y0) < 4 else lr.x1   # 末行止于止词右缘
        out.append((x0, lr.y1 + 1.6, x1, lr.y1 + 1.6))
    return out
```

- **`r1` 必须取「起点之后的第一个命中」**：终点词在一页里出现多次时（`答辩`、`案例报告`），取最后一个会让划线从句子一路铺到页脚，整页被划满。
- **终点词仍要短**：`分析总结及前瞻性验证`、`质量和严谨性` 这类跨行长串命中为 0；缩到 `前瞻性`、`确保学位申请质量` 才命中。差末尾两三个字是可接受的，硬凑反而整句划不上。
- **批注说「第一个划线删掉」＝ 该 op 直接不写**：删掉对应 `apply()` 那一条，不要画了再想办法抹。

## 四之三、表格「整块框起来」用矩形，不要划线

批注写「应用价值整个框起来，不用划线」时，`draw_rect` 要框**整行三列**（一级指标 + 二级指标 + 具体要求），只框左边四个字会被退回：

```python
r = page.search_for('应用价值')[0]
cells = [fitz.Rect(c) for c in page.find_tables().tables[0].cells if c]
target = next(c for c in cells if c.contains(fitz.Point(r.x0 + 2, r.y0 + 2)))
same_row = [c for c in cells if c.y0 < target.y1 - 2 and c.y1 > target.y0 + 2]
box = fitz.Rect(min(c.x0 for c in same_row), target.y0, max(c.x1 for c in same_row), target.y1)
page.draw_rect(box, color=(1, 0, 0), width=4.0)
```

取「与该单元格纵向重叠的所有 cell」的并集，合并单元格（纵向跨行的一级指标格）也自然带上。

## 四之四、先读批注再动手

划线要求常在文档批注里，**别按自己的判断先划**：

```bash
lark-cli drive +list-comments --token <docx-token> --type docx --solved-status all --as user --format json
```

- flag 是 `--token` + `--type`，**没有 `--file`**（用错会报 unknown flag）。
- 默认只回未解决的；要看全量加 `--solved-status all`。
- 内容在 `reply_list.replies[].content.elements[].text_run.text`。
- 一条批注对应一处划线，逐条对；同一页多条批注（「删这个、划那段、框这块」）要一起处理完再渲染一次。
- 改完 PDF 要**重新 open 副本**再渲染，别拿旧 `fitz.Document` 继续用（标注已写入文件，对象状态可能还是旧的）。
- 同一页多处划线要一次跑完再 save，中途 save 再加线会叠两遍。
