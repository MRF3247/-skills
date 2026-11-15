# lark-cli Base 批量拉取/写入（Python 循环模式）

验证过的完整链路：wiki 链接 → base_token → 全量拉取(带 record_id) → 新建 select 字段 → 分批写入 → 读回验证。

## 1. 解析链接

```bash
lark-cli base +url-resolve --url "https://my.feishu.cn/wiki/<wiki_token>" --as user
# 返回 data.base_token；resource_type=bitable
lark-cli base +base-block-list --base-token "<base_token>" --as user   # 找 table_id + records_count
lark-cli base +field-list --base-token "<base_token>" --table-id "<table_id>" --as user  # 看字段/选项
```

## 2. 全量拉取（关键：保存 record_id_list）

`+record-list` 返回 `data.data`（列值数组，顺序由 `data.fields` 给出）和 `data.record_id_list`，两者**按位置一一对应**。分页用 `--offset`（不是 page_token）。

```python
import subprocess, json

BASE, TABLE = "<base_token>", "<table_id>"
all_rows, fields, offset = [], None, 0
while True:
    cmd = ["lark-cli","base","+record-list","--base-token",BASE,"--table-id",TABLE,
           "--as","user","--limit","200","--offset",str(offset),"--format","json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    d = json.loads(r.stdout[r.stdout.index('{'):])
    data = d['data']
    recs, ids = data.get('data', []), data.get('record_id_list', [])
    if not recs: break
    if fields is None: fields = data.get('fields', [])
    name_idx = fields.index('账号名')   # 换成你的业务键字段
    for rid, rec in zip(ids, recs):
        all_rows.append({"record_id": rid, "账号名": rec[name_idx]})
    offset += len(recs)
    if len(recs) < 200: break
# 得到 record_id -> 业务键 映射，写入本地 json 备用
```

注意：raw `api GET /records` 的 page_size 不透传（固定 20 条/页，--page-all 也无效），全量必须走 `+record-list --offset`。

## 3. 新建 select 字段

```bash
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" --as user --json '{
  "type":"select","name":"产品相关性","multiple":false,
  "options":[
    {"name":"S","hue":"Red","lightness":"Light"},
    {"name":"A","hue":"Orange","lightness":"Light"},
    {"name":"B","hue":"Yellow","lightness":"Light"},
    {"name":"C","hue":"Wathet","lightness":"Light"},
    {"name":"D","hue":"Gray","lightness":"Lighter"}
  ],
  "description":"与产品相关性分级说明"
}'
```

## 4. 分批写入（每批 ≤200，串行 + sleep）

`--json @file` **必须是相对路径**：先 cd 到文件目录，再传 `@batch_N.json`。绝对路径报 `invalid JSON file path ... must be a relative path within the current directory`。

```python
import os, json, subprocess, time

updates = {rid: {"产品相关性": [grade]} for rid, grade in grades.items()}  # select 用数组值
items = list(updates.items())
os.makedirs('/tmp/ub', exist_ok=True)
for i in range(0, len(items), 200):
    batch = dict(items[i:i+200])
    with open(f'/tmp/ub/batch_{i//200}.json', 'w', encoding='utf-8') as f:
        json.dump({"update_records": batch}, f, ensure_ascii=False)

# 执行（cwd=/tmp/ub）
for i in range(7):
    r = subprocess.run(["lark-cli","base","+record-batch-update","--base-token",BASE,
        "--table-id",TABLE,"--as","user","--json",f"@batch_{i}.json"],
        capture_output=True, text=True, timeout=120)
    ok = json.loads(r.stdout[r.stdout.index('{'):]).get('ok')
    print(i, "ok" if ok else "FAIL")
    time.sleep(2)
```

## 5. 读回验证

```bash
# 单条抽查
lark-cli base +record-search --base-token "<base_token>" --table-id "<table_id>" \
  --as user --keyword "解螺旋官方频道" --search-field "账号名" --limit 1 --format json
# 全表分布统计：record-list --field-id 产品相关性 分页，Counter 计数
```

## 坑点速查

| 现象 | 原因 | 解法 |
|---|---|---|
| `--json @/abs/path` 报 invalid JSON file path | @file 限相对路径 | cd 到目录或复制文件过去 |
| raw api 只回 20 条 | page_size 不透传 | 用 `+record-list --limit 200 --offset` |
| record_id 拿不到 | CLI 把 record 拆成 data + record_id_list | zip 两数组 |
| 批量更新报 1254104 | 单批 >200 | 分片，每批 ≤200 |
| select 写入失败 | 选项不存在 | 先 field-list 确认 options |
| 命令从 execute_code 调 lark-cli 报 not found | PATH 未继承 | 用 terminal 并 export PATH=$PATH:$HOME/.local/bin |
