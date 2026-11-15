<!-- 由 feishu-doc-sync 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/productivity/feishu-doc-sync -->

---
name: feishu-doc-sync
description: 本地 Markdown 同步为飞书云文档（原图上传、飞书格式排版）时使用。
---

# 本地 Markdown → 飞书云文档（含原图上传）

用 lark-cli 把含本地图片的 md（Obsidian 笔记等）同步成飞书云文档：图片全部上传原图，表格/高亮块按飞书格式重新排版。实测于「视觉风格家谱」225 图同步（会话脚本参考：/Users/Jin/Documents/Hermes/feishu_sync/，含 token 映射可增量更新）。

## 前置
- lark-cli 已安装绑定并完成 auth login（见 references/lark-cli-setup.md）
- 操作前 MUST 读官方 vendor skill：`lark-cli skills read lark-doc`（docs 工作流 / XML 语法 / 格式规则，勿从 --help 猜）；涉及云空间另读 `lark-cli skills read lark-drive`
- 文档操作默认 `--as user`（用户身份）

## 核心结论（实测验证，勿走弯路）
1. **本地图片入文档的正解**：XML 内容里 `<img src="<file_token>">` 可直接引用已上传媒体（图片内容正确，实测下载核验原图尺寸一致）。Markdown 导入（`--doc-format markdown`）只吃 http(s) URL 图片，本地路径不行。
2. **批量上传套路**：建临时文档 → 逐张 `docs +media-insert --file ./相对路径` 收集返回的 file_token（脚本 templates/batch_upload.py）→ XML 引用 token 建正式文档 → 删临时文档。225 张约 20 分钟（~5s/张）。
3. **大文档分块**：一次性 `docs +create --content @whole.xml` 超 ~100KB 会 server time out（120KB 实测挂）。先建骨架（title+说明+callout），再逐章节 `docs +update --command append --content @sec.xml`，单块 ≤60KB 稳定。
4. **WebP/BMP**：+media-insert 对非 PNG/JPEG/GIF 必须同时传 `--width` 与 `--height`（否则 "source image dimensions could not be detected"），用 `sips -g pixelWidth -g pixelHeight` 探测后按目标宽等比算高。
5. **--file 限相对路径且不得越出 cwd**：先 cd 到图片根目录，传 `--file ./子目录/图.jpg`；传绝对路径或 `../` 越界都会被拒（unsafe file path）。

## 流程
1. 解析源 md → JSON：跳过 YAML frontmatter；按 `|` 拆表格行；`<img src="...">` 提取图片相对路径；`> [!tip]` / `> [!abstract]` callout 段单独收集；校验全部图片路径存在
2. 建临时文档（标题如「临时-图片中转站（自动删除，勿动）」）+ 批量上传（templates/batch_upload.py：断点续跑 state 文件、每张失败重试 4 次、webp 自动补 height）
3. 生成 XML：文本用 xml.sax.saxutils.escape 转义；英文提示词两侧反引号去掉；callout 内只放文本/标题（禁 table/img）
4. 分段创建：骨架 + 每章节一个文件 append；create_state.json 记 doc_id/appended 支持断点续跑
5. 验证：`docs +fetch --doc <id> --detail with-ids`，python 正则数 `<img `/`<h2 `/`<table `/`<callout ` 数量与源数据一致；抽查 `docs +media-download --token <token> --output x` 后用 `file` 命令核对尺寸
6. 清理：`drive +delete --file-token <token> --type docx --yes` 删临时/测试文档

## 飞书排版要点
- `<title>` 文档标题；`<p>` 段落；使用说明用 `<callout emoji="bulb">`；章节模板用 `<callout emoji="abstract" background-color="blue">`（子块仅文本/标题）
- 表格：`<table><thead><tr><th><p>列名</p></th>…</thead><tbody><tr><td>…</td>…</tr></tbody></table>`，单元格文本必须包 `<p>`
- 表格内图片 240px（`<img src="token" width="240" name="文件名"/>`），点击可放大看原图
- 修正源文档过时数字（如「60 张」→ 实际 225 张）并在文末标注数据快照时间（用户偏好：数据标注快照）

## 坑
- +media-insert 输出带 "Inserting: …" / "Root block ready: …" 前缀行，json.loads 前需先跳过非 JSON 行
- 数 img 数量用 `re.findall(r'<img ', content)`；grep -c 数的是行数（整表在一行会误报为 11 而非 225）
- 删文档报 "file has been delete." / "not found." = 已删，幂等属正常
- `docs +create` 大内容 server time out 后可能已部分建文档：先 `drive +search --query <标题> --doc-types docx` 确认无残留再重试
- lark-cli 的 docs 域要求先读 vendor skill 再操作——直接看 --help 推断参数容易踩格式错误

## 支持文件
- references/lark-cli-setup.md — lark-cli 安装 / Hermes 上下文绑定 / 设备流授权 / 二维码
- templates/batch_upload.py — 批量上传脚本模板（webp 探测、断点续跑、失败重试）
