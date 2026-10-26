# 飞书文档：读批注 + 写回正文

场景：长文和图文版在同一篇飞书 docx/wiki 里，用户在「标题：」「正文：」两栏下批注，要求据此改写并把新稿写回。

## 1 · 读全文（拿到事实骨架）

```
terminal(command="lark-cli docs +fetch --doc \"<URL>\" --as user --doc-format markdown", timeout=120)
```

返回 JSON，正文在 `data.document.content`。

## 2 · 读批注（关键一步）

同一个 fetch 会带 `reference_map.comments`，里面每条：

```xml
<comment comment-id="..." start-block-id="..." end-block-id="...">
  <quote>被批注的原文</quote>
  <msg user="...">批注意见</msg>
</comment>
```

逐条抄成「原文 → 意见」两列，**按文本顺序**排，再动手改。同一条 quote 可能挂多条 msg（一个位置两轮意见）。

批注上限会被截断，返回的 `comments.tips` 有提示时改用 `lark-cli drive +list-comments` 取全量。

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

## 坑

- **`block_replace` 会让被替换块的批注一并失效**。用户还在标注时不要边改边 replace：先本地改好，再一次性提交。
- **别用 `--command overwrite`**：会清空文档里的 `<grid>` 配图和已有评论。
- 灰色小字用 `<span text-color="rgb(143,149,158)">`，与长文里「素材来源」同色。
- 标题栏放「主标题 + 备选一行」便于用户挑；正文栏不放备选。
- 插入空 `<p>` 会把段落挤散，写入时每个 `<p>` 都要有内容。
