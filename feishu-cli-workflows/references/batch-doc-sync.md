# 本地 md+图片 → 飞书云文档 批量同步配方

实测场景：Obsidian 视觉风格家谱 md（11 家族、225 张样张图、115MB 原图）同步为飞书云文档，图片上传原图并放入表格单元格。全程实测通过。

## 为什么是这个方案

- 飞书 docs 创建/导入时，图片只能通过：http(s) URL（markdown 导入）、或 **file_token**（XML `<img src=token>`，实测可用且内容正确）
- `+media-insert` 一次一张且固定插文档末尾 → 不能直接用于表格内图片
- 因此最优路径：**先批量上传拿 token，再用 token 一次构建完整 XML 创建文档**（225 图只花 225 次上传 + 1 次创建，无需移动）

## 步骤

### 1. 解析本地 md → 结构化 JSON

- 跳过 YAML frontmatter（`---` 块）
- 提取：标题、开头说明、tip callout 行、每个 `##` 家族 + `> [!abstract]` 模板块 + 表格行（5 列：样张 img src / 文件名 / 画面元素 / 提示词中 / 提示词英）
- 表格行按 `|` split（提示词里无 `|`，安全）；img src 用正则 `src="([^"]+)"` 提取
- **read_file 对超长行文件误判 is_binary**（本 md 单行 612 字符）：先 `file xxx.md` 确认 UTF-8，再用 python 读
- 校验：家族数、图片总数、每张图本地存在性（防漏）

### 2. 批量上传到临时文档（断点续跑）

```python
# 每张图：cd 到图片父目录（--file 必须 cwd 内相对路径）
lark-cli docs +media-insert --doc <临时doc> --file ./样张/xxx.jpg --width 240
# 输出 JSON 里取 data.file_token
```

- state 文件（upload_state.json）记录 `{doc_id, uploads: {img_rel: token}}`，每张落盘 → 中断可续
- 失败重试 4 次（间隔 2s 递增）；文件缺失记 MISSING 跳过
- 实测 ~5s/张（225 张 ≈ 19 分钟）
- **WebP 必须带 --height**（否则 Rolling back 失败）；`sips -g pixelWidth -g pixelHeight` 探测后按 240 宽等比算高

### 3. 构建完整 XML

- `<title>` + 说明 `<p>`（顺手把原文过时数字更新 + 标注快照时间，用户重视数据快照标注）
- tip → `<callout emoji="bulb">`；家族模板 → `<callout emoji="abstract" background-color="blue">`（模板文本按 `**标签**：内容` 分段，加粗标签）
- 每个家族：`<h2>家族名（N 张）</h2>` + callout + 5 列表格（样张 `<img src=token width=240 name=文件名/>` + 文件名 + 画面元素 + 中英提示词）
- XML 转义全部文本（& < > "）；英文提示词剥掉两侧反引号
- 225 图 XML ≈ 210KB，`docs +create --content @feishu_doc.xml` 一次创建成功

### 4. 验证与清理

- `docs +fetch --detail with-ids` 检查图片块数量与表格结构
- 抽查：`docs +media-download --token <token> --output v.jpg` → `file v.jpg` 尺寸 = 原图（1640x2048 等）
- 删除临时文档与测试文档（drive 域）

## 备选方案（已实测，作为降级路径）

- **逐张插入 + 移动**：`+media-insert`（末尾，返回 block_id）→ `block_move_after --block-id <单元格占位段> --src-block-ids <图片块>` → `block_delete` 删占位段。链路可行但 225 图要 675 次调用（3 倍于 token 方案），仅当 token 方案失败时用
- **骨架 + append**：大 XML 超限时，先建骨架再分家族 `block_insert_after` 追加

## 关键验证结论（实测）

1. XML `<img src="<file_token>">` 创建出的图片块内容 = 原图（下载验证 1640x2048），token 会被 CLI 复制成新值，不影响正确性
2. 表格单元格内可直接创建 img block（`<td><img src=token/></td>`），无需移动
3. callout 内禁止 img/table（lark-doc-xml 明确），模板提示词必须走文本
4. `--file` 绝对路径/`../` 越界都会被拒（unsafe file path），必须 cd 后相对路径
