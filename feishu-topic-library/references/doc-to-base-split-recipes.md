# 文档 → 多维表格 → 云文档：可复用配方

`docs +fetch --doc-format markdown` 的输出里，文档表格是内嵌 HTML，图片是 `<img … src="<img_token>"/>`。下面是实际跑通过的解析与生成代码。

## 1. 切章节 + 切表格

```python
import re, json, html

c = json.load(open('src_doc.json'))['data']['document']['content']
sec = {p.split('\n')[0]: p for p in re.split(r'\n(?=# )', c)}   # 按一级标题分节

def tables(p):
    return re.findall(r'<table>.*?</table>', p, re.S)

def rows(t):
    return [re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', tr, re.S)
            for tr in re.findall(r'<tr>(.*?)</tr>', t, re.S)]

def plain(x):
    return html.unescape(re.sub(r'<[^>]+>', '', x)).strip()
```

表头行是 `rows(t)[0]`，数据从 `[1:]` 开始。缺列的行用 `r + ['']*(n-len(r))` 补齐再取值。

## 2. 单元格里的多条目必须走 `<li>` 树

只按 `<br/>` 切会把 `<ol><li>` 的 6 条痛点粘成一句。正确的做法是跟踪 `<li>` 深度：

```python
def li_tree(cell):
    """返回 [(depth, text)]，只看 <li> 的文字，<br/> 变换行。"""
    out, depth = [], 0
    for tok in re.finditer(r'<li[^>]*>|</li>|<ul>|</ul>|<ol[^>]*>|</ol>|<br\s*/?>|<[^>]+>|[^<]+', cell):
        t = tok.group(0)
        if t.startswith('<li'):
            depth += 1; out.append([depth, ''])
        elif t == '</li>':
            depth -= 1
        elif t.startswith('<br'):
            if out: out[-1][1] += '\n'
        elif not t.startswith('<'):
            if out: out[-1][1] += html.unescape(t)
    return [(d, s.strip()) for d, s in out]

def li_items(cell):
    """只取顶层 li（= 一条痛点），内部换行压成；分隔。"""
    return [re.sub(r'\s*\n\s*', '；', s) for d, s in li_tree(cell) if d == 1 and s]
```

嵌套 `li`（`depth == 2`）是父选题下的子要点（如「选题前先确认这 3 件事」下的三条），不是独立选题——只能在父行的备注里拼进去，不能单独成行。

原文用 `<del>` 划掉的条目：解析时用 `<del>` in cell 判断并加前缀标记；用户明确要求「划除的也算回来」时直接不加前缀即可。

## 3. 图片按顺序取出

```python
# 整段方案单元格 → 有序的 文字行 / 图片token 序列
lines, buf = [], ''
for tok in re.finditer(r'<br\s*/?>|<img[^>]*?src="([^"]+)"[^>]*>|[^<]+|<[^>]+>', cell):
    t = tok.group(0)
    if t.startswith('<br'):
        if buf.strip(): lines.append(buf.strip())
        buf = ''
    elif t.startswith('<img'):
        if buf.strip(): lines.append(buf.strip()); buf = ''
        lines.append({'img': tok.group(1)})
    elif not t.startswith('<'):
        buf += html.unescape(t)
if buf.strip(): lines.append(buf.strip())
```

## 4. 拆分云文档的 XML 模板

关键点：`<img src="img_token"/>` 是**复制原图**，不需要下载再上传；顺序就是输出顺序。

```python
L = [f'<title>{esc(title)}</title>']
L.append('<h1>操作流程（文案 + 配图）</h1>')
for ln in lines:
    if isinstance(ln, dict):
        L.append(f'<img src="{ln["img"]}"/>')
    elif re.match(r'^\d+[、.]', ln):
        L.append(f'<h2>{esc(ln)}</h2>')     # 「1、上传数据」这类步骤用小标题
    else:
        L.append(f'<p>{esc(ln)}</p>')      # 提示词原文用正文
```

- 只转义文本：`& < >`，标签本身不转义。
- **不要写元信息表**（归属/分类/痛点/对接点）：用户口径是这些只留在多维表格里。
- 写完逐篇 `docs +fetch --doc-format markdown`，数 `![` 的次数与源小节图片数比对。

## 5. 按原章节序号命名

```python
order = [1, 2, 3, 4, 5, 6, 7, 9, 11]   # 原文档中实际有内容的小节位置，跳号保留
for d, no in zip(docs, order):
    new = f"{no}.{title}"
    subprocess.run(['lark-cli', 'drive', '+update-title', '--url', d['url'],
                    '--title', new, '--as', 'user'])
```

`docs +fetch` 读回时第一行 `<title>…</title>` 就是文档标题，可以用它验收改名是否生效。

## 6. 批量写入的健壮循环

```python
BATCH = 12
for i in range(0, len(recs), BATCH):
    chunk = recs[i:i+BATCH]
    json.dump({'create_records': chunk}, open('/tmp/t.json', 'w'), ensure_ascii=False)
    out = subprocess.run(['lark-cli', 'base', '+record-batch-create',
                          '--base-token', B, '--table-id', T,
                          '--json', '@/tmp/t.json', '--as', 'user'],
                         capture_output=True, text=True).stdout
    print(i, 'OK' if '"ok": true' in out else f'FAIL {out[:200]}')
```

- `--json @file` 的白名单：当前工作目录、`/tmp`、`~/files`。写别处先 cp 到 `/tmp`。
- 失败批不重跑，先 `+record-list --format ndjson` 数行数、按主键去重，再补差集。
