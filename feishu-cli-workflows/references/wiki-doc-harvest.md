# 清单表里的 N 篇云文档 → 批量收进知识库节点（复制保原树）

用户给一张「文档汇总表」（sheet 里逐行列着 wiki/docx 链接 + 标题），要求「都整理到 X 节点的子文档」。
这是**跨空间收集**任务，不是移动，也不是新建。

## 0. 先确认三件事（一个 clarify 问完，别自己猜）

| 要问 | 为什么 | 常见答案 |
|---|---|---|
| 范围：表里的「原文档/父文档」那一行算不算 | 表里常混着 1 行父文档 + N 行子文档 | 全要，且保留层级（父文档下挂子文档） |
| 复制还是移动 | 移动会让源空间的文档树清空、源表里的链接指向空节点 | 复制（原件保留，表内链接照旧可用） |
| 落到哪个子节点 | 知识库顶层往往有 A.方案/B.调研/C.选题&创作 这类目录 | 按内容归类，不要默认塞根目录 |

默认取向：**收集/交接类任务一律 copy**；move 只在用户明确说「旧的不要了 / 搬家」时用。

## 1. 读表拿清单

```bash
lark-cli sheets +workbook-info --url "<sheet url>" --as user --format json   # 先看有几张子表、sheet_id
lark-cli sheets +csv-get --url "<url>" --sheet-name "<实名>" --range "A1:C60" --as user
```

`+csv-get` 的 `annotated_csv` 每行带 `[row=N] ` 前缀（N 是真实行号）；要拿结构化清单就 python `csv.reader` 解析后丢掉第一列前缀。**只取「标题 + 链接」两列**——正文列可能几千字，别整列读进上下文。

## 2. 解析每个链接：拿 space_id / node_token / 父节点

```bash
lark-cli wiki +node-get --node-token "<wiki url>" --as user --format json
# → data: space_id, node_token, obj_token, obj_type, parent_node_token, title, has_child
```

一次循环打印 4 个字段（space_id / parent_node_token / obj_type / title）：
- 全部同 space_id → 源空间确定；目标空间的 space_id 用 `wiki +space-list --as user` 按中文名对（如「不卷@医时」）。
- parent_node_token 相同且等于其中某一行的 node_token → 那行就是父文档，其余是它的子文档，层级直接照抄。

## 3. 复制：先父后子，`--title` 顺手改名

```bash
# 父文档挂到目标节点下
lark-cli wiki +node-copy --space-id <源空间> --node-token <父node> \
  --target-parent-node-token <目标node> --title "推广｜<原名>" --as user --yes --format json
# → data.node_token 就是新的父节点，子文档挂到它下面

# 子文档逐个复制到新父节点
lark-cli wiki +node-copy --space-id <源空间> --node-token <子node> \
  --target-parent-node-token <新父node_token> --title "推广｜<子原名>" --as user --yes --format json
```

- **`+node-copy` 非递归**：只复制这一个节点和它的正文，子节点不会跟过来 → 必须按「父先复制、拿新 node_token、再逐个复制子」的顺序手工排。
- `--title` 与复制同一步完成改名，**不要**复制后再 `drive +update-title` 走第二趟（会破一次锁、多一轮网）。
- 是 high-risk，必带 `--yes`；用户已明确回答「复制」即视为同意整批，不必逐篇再问。
- 批量循环里每篇 `sleep 1`、失败 `sleep 3` 重试 3 次：wiki 写入有锁竞争（`131009`），并发或连发会偶发失败。
- 目标节点本身可以是 bitable（多维表格）——wiki 节点不论 obj_type 都能挂子节点，别因为 `obj_type: bitable` 就以为不能放子文档。

## 4. 标题体例（本用户知识库）

选题库里用**全角「｜」前缀**做内容类型标签：`推广｜`、`营销 ｜`、`引流｜`。用户让加前缀时照此体例写全角竖线，不要写半角 `|`、也不要加空格。没点名加前缀就**保持原标题**，不要自行补标签。

## 5. 验证（ok:true 不是证据）

```bash
# 层级
lark-cli wiki +node-list --space-id <目标空间> --parent-node-token <目标node> --page-all --as user --format json
lark-cli wiki +node-list --space-id <目标空间> --parent-node-token <新父node> --as user --format json
# 正文非空 + 与源一致（docx）
lark-cli api GET "/open-apis/docx/v1/documents/<obj_token>/raw_content" --as user --format json
```

逐篇比 `content` 长度/逐字相同。**源文档本身是空壳时（只有标题、正文为空）复制后仍然为空——交付里点名是哪几篇，不要写成「全部完成」糊过去。** 总子文档数应等于「原数 + 新增数」，报给用户让他对账。

## 6. 单个 sheet 子表 → 独立备份表挂进知识库（「复刻一个副本备用」）

用户说「这张表里的 XX 总表单独复刻一个副本放到某知识库备用」时，**不要**用 `+workbook-create` 重灌值（丢样式/公式），走整簿复制再裁剪：

```bash
# 1) 整簿复制到我的空间（样式/公式/列宽/条件格式全保真）
lark-cli drive +copy --url "<sheet url>" --name "审核总表-备份副本" --folder-token my_space --as user --format json
#    → data.file_token 即副本 token

# 2) ⚠️ 刚复制完 +workbook-info 会返回 ok:true 但 data 为空（副本还在生成）
#    不是失败：sleep 8 后重试即出 sheets[] 结构

# 3) 副本里删掉不需要的子表（只在副本上删，源表不动；--yes 是 high-risk 门禁）
lark-cli sheets +sheet-delete --url "https://my.feishu.cn/sheets/<副本token>" --sheet-id <要删的sid> --as user --yes

# 4) 挂进知识库指定节点（docs_to_wiki 模式，CLI 自动轮询）
lark-cli wiki +move --obj-type sheet --obj-token <副本token> \
  --target-space-id <空间> --target-parent-token <父节点> --as user --format json
#    → data.wiki_token / node_token = 新节点；交付链接用 https://my.feishu.cn/wiki/<wiki_token>
```

值是否真的一致的核对方式（比整表肉眼比对可靠）：两边各 `+csv-get --range A1:T27` 落文件，`sed 's/\[row=[0-9]*\] //'` 去掉行号前缀后 `diff`，无输出即逐格相同。

## 7. 交付

- 备份表给 wiki 链接 + 位置（「不卷@医时 › 3. 内容增长」）+「已删掉另一个子表，只留 XX 总表」。
- 收进知识库的文档**逐条列全**（编号 + 标题 + 链接），不许省略成「等 16 篇」；末尾报总数与空壳文档。
- 主动说明「全部是复制，同事原文档树和表内链接都没动」，让用户知道原件还在。
