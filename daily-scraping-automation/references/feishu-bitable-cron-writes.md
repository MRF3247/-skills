# 飞书多维表格写入/更新要点（lark-cli，2026-08 实测）

每日管道向多维表格写增量/回写数据时的踩坑合集。

## 写入记录
- **批量写：`base +record-batch-create --base-token <base> --table-id <tbl> --json '{"create_records":[{字段名:值,...},...]}' --as user`**
  - 参数是 `--json`（不是 `--records`）；结构 `{"create_records":[...]}`（不是 `{"fields":[...]}` 或数组）。
  - select 字段写**裸字符串值**（如 `"来源": "ScienceDaily"`），不是数组。
  - url 样式 text 字段写 URL 字符串。
  - 每批 ≤200；`--json` 参数直接传 JSON 字符串（超长 payload 写临时文件读取后作为参数传入，避免 shell 展开问题）。
  - `ok: true` 后 **table-list 的 records_count 有缓存延迟**（等 2-3s 再查）。

## record_id 获取（回写/删除必需）
- **`+record-list` / `+record-search` 返回 data 是二维数组，不带 record_id**——无法定位更新/删除。
- 可靠方法：原生 API 拉全量带 ID 记录：
  `lark-cli api GET /open-apis/bitable/v1/apps/<base>/tables/<table>/records --params '{"page_size":500,"page_token":""}'`
  → `data.items[]` 每条带 `record_id` + `fields`。按业务键（URL/bvid/账号名）建映射。
- 回写：`+record-batch-update --json '{"update_records":{"recXXX":{"字段":值}}}'`（≤200/批）。
- 删除：`+record-delete --json '{"record_id_list":[...]}' --yes`（high-risk-write 必须 --yes；≤100/批）。

## 字段操作坑
1. **字段名必须与表实际字段完全一致**：报 `code:800030201 not_found` 时 hint 会列出表内前 5 个字段——用它核对。**建表后先 `+field-list` 核对字段名**：base-create/table-create 可能把 select 字段命名成意外名字（实测 `"章节"` 被建成了 `"来源类型"`，选项内容对但字段名不对，写入时 not_found）。
2. **auto_number 字段（如 ID）删不掉**：`+field-delete` 报 `unsafe_operation_blocked`（系统字段）。用户嫌"ID 列莫名其妙"时 → **视图层隐藏**：`+view-set-visible-fields --view-id vewXxx --json '{"visible_fields":["UP主","标题",...]}'`（先 `+view-get-visible-fields` 看现状）。
3. **select 字段加选项**：`+field-get` 拿 options（顶层 `options` 数组，不是 property.options）→ append → `+field-update --json '{"type":"select","name":"来源","multiple":false,"options":[...]}' --yes`（全量提交）。
4. **链接字段在 fields 里可能是 dict**：`{"text":..., "link":...}`——解析 URL 时 `isinstance(url, dict)` 取 `link`。
5. **数值字段**：number 类型写 int；从 fields 读出时可能是字符串/空，`int(x or 0)` 容错。

## 建表/建字段
- `+table-create --base-token <base> --name "xxx"` → 返回 table_id。
- `+field-create --base-token <base> --table-id <tbl> --json '{"type":"text","name":"标题"}'`（逐个建；select 带 `"options":[{"name":...}]`）。

## 其他
- 每日增量建议加「入库日期」字段（内容发布日期 ≠ 入库日期，用户按入库日期筛当天新增）。
- wiki 移动：`wiki +move --obj-token <base_token> --obj-type bitable --target-space-id <sid> --target-parent-token <node>`（obj-type 是 `bitable` 不是 `base`；docs-to-wiki 自动轮询返回 node_token）。
