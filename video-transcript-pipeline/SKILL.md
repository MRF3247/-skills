---
name: video-transcript-pipeline
description: Use when 视频链接要转写逐字稿并归档 Obsidian。
---

# 视频转写与归档管线

## 触发
用户给视频链接（单条/多条）要求：转写成文字、做笔记、存 Obsidian、存档。
也覆盖**本地批量视频**（已下载的课程 mp4 一整个文件夹）要逐节课转逐字稿 —— 见「本地批量课程视频」。

## 环境
固定 `/Users/Jin/Documents/Open Programs/whisper/`（uv venv）：`mlx-whisper` + `yt-dlp` + `imageio-ffmpeg`
- 转写：`transcribe_any.py <wav> <out.json> <lang>`
- 字幕解析：`parse_subs.py`
- 校对翻译：`process_doc.py <in.txt> <prefix> <en|zh> <ctx_file>`
- 组装：`assemble_batch.py`（改 VIDEOS 列表后运行）

## 中文音频走 FunASR，别用 whisper（实测 2026-10）

**选型铁律：中文课程/讲座 → FunASR；英文字幕/播客 → mlx-whisper。** 同一节中文医学课实测：

| | mlx-whisper large-v3 | FunASR paraformer-zh |
|---|---|---|
| 18 分钟音频耗时（M1 Max） | 174s | 336s（慢一倍） |
| 标点 | 无（全文连写） | 自带标点+句级时间戳 |
| “解螺旋/生信/检索式/知网/摘要” | 全错（解罗旋/生性/检索师/之网/专要） | 全对 |

whisper 的中文错法是**专业词全军覆没**，不是润色能救的级别，宁可慢一倍。

环境：`/Users/Jin/Documents/Open Programs/funasr/`（`funasr 1.4.17` + `torch 2.15`，模型缓存 `~/.cache/modelscope` 约 2.1GB，首次自动下）

```bash
# 批量（一次加载模型循环跑，别逐文件起进程——模型加载就要 40s）
.venv/bin/python batch_transcribe.py <wav目录> <输出目录>
# 术语校对（DeepSeek，只改听错的字）
.venv/bin/python proofread.py <in.json> <out.json>
# 出可读 md（按 260 字合并成段，FunASR 逐句排会碎）
.venv/bin/python make_md.py
```

性能基准：14 节 / 2h23m 音频 / 40k 字 → 转写 44.7 分钟（≈ 1/3.2 实时），CPU 转，不占 MPS。

### FunASR 四个必踩的坑

1. **必须传 `hotword`**（空格分隔），否则专有名词识别明显变差（不传时“解螺旋”→“解螺学”）。
2. **必须传 `sentence_timestamp=True`**，否则返回只有 `text` + 字级 `timestamp`（长度还对不上），拿不到句子边界。
3. **必须传 `log_level="ERROR"`**，否则进度条 + INFO 把 stdout 淹掉，看不到自己的 print。
4. **别从 transcribe.py import 常量**：它顶层就 `wav = sys.argv[1]`，一 import 就执行整个转写流程。常量在 batch 脚本里自己定义。

### 残留瑕疵：标点会插在词中间

FunASR 在**停顿处**加标点，停顿有时落在词中 → `期，刊`、`数据，库`、`知，道了`。约占 5%，不影响理解，但正式引用/RAG 前需处理。LLM 逐句校对本只能修一部分（跨句断字它看不到）。

### 中英混说的英文术语 FunASR 也搞不定

音频里念英文（PubMed / Web of Science / MEDLINE / Embase）会变乱码（power mind、拍卖的、泡卖、麦拉、麦当兰）。**必须做 LLM 术语校对**：给 `proofread.py` 一份“误写→正写”对照表（PubMed 的误写有十几种，全列上），只让它改错字、禁止润色。校对后 PubMed 命中从 0 → 50 次、MEDLINE 全对。

## 流程（按优先级）

1. **先查字幕**：`yt-dlp --list-subs <url>`
   - 有 `en` 自动字幕 → 下载 json3（**省去 Whisper，YouTube ASR 质量优于本地模型**）
     `yt-dlp --skip-download --write-auto-subs --sub-langs en --sub-format json3`
   - 无字幕 → 下载音频 → 转 16k wav → mlx-whisper 转写
2. **转 wav**：`ffmpeg -y -i x.webm -vn -ac 1 -ar 16000 -c:a pcm_s16le x.wav`
3. **校对+翻译+摘要**（DeepSeek，每 12000 字符分块，块间 sleep 2s）
4. **组装**：中文摘要 + 中文逐字稿 + 英文逐字稿（中文视频则两段式）
5. **入库**：Obsidian `1-INBOX/`，编号接续根目录最大编号

