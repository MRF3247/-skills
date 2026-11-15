# md 表格 → 批量飞书 sheet（对标账号稿件清单模式）

2026-08-14 实测：44 个对标账号 md（`/Users/Jin/Documents/医时知识库/选题参考/B站素材库/对标账号库/`）里每账号一个「全部稿件清单」markdown 表格 → Wiki「ⅰ. B站参考账号」同级电子表格，43 表 / 31,280 行一次成型。

## 目标表格格式（对齐参考表 01-兔叭咯）

列序：`标题 | 播放量 | 点赞 | 投币 | 收藏 | 评论 | 转发 | 弹幕 | 互动总量 | 发布时间 | 时长 | 链接`
- 数值：纯数字（万 → int），dtypes `Int64`，可排序
- 发布时间：`yyyy-MM-dd`（string）
- 链接：纯 URL（`https://www.bilibili.com/video/BVxxx`），string
- 本地 md 无弹幕/互动总量数据 → 传 `null`

## 1. 解析 md 表格

md 结构：frontmatter → `## 全部稿件清单（按播放量从高到低）` → markdown 表格。
本地列序：`播放 | 点赞 | 投币 | 收藏 | 转发 | 评论 | 标题 | 时长 | 发布 | 链接 | 逐字稿 | 选题分析`（12 列，末两列常为 `—`）。

```python
import re
m = re.search(r'^##\s*全部稿件清单.*$', content, re.M)
rows = []
for line in content[m.end():].split('\n'):
    line = line.strip()
    if line.startswith('|') and line.endswith('|'):
        cells = [c.strip() for c in line.strip('|').split('|')]
        if cells[0] == '播放' or set(cells[0]) <= set('-: '):
            continue  # 跳表头行/分隔行
        rows.append(cells)
```

## 2. 转换规则

```python
def to_number(v):   # '1080.64万' → 10806400；'—'/'' → None
    v = v.replace(',', '').strip()
    if not v or v in ('—', '-'):
        return None
    m = re.match(r'^([\d.]+)(万)?$', v)
    if m:
        num = float(m.group(1))
        if m.group(2):
            num *= 10000
        return int(num)
    return v

def extract_url(v):  # '[B站](https://...)' → 'https://...'
    m = re.search(r'\((https?://[^)]+)\)', v)
    return m.group(1) if m else v

def to_date(v):      # '2022-11-12' 截断（原始可能是带 T 的时间戳）
    return v[:10] if re.match(r'^\d{4}-\d{2}-\d{2}', v) else v
```

列映射（本地 → 目标）：`播放→播放量`、`点赞/投币/收藏/转发` 同名列、`评论→评论`、`标题`、`时长`、`发布→发布时间`、`链接`（extract_url）；弹幕/互动总量 = None。

## 3. typed 一步建表

payload（每账号一个文件，如 `payload_34.json`）：

```json
{"sheets": [{"name": "稿件清单",
  "columns": ["标题","播放量","点赞","投币","收藏","评论","转发","弹幕","互动总量","发布时间","时长","链接"],
  "data": [[...每行 12 个值...]],
  "dtypes": {"标题":"string","播放量":"Int64","点赞":"Int64","投币":"Int64","收藏":"Int64",
             "评论":"Int64","转发":"Int64","弹幕":"Int64","互动总量":"Int64",
             "发布时间":"string","时长":"string","链接":"string"}}]}
```

```bash
cd <payload 目录>   # --sheets @file 只接受 cwd 内相对路径
lark-cli sheets +workbook-create --as user --title "34-SCI论文写作-稿件清单" --sheets @payload_34.json
# 返回 data.spreadsheet.spreadsheet_token + url；data.sheets[].sheet_id 验证用
```

## 4. 移入 Wiki 同级节点

```bash
lark-cli wiki +move --as user --obj-token <spreadsheet_token> --obj-type sheet \
  --target-space-id <space_id> --target-parent-token <父node_token>
# 返回 data.wiki_token（即新 wiki node_token，文档 URL 用 https://my.feishu.cn/wiki/<wiki_token>）
```

父节点解析：参考表链接 `https://my.feishu.cn/wiki/<token>` → `lark-cli wiki spaces get_node --params '{"token":"<token>"}'` 读 `data.node.parent_node_token` + `space_id`。

## 5. 批量脚本骨架（断点续跑 + 重试）

- `done.json`：`{序号: {"title","token","wiki_token","rows"}}`，每完成一个即写入
- 循环：create（重试 3 次，捕获 socket timeout）→ move（重试 3 次）→ sleep 1.5s
- ⚠️ **手动先测试的小账号必须手动写进 done.json**，否则批量循环会重建同号 → 重复节点
- 大文件（6000+ 行）payload 数 MB 无问题；`--sheets @file` 一次成型

## 6. 验证

```bash
# 节点完整性：数 sheet 数、查重复标题、查缺号
lark-cli wiki +node-list --space-id <sid> --parent-node-token <父node> --format json
# 数据抽查：表头 + 首行
lark-cli sheets +cells-get --spreadsheet-token <t> --sheet-id <sid> --range "A1:L3"
```

⚠️ `+node-list` / `+node-get` 输出 JSON 前有进度行（`Fetching wiki node Tmh7...anub...`），直接 json.load 报错 → `raw[raw.find('{'):]` 再解析；字段是 `data.nodes`（不是 items）。

## 7. 重复节点清理

```bash
lark-cli wiki +node-get --node-token <wiki_token>          # 拿 obj_token
lark-cli drive +delete --file-token <obj_token> --type sheet --yes
```
