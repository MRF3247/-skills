# 飞书云文档：写入成稿 → 收批注 → 逐条返工

用户给一条飞书长文链接（`/wiki/<token>` 或 `/docx/<token>`），会先要「图文版本的正文」，写完让你**直接写进那篇文档**，接着他在文档里逐句批注。这是同一条流水线，别拆成两件事。

## 1. 读长文（事实源）

```bash
lark-cli docs +fetch --doc "<URL>" --as user --doc-format markdown
```

长文常分「一、公众号长文版」「二、图文版本」两大块，后者留着空的「标题：」「正文：」小节——那就是要填的位置。图片是 `<img src="token">`，按 alt 描述判断用哪几张。

## 2. 写入（先拿 block id）

```bash
# 拿空小节的标题块 id
lark-cli docs +fetch --doc "<URL>" --as user --doc-format xml --detail with-ids
# 输出里找：<h2 id="...">正文：</h2>

lark-cli docs +update --doc "<URL>" --as user --command block_insert_after \
  --block-id <正文标题的 h2 id> --content "$(cat body.xml)"
```

XML 写法：一个 `<p>` 一段，`<p>…</p>` 连写；备选标题用灰色行 `<p><span text-color="rgb(143,149,158)">备选：…</span></p>`。中文引号直接写，不转义。

## 3. 收批注

不加 `--scope` 地 fetch，批注在 `data.document.reference_map.comments`：

```bash
lark-cli docs +fetch --doc "<URL>" --as user --doc-format xml --detail simple
```

```python
for k, v in rm["comments"].items():
    print(k, v["data"])   # <comment ...><quote>被引原文</quote><msg user="…">批注</msg></comment>
```

读法：`<quote>` 是他圈中的那几个字，`<msg>` 是他的话，可能一条 block 上挂多条（同一句被连着批两次）。**先把全部批注列成对照表（被引原文 → 他的指令 → 你的处理）再改稿**，不要边看边改。

批注的三种语义，别一律当「润色」处理：

| 批注 | 真实含义 |
|---|---|
| 「AI 味太冲，删掉」「滚远点」 | 整句/整段删除，不许换句话留着 |
| 「改为：<他的原句>」 | 直接采用他的句子，不要再改措辞 |
| 「先写中文官方名称，再标注英文缩写」 | 全篇同类写法一起改，不只改这一处 |
| 「这个标题都很烂，起码要贴近主题」 | 整个标题重做，换方向而不是换词 |
| 「没啥要点」「结尾收得不咋地」 | 删，不留替代句 |
| 「核实原文回复我的批注」 | 他要的是**在文档里那条批注下回复**，不是正文改一改了事，见第 3.1 节 |
| 「XX 叫 YY，写进原文吧」 | 直接改用他给的名字，同时把事实核对表里的「不猜汉字」那一行一起改 |

### 3.1 批注的真实 comment_id 与回复

`reference_map.comments` 里的键（`c1`、`c2`…）是**本地锚点，不是 comment_id**，直接拿去调接口会失败。真实 ID 要单独列：

```bash
lark-cli drive +list-comments --url "https://my.feishu.cn/docx/<token>" --as user --format json
# items[]: comment_id / quote / is_solved / reply_list
```

`quote` 就是被圈的原句，用它跟 `reference_map` 的条目对齐（两边文字一致即同一条）。

回复：

```bash
lark-cli drive +add-reply --url "https://my.feishu.cn/docx/<token>" \
  --comment-id 7704xxxxxxxxxxxxxxx --content @/tmp/reply.json --as user
```

`--content` 的形状是 **`[{"type":"text","text":"…"}]`**（裸数组）。传 `{"reply_elements":[…]}` 会直接 `--content is not valid JSON: cannot unmarshal object`。

⚠️ **回复要活下来，锚点那一段就不能被替换**：`block_replace` 会把挂在该块上的批注一起消掉。含「核实原文回复我」这类要求回复的批注，该段保持原样（正文想解释的内容写进回复里），其余段落随便替换。别回复完再把整篇 overwrite 一遍。

## 4. 改稿：整段替换

同父连续段落用区间替换（正文各段与 tag 行都是顶层 `<p>`，同父）：

