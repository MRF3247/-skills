# 飞书文档：读批注 + 写回正文

场景：长文和图文版在同一篇飞书 docx/wiki 里，用户在「标题：」「正文：」两栏下批注，要求据此改写并把新稿写回。

## 1 · 读全文（拿到事实骨架）

```
terminal(command="lark-cli docs +fetch --doc \"<URL>\" --as user --doc-format markdown", timeout=120)
```

返回 JSON，正文在 `data.document.content`。

## 2 · 读批注（关键一步）

**别指望 `docs +fetch` 带批注**——实测 fetch 只回 `{document}`，`reference_map.comments` 已经没有了。拿批注只能走 drive：

```
lark-cli drive +list-comments --url "<文档或 wiki URL>" --solved-status all --as user
```

每条给 `comment_id / quote / is_solved / reply_list.replies[].content.elements[0].text_run.text`。用 Python 逐条打印下面四行再动手：

> **`count: 0` 是有效答案，不是接口坏了**：wiki token 与 docx obj_token 各查一次都回 0，就认定这篇真的没有批注（用户可能只是说「这篇也改一下」）。别换着 URL 形式查第三次，改走「按 skill 全量自查 + 报改动点与依据」。

```python
for c in d['data']['items']:
    msgs = [r['content']['elements'][0]['text_run']['text'] for r in c['reply_list']['replies']]
    print(c['comment_id'], '|', repr(c['quote'])[:120], '|', msgs)
```

按文本顺序排成「原文 → 意见」两列表，再动手改。同一条 quote 可能挂多条 msg（一个位置两轮意见）。

改完要**逐条 `+resolve-comment`**（`--comment-id`，可传 URL）：

```
lark-cli drive +resolve-comment --url "<URL>" --comment-id <id> --as user
```

不 resolve 的话，`overwrite`／`block_replace` 之后批注会挂到已删 block 上，文档右侧会长期挂着一堆对不上位置的批注。

## 3 · 拿 block id

标题/正文是空栏时，先定位两个 h2：

```
terminal(command="lark-cli docs +fetch --doc \"<URL>\" --as user --doc-format xml --detail with-ids", timeout=120)
```

输出里 `<h2 id="...">标题：</h2>`、`<h2 id="...">正文：</h2>`，记下两个 id。

## 4 · 插入

标题（含一行灰色备选）：

```
terminal(command="lark-cli docs +update --doc \"<URL>\" --as user --command block_insert_after --block-id <标题h2 id> --content \"$(cat title.xml)\"", timeout=120)
```

`body.xml` 形状：每个自然段一个 `<p>`，最后一段是 tag 行，整体一次性插入。

## 5 · 改稿（批注落实之后）

同一父节点下连续的旧段落一次性替换：

```
terminal(command="lark-cli docs +update --doc \"<URL>\" --as user --command block_replace --start-block-id <首个段落id> --end-block-id <tag段落id> --content \"$(cat body.xml)\"", timeout=120)
```

单段替换用 `--block-id`。替换后旧 block id 全部失效。

## 6 · 回读验证（不可省）

```
terminal(command="lark-cli docs +fetch --doc \"<URL>\" --as user --doc-format markdown --scope keyword --keyword \"正文：\" --context-after 30", timeout=120)
```

确认标题、每个段落、tag 行都在，且顺序正确。

## 5b · 多维表格：字段与附件回写（物料库固定动作）

一篇稿定稿后表里要同步六列：`图文建议标题`、`封面建议文案`、`DS建议正文`、`系列`、`润色正文`（纯云文档 URL），以及三张图（封面图／封面图（带文案）／P2截图）。

```bash
# 1) 字段 ID 一次性拉全（返回 data.fields[]，键名是 id / name，不是 field_id / field_name）
lark-cli base +field-list --base-token <BASE> --table-id <TABLE> --as user

# 2) 上传新图拿 file_token（注意：这是**追加**语义，不是替换）
lark-cli base +record-upload-attachment --base-token <BASE> --table-id <TABLE> \
  --record-id <REC> --field-id <字段ID> --file "/tmp/骨肉瘤-封面.png" --as user

# 3) 用 batch-update 把字段写成「只含新 token 的数组」→ 旧文件自动掉（清空字段就写 []）
lark-cli base +record-batch-update --base-token <BASE> --table-id <TABLE> \
  --json @upd.json --as user
```

`upd.json` 的形态（附件列是对象数组，不是字符串）：

```json
{"update_records":{"<record_id>":{
  "fldXY4cwQ2":"主标：…｜副标：…",
  "fld03IouOZ":[{"file_token":"<新token>"}],
  "fldEMsdmhF":[]
}}}
```

- **想真替掉旧附件，只有这一条路**：upload 只追加，必须再 batch-update 把整列覆盖成单元素数组；只 upload 会在格子里留新旧两张同名图。
- 字段被清空（`[]`）后，旧文件的 file_token 不需要再单独删。
- 附件名要带内容关键词（`骨肉瘤-封面.png`），不要留 `cover_plain.png` 这种英文临时名——用户看得到。
- 附件路径只能给 cwd／`/tmp`／`~/files`，给 Obsidian 库里的路径会报 `unsafe file path`，先 `cp` 到 `/tmp`。

**整表导出时 `--format ndjson` 不回记录**：它只回一份清单（`records_count`、`page_count`、`record_file` 字段指向的**另一个文件路径**），真正的记录在 `record_file` 里。直接解析 stdout 会拿到 `{manifest_version…}` 而误以为没数据。做法：先读 stdout 拿 `record_file`，再 `json.loads` 每行那个文件。要找某篇的 record_id，就用 `内容标题／DOI／原文链接` 在 `record_file` 里 grep，比 `record-search` 的 filter 语法省事。

## 坑

- **`drive +download` 拉文档里的内嵌图会 403**（`token lookup failed … code=981003`）：报错 hint 指向 `lark-cli drive +preview --file-token <TOKEN> --type source_file --output <path>`。只是想看旧图长什么样、而反正要重出时，别在下载上耗时间——直接从图片来源重拍（P2 重跑 `shot_p2p3.py`，封面重跑豆包）。

- **`block_replace` 会让被替换块的批注一并失效**。用户还在标注时不要边改边 replace：先本地改好，再一次性提交。
- **别用 `--command overwrite`**：会清空文档里的 `<grid>` 配图和已有评论。
- 灰色小字用 `<span text-color="rgb(143,149,158)">`，与长文里「素材来源」同色。
- 标题栏放「主标题 + 备选一行」便于用户挑；正文栏不放备选。
- 插入空 `<p>` 会把段落挤散，写入时每个 `<p>` 都要有内容。