## 本地批量课程视频（无链接，已落盘 mp4）

用户说「把这些课程做一下 stt / 转逐字稿」时。**先回答「本机装的是什么」再动手**，查 `~/Documents/Open Programs/` 而不是凭印象或用户记忆：

- `whisper/`：mlx-whisper（英文/带字幕场景）
- `funasr/`：FunASR paraformer-zh（**中文默认走这套**，已装好并带一批脚本）

用户常记成「以前部署过 funasr」或反过来说「只装过 whisper」——实际两个都在（FunASR 是后装的）。先报现状再选路，别顺着记忆编流程。

1. 音频抽出来，单声道 16k（转换≈1 秒/节，很快）：
   `ffmpeg -y -loglevel error -i "01_xxx.mp4" -vn -ac 1 -ar 16000 -c:a pcm_s16le audio/01.wav`
2. 逐节转写，**每节一份独立 json**（`transcribe_any.py <wav> <out.json> zh`），节间互不依赖，可并行；失败只重跑那一节。
3. 抽一节做**质量抽检**再批量：读 `json.text` 前 800 字，拿平台课程简介/目录里的正确术语对照。**中文专业课程的首轮稿几乎必然不能直接交付**，先证明它会错成什么样，再决定用不用 LLM 校对或换模型。

### 把视频里的 PPT 抠出来，跟逐字稿对应（实测 2026-11）

课程/讲座视频要“PPT ↔ 逐字稿”对照时：

```bash
# 1) 场景检测提帧 + 去重 + 时间区间 + 逐句挂页号
.venv/bin/python extract_slides.py <视频mp4> <XX_proofed.json> <输出目录>
# 2) 清理 <2s 碎片页（演示操作类视频会切出一堆 1.8s 的闪帧）
.venv/bin/python clean_slides.py <输出目录> 2.0
# 3) 页面文字 OCR（macOS Vision，先 swiftc -O scripts/ocr_vision.swift -o ocr_vision）
.venv/bin/python ocr_slides.py <输出目录>
# 4) 生成「画面+页面文字+口述」三层 md
.venv/bin/python make_md_slides.py
```

产出：`slides/xx_00N.jpg`（页图）+ `XX_slides.json`（页 start/end、OCR `text`/`header`、每句 `slide`）+ `XX_with_slides.md`。14 节 / 143 分钟 / 220 页 / 页面文字 12.7 万字实测。

**完整参数、清洗规则、代码要点见 `references/ppt-slide-extraction.md`；Vision OCR 源码在 `scripts/ocr_vision.swift`（复制出去 `swiftc -O` 编译即可，本地免费、0.5s/页）。**

**最值钱的一条**：PPT 上的字比 ASR 准一个档（讲师自己确认过的原文）。要修 `回湖至→回溯至`、`黄文→英文` 这类错，拿同页 OCR 文字反校该时段的逐字稿，比继续扩术语表有效。

**关键参数与坑：**

1. **场景检测阈值用 0.08**，不是 0.4。0.4 在两小时的课件视频里只出 2 张；0.08 才能抓住淡入淡出的翻页。
2. **首帧要单独截（t=0.5s）**：开场常是静止标题页，不触发场景切换，不补截就会丢掉前几分钟（实测 02 节前 59 秒全空）。
3. **去重用双哈希**：`aHash ≤ 8 或 dHash ≤ 6` 才判同页。只用 aHash 会把「同一页加了红框标注」（不同页，必修保留）误删；只用 dHash 会漏掉纯白底轻微变化的重复页。比较时只往前看 2 页（讲师真翻回旧页要保留）。
4. **`~/.local/bin/ffprobe` 其实是 ffmpeg 的软链**，用 ffprobe 参数拿不到时长（返回空→最后一页 end=0）。改用 `ffmpeg -i` 解析 stderr 里的 `Duration:`。
5. **重跑前先删旧图**：页数变少时旧文件残留，拼图/引用全错位。
6. **演示操作类视频页数会爆多**（点浏览器/切窗口，30+ 页/10 分钟），页数多不代表错；纯讲授的节可能只有 2 页。

### 用页面文字反校逐字稿（PPT 校准，必做）

```bash
.venv/bin/python proofread_slides.py <逐字稿目录> [节号]
```

把「该页 OCR 文字」+「该页口述句子」并排给 LLM，只修被页面文字证实的错字。14 节实测修 61 处（`心房颤抖→心房颤动`、`挑圈连靠→挑圈联靠`、`仙桃血书→仙桃学术`、`哈的基因→Hub gene`、`利标准成→专利、标准、成果`）。