```bash
lark-cli docs +update --doc "<URL>" --as user --command block_replace \
  --start-block-id <第一段 p id> --end-block-id <tag 行 p id> --content "$(cat n_body.xml)"
```

单块替换：`--block-id <p id>`。

- 替换会让旧 block id 和挂在上面的批注一起失效——这是可接受的：新正文已经落实了批注。**替换前确认每条批注都进了新文本**，否则批注一删就找不回来。
- 标题块与备选行分别替换（两条 `block_replace`），别把两行塞进一个块。
- ⚠️ **替换会带原来块的类型走一部分，但小标题要显式写标签**：把一个 `<h2>` 块用 `<p>…</p>` 替换，它就变成普通段落（字数标注行这类「伪小标题」最容易踩），后续文档结构和同批子文档对不上。要保留层级就用 `<h2>正文</h2>` 作为 `--content`，XML 里的标签决定结果类型，不是原块决定。表格里的格子（`<td>`/`<li>`）同理，替换 `<li>` 必须用 `<li>`。
- 一次改多处就逐个 `block_replace`（bash 里 `for` 循环跑），比整篇 overwrite 安全：overwrite 会连元信息、事实核对表一起冲掉。
- ⚠️ **`block_insert_after` 的锚点落在表格单元格里时，新内容全部塞进那个格子**（变成同一格里 `<br/>` 分隔的一串），不会新建表格行——表格的行是 `<tr>` 结构，插 `<p>` 只能进格。要往「事实核对表」加行：先 `block_delete --start-block-id <误插的首个 p> --end-block-id <末个 p>` 把塞进格子的段落删掉，再把补充信息写成**表格外的段落**（例如拼进出处的「补充信源」段），别硬凑表格行。删完必 fetch 确认格子恢复成单段。
- 写完必 fetch 一次验证实际落盘内容（`--scope keyword --keyword "标题：" --context-after 30` 最省 token）；**要看层级有没有掉，用 `--doc-format xml --detail with-ids` 看标签**，markdown 视图看不出 h2 变 p。

## 5. 同步回选题库记录

子文档改完，选题库里那条记录的「润色正文」还是旧版——两边都要更。用 `+record-batch-update` 覆写正文列，再 `+record-list` 读回核长度（`+record-get` 可能显示空，别据此判失败）。字数标注行里的「正文 X 字／含 tag Y 字」也要跟着重算，别留旧数。

## 5.1 定稿后他补发一手长报道：按三档取增量，按字数取舍

稿子已成型，用户会再丢一篇更详细的报道（公众号/行业媒体专访）说「把某某的经历补进去，不超过 N 字」。**不要整段搬运**，按可信度贡献从高到低取三类：

1. **评审环节**：答辩/评审的时间、委员会阵容（主席与委员的机构+职务）、结果是否「不完美」、被要求补什么——这是「成果够不够格」的直接证据，读者最想看。
2. **成果体量**：报告页数与字数、数据基础（多少年队列/多少例）、独创工具——把「实践成果是不是水」这件事量化掉。
3. **后续应用**：成果用在了哪一例真实病人、结局如何——比任何专家评价都有力。

**腾字数的删减顺序**（从上往下删）：旁证型专家观点（第二位学者的评论）→ 背景铺垫段（法律沿革只留一句）→ 理念型收尾句。案例与评审细节最后保留。**花边内容**（绰号、师徒趣事）默认不进正文，除非用户点名要它当钩子；此时应改标题方向，而不是挤正文字数。

新报道必须**写进「出处」作为第二信源**（媒体名 + 日期 + 版面 + 记者 + 链接），并在事实核对表旁注明它提供了哪几条事实；正文里属于它的事实，状态列标它的名字，别混在英文原文那一列。

## 6. 交付顺序

1. 聊天里先给标题（主+备选）与完整正文，正文照旧完整贴出，不只给路径。
2. 附「批注落实对照表」（被引原文 → 他的处理指令 → 我的处理），他要拿它核。
3. 落一份 md 到 `~/Documents/Hermes/小红书成稿/`，`MEDIA:/绝对路径` 附上。
4. 文末提醒：出处链接放评论区置顶，正文不放链接。
