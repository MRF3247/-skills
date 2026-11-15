<!-- 由 dse-encrypted-docs 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/productivity/dse-encrypted-docs -->

---
name: dse-encrypted-docs
description: "Use when docx 读乱码且头含 encrypted by dse。走 WPS 备份或 wpscli。"
version: 1.0.0
metadata:
  hermes:
    tags: [DSE, docx, 加密, WPS, 文档处理]
    category: productivity
---

# DSE 加密文档处理

## 触发
- 终端读 .docx/.xlsx 得到乱码，或 `unzip` 报 "End-of-central-directory signature not found"
- `xxd file | head -1` 头部含 `This file is encrypted by dse!!!!` / `已被DSE加密` / `2121 2121`

## 机制（为什么直接改不行）
DSE（DSE.app）是**透明加密**：只加密**白名单进程**（WPS/Office 等）写出的文件；终端写入的是明文，终端读加密文件得到密文。推论：
- 终端无法直接解析原文件 → 必须借道白名单进程（wpscli）或 WPS 备份
- 编辑产物用终端写回 → 明文，WPS 能正常打开（用户保存时 DSE 会重新加密，无感）

## 读取内容（二选一）
1. **WPS 自动备份（最快，明文 docx）**：
   `~/Library/Containers/com.kingsoft.wpsoffice.mac/Data/.kingsoft/office6/data/backup/`
   同名 `.wps` 文件是明文 docx（PK 头），按时间戳取最新。⚠️ **备份可能比当前文件旧**（用户保存后 WPS 未必即时备份）——需与当前内容对比确认差异（见验证）。
2. **wpscli 转 PDF（以当前文件为准）**：
   `/Applications/wpsoffice.app/Contents/MacOS/wpscli word2pdf <加密.docx> --output out.pdf`
   wpscli 是白名单进程，可透明解密。输出目录必须用户可写（`/tmp` 会被 Permission denied → 用 `~/Documents/Hermes/` 等）。

## 编辑 docx（排版/内容修改）
1. 拿明文底稿：WPS 备份 `.wps`（复制为 `.docx`）作格式基底；wpscli 转 PDF 作内容参照
2. `unzip -q base.docx -d unpacked/`，`find . -type l -delete`
3. 改 `word/document.xml`：python 正则定位段落（按文本匹配）、字符串替换；**不要 pretty-print/格式化 XML**（破坏 OOXML）
4. 重新打包：`cd unpacked && zip -Xr ../out.docx .`（从解压目录内打包；先删旧目标）
5. 校验：`zipfile.ZipFile.testzip()` + wpscli word2pdf 渲染 + 文本对比（见验证）
6. 覆盖原文件前先 `cp` 备份原加密文件到安全目录

## docx 排版风格匹配（用户改完内容排版乱时的修复套路）
从现有 XML 提取格式规范，再套用到新段落：
- 字号 `w:sz` 单位 half-point：32=三号16pt、27=小一13.5pt、24=四号12pt、22=五号11pt、19=9pt
- 大标题（一、/4.x）：sz=32 粗体 蓝 `#1B6CA8` + `pBdr bottom` 下边框 + spacing before=360 after=160
- 小节标题（▎x.x）：sz=27 粗体蓝（▎用 1B6CA8，编号文字用 144E7E）
- 三级标题（x.x.x）：sz=24 粗体蓝
- 正文：sz=22、Calibri/微软雅黑、`#262626`、非粗体（`<w:b w:val="0"/>`）、`ind firstLine=440`
- 重建段落保留原 `w14:paraId`；`&` 转义为 `&amp;`

## 陷阱
- **不要驱动 WPS GUI**（computer_use 点菜单/另存为）：用户明确反感（"你为啥非得操纵WPS呢，你直接自己改不就得了"）。用 wpscli / 备份代替
- WPS AppleScript：`open` 可以，但 `document 1` / `count documents` 不支持；System Events 需要辅助功能权限（报 -1728）
- `read_file` 对含超长行的 .md/.xml 误判 binary → 用 python 读
- 覆盖加密原文件前必备份；明文写回原目录后 WPS 打开正常

## 验证
- 内容对比：两版都 wpscli 转 PDF → PyMuPDF `get_text()` → 各自 `re.sub(r'\s+','',t)` 规范化 → difflib.SequenceMatcher 找真实差异（PDF 换行伪影 vs 真差异；注意表格单元格文字被拆行）
- 视觉：`page.get_pixmap(dpi=150)` 存 png → vision 检查层级/对齐
- 结构断言：sz/bold/文本逐项校验（粗体判断：`<w:b/>` 或 `<w:b w:val="1"/>`，`<w:b w:val="0"/>` 是非粗体）