**三道闸门缺一不可：**

1. **防篡改闸门**：`difflib.SequenceMatcher(None, 原句, 新句).ratio() < 0.6` 的改动一律回滚。不加这道，模型会用页面文字把整句换成不相干的句子（实测把「五细细胞粒进入 BEAS 二 b 细胞…」换成「说一遍大家在这节课里能看懂文献…」）。真错字只占几个字，改动幅度大就是出事了。
2. **空白噪声过滤**：`re.sub(r"\s+", "", t)` 相等则丢弃。否则几十句“修正”只是句尾多了空格/换行（09 节 134 句“修正”里真错只有 6 句）。
3. **每次从原始稿重置基准**：跑前把 `segments[i].text` 从 `XX_proofed.json` 写回去，否则第二次基于改过的稿再改，越改越偏且不可重复。

prompt 硬约束：“页面文字没涉及的词一律不改”+“不合并/不拆分/不增删句子”+“拿不准就不改”。OCR 自己也会错（小字、表格数字），不能当唯一真理。

## 坑

- **`glob` 扫不到文件不会报错，脚本会静默零处理退出**——退出码 0、输出为空，看着像“跑完了”。OCR 这一环实测踩过：`ocr_slides.py <目录>` 传成了父目录（`*_slides.json` 实际在 `<目录>/slides/` 子目录），循环体一次没执行，一页没处理。**判据只能看产物，不能看退出码**：跑完统计 `slides[*].text` 非空页数，或产物文件数。

  同时记住目录层级：`extract_slides.py <video> <json> <out_dir>` 的 out_dir 会**再套一层 `slides/`**——图片在 `<out_dir>/slides/`，`XX_slides.json` 在 `<out_dir>/`。找图/拼装时别只翻一层。

- **项目根目录带空格，批量循环里每个路径都要加引号**。`/Users/Jin/Documents/Open Programs/...` 在 `for f in $DIR/*.mp4` 这类循环里不加引号会被拆成 `Open` 和 `Programs/...`，报 `/Users/Jin/Documents/Open: No such file or directory`。写成 `for f in "$DIR"/*.mp4; do ffmpeg -i "$f" ...; done`，变量引用一律包引号。调试时先 `echo` 出拼好的命令再执行，比看 exit code 快。

- **抽帧不必等转写完成，传占位 json 就能先跑**。`extract_slides.py` 只在拿不到视频 Duration 时才读 `trans_json`，平时只往里写 `slide` 字段。转写要 2–3 小时、抽帧只要 30 分钟，**一开始就 `echo '{"segments":[]}' > trans/_placeholder.json` 把抽帧并行起来**，转写完再重跑挂时间（或直接后处理填 `slide`）。两件事串行会白白多等一小时。

- **演示类课程的抽帧会失控，但那些不是重复帧**。阈值 0.08 在纯 PPT 课上正好（26 分钟 17 页），但在「讲师在浏览器/软件里实操」的课上会疯长（43 分钟抽出 112 页、14 节共 955 页）。先别急着调阈值或去重：抽查发现这些帧的 OCR 文本全是浏览器地址栏、WPS 菜单栏（「文件 开始 iSlide 插入 绘图…」）、网址切换，**相邻帧确实是不同画面**，按文本相似度去重只能删掉 4/951 页——因为打字/滚动的帧文字真实不同。

  正确的处理：① 这些演示帧对教材写作价值很低（教材本来就不用课程截图，配图是重绘的），保留但不加工，写作时只作上下文参照；② 真要减页得换判据——提高场景阈值到 0.15–0.2，或用「OCR 文本里是否含标题层级/项目符号/大字号标题」筛幻灯片真页；③ 别用相似度阈值 0.92 去硬删，会误删真页且收益微乎其微。

- **DeepSeek 逐句校对按 6000 字分批会被 max_tokens 截断**，症状是 `[1/2] 失败 JSONDecodeError: Unterminated string` 整批回退原文（看着“跑完了”实则一半没校）。改成 **3000 字或 150 句封顶**，719 句拆 5 批全成功。校对结果写在顶层 `text_proofed`（全文），`segments` 里只有 `text`，别去 segments 里找校对字段。实测修正效果：「解罗旋→解螺旋」「深性研究→生信研究」×5。

- ⚠️ **whisper 对中文专业术语的误识别是系统性的，且集中在英文缩写和学科名词上**，不是零星错字。实测一节医学文献检索课（18 分钟）：`PubMed→PowerMind`、`中国知网→中国之网/中国智网`、`生信→生性`、`检索式→检索师`、`摘要→专要`、`解螺旋→解罗旋/解模学`、`冠心病→关心病`。**这类错必须靠术语表批量替换 + LLM 带正误对照表校对**，人工逐字改 2 小时以上的课不现实；纯标点/断句差是正常现象，术语整体错位才是要处理的信号。
- **换 ASR 引擎前先 A/B，同一节音频跑两套再定**：不要仅凭某引擎「更适合中文」的宣传就把整批押上去。中文已 A/B 过，结论是 **FunASR 胜出**（见上面选型表），不用再试；换到新语种/新领域时这套对比方法照用——看术语错误数，不看流畅度。
- **mlx_whisper 找不到 ffmpeg**：它调用 PATH 里的 `ffmpeg`。用 imageio 的二进制建软链：
  `ln -sf $(python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())") ~/.local/bin/ffmpeg`
  同时软链 ffprobe，否则 yt-dlp 转码也失败（webm 可直接用 ffmpeg 转 wav，不必依赖 yt-dlp 后处理）
- **YouTube 自动字幕无标点、全小写**：校对提示词必须明确要求「补标点+恢复大小写」
- **中文转写需二次校对**：首轮常残留系统性误识别（如「前空间」→「潜空间」、「X-Wall」→「Astra」）。
  做法：先看 summary 得出正确术语，用 `reproof_cn.py` 带「正误对照表」重跑，验证残留计数归零
- **JSON3 重复段**：自动字幕有滚动重复，解析时需去重
- **编号接续**：组装前扫描 `[0-9][0-9][0-9]-*.md` 取最大值 +1
- **文件名冒号**：标题含 `:` → 替换为 ` -`（macOS 兼容）
- 转写性能参考（M1 Max 32GB / large-v3）：**中文约音频时长的 1/6**（18 分钟→174 秒，421 段）；技能早期记录的 1/18（86 分钟→291 秒）是英文/快语速场景，排期按 1/6 估才不踩空。

## 交付格式

```markdown
---
title/author/平台/source/duration/发布日期/tags/转写方式
---
# 标题
> [!info] 视频信息
## 📌 一、中文摘要
## 📝 二、中文逐字稿（AI 翻译）
## 📖 三、英文逐字稿（AI 校对版）
```

摘要自带的一级标题需降级（`#`→`###`、`##`→`####`）避免与文档大纲冲突。

## 得到大脑链接笔记 → Obsidian（import_getnote.py）

用户说「把得到大脑摘录的链接笔记整理到 INBOX」时：

1. `getnote notes --limit 50 -o json` 分页拉到日期早于目标日为止，筛 `note_type=link` + `created_at` 匹配
2. 每条 `getnote note <id> -o json`，关键字段：
   - `content` = **AI 智能总结**
   - `web_page.content` = **原文**（带时间戳逐字稿）
   - `web_page.url` / `attachments[0].title` = 源链接与**原稿标题**
   - `children_ids` = **用户追加的笔记**（手记，`note_type=plain_text`）
3. **追加笔记必须融入 AI 总结，不能单列**（用户明确要求）：用 DeepSeek 提炼知识点 → 插入语义对应章节；无对应位置才在「💡 关键洞察」后新建小节；
   **禁止元叙述字样**（“用户手记/追加笔记/补充/含个人追加要点”也不能出现在章节标题里）
4. 追加笔记里的图片（`get-notes.umiwi.com` 签名链接，月内过期）→ 立即下载到 INBOX 并用 HTML `<img>` 嵌入对应位置
5. 文件名：只替换 `/ : |`（`|` 会破坏 wikilink），**保留 `? "` 等**；不要用 `[\\/:*?"<>|]` 全替换，会把标题弄难看
6. 并行 5 线程拉取；CLI 偶发返回空 stdout 导致 `Expecting value` → 重试即可
7. `content` 与标题均为空的笔记 = 得到大脑处理失败（多为无字幕长视频），跳过并告知用户

## Obsidian INBOX 规则（用户强制）

- 笔记**平铺根目录 + 编号**（`001-标题.md`），**禁止**平台/博主子文件夹
- 图片附件同样平铺，命名 `<笔记编号>_原名.jpg`
- 笔记内图片用**库根相对路径** wikilink（`![[1-INBOX/234_01.jpg|220]]`）——
  正因如此，移动 md 文件**不影响**图片显示，但移动图片必须同步改链接
- 按 mtime 升序 = 入库先后顺序
- 操作前先存映射表（JSON）到备份目录，可回滚
