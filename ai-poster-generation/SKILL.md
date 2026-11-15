---
name: ai-poster-generation
description: 用 libtv AI 生图引擎批量生成小红书/社交海报，抽卡选优、版本编号、复盘迭代提示词。
---

# AI 生图海报批量生成（libtv 引擎）

用户有 LibTV 账号（进阶版 VIP），生图引擎通过 `libtv` CLI 调用 Liblib 云端画布，**不是本地模型**。命令手册见用户自装的 libtv-cli skill（勿改）；本 skill 记录**用生图引擎批量做小红书/社交海报的完整方法论**。

## 铁律（用户明确纠正过，第一条是重灾区）

1. **用户装了 libtv skill 就是要用 libtv 生图引擎出图**——不要自作主张用 HTML/CSS 排版替代。生图引擎排版能力不足时才允许分图层兜底（见下），但主视觉必须走引擎。
1b. **HTML 分层排版必须真用排版参考手法，不能只精致化旧框架**（用户 2026-08-06 强纠正：「你这个排版我完全没看出你有用我之前给你找的那些排版参考啊」）。v4 把「上图下文+底部贴背景块」做得再精致（接缝渐变/徽章/卡片描边）也是错的——用户一眼看穿。v5 正解见 references/layered-composition.md 的「v5 定稿」一节。
1c. **用户最终路线判定（2026-08-06）：HTML 排版也不行，要「AI 生图引擎直接出带文案整图」**（用户原话：「我觉得用html让你排版果然还是不行，要么你直接设计和排版都用AI生图引擎做吧」）。即：插画与文字排版都交给生图引擎一次性生成，不要再做 HTML 分层。选引擎时注意：**MiniMax image-01 中文长文案必乱码**（实测 2 次：插画 8/10、文字 1/10 全伪汉字，不可用于带中文文案整图）；**libtv doubao-seedream-5-0-pro 是中文排版最强引擎**（历史实测中文文案 10/10），带文案整图优先它。MiniMax 只可用于无字插画/英文短文案。完整实测与脚本见 references/ai-fullposter-direct.md 与 gen_ai_fullposter.py。
2. **一套内容（如小红书笔记 p1-p6）必须同一种风格生成整套**，换风格再整套重新生成，不能每张各搞一套。
3. **每个版本都要编号保存**（版本库目录 + 选版说明.md），用户会自己挑选；**抽卡是标准操作**（count=2/4 一次出多张对比）。
4. **生成后必须视觉目检评分**（10 分制），不美观继续抽下一版或切换引擎，直到出好图。
5. **提示词要复盘迭代**：每轮失败记录教训，用户抽查给意见时要综合改进并重新验证。
6. **排版全交引擎不可靠时，分图层兜底**：AI 生成无字/少字背景层，文字层用本地排版（HTML/PIL）精排叠加。
7. **配合产出模式（用户 2026-08-07 确立「我们配合来进行产出」）**：每个流程环节都要让用户确认 OK 再往下推进——选风格给推荐清单（含主观排序和理由）→ 定设计出设计稿（风格锚点+留白+元素组合，逐项列明待确认问题）→ 抽卡生成后给用户看 → 用户拍板才归档。**画面元素按内容主题确定**（用户原话「画面元素根据我的主题来确定」）：先问/推主题相关元素，不要套通用医学元素（DNA/细胞）——如「文献检索」主题用放大镜+文献摞+精准定位箭头，而非 DNA 螺旋。不要自己一路跑到底再汇报。**用户不满意时不要反复自己重写 prompt：让用户给「觉得对」的样张 → kimi 倒推风格 → 重新生成**（实测是唯一把风格还原度从「0 关系」拉到 8-9/10 的路径；详见 references/cover-iteration-lessons.md）。**审图必须用挑剔模式**（「用挑剔的审美眼光，直说缺点，与 Cell/Nature 对比，逐维打分」），默认审图会虚高（v2 审 9.1/10 用户却说「好丑」）；机器分是参考，用户观感是终审。

## 标准流程

0. **定风格 + 留白一体设计（用户 2026-08-07 拍板）**：定风格时就同步设计留白，**生图直接出无文字版本**，文字用户后期自己加（用户原话：「文字我后期自己加，我感觉你加的也不太好看」）。**留白位置统一规定在上半部分**——顶部留出干净的纯色/同色系渐变区（约占 30%，25%-40% 均可），供标题文字使用；提示词写「画面上方留出干净留白区，无任何元素，适合后期叠加标题文字」。不要单独做「留白设计」步骤，不要生成带文字版本。**留白区颜色必须跟随主底色、与主底完全一致**（2026-08-07 v4/v5 实测：S4 深蓝风格下米白留白贴深蓝主底 = 割裂 7/10，改纯深蓝留白 = 统一 9/10；留白不是固定米白/白色）。**生图尽量纯 prompt、不挂参考样张**（用户 2026-08-07 明确：「你尽量不要用参考样张，依靠纯prompt来完成生图指令」）——参考样张只用于定风格锚点（媒介/配色/元素/气质），写进 prompt 描述即可。注意：早期「纯 prompt 出 9/10」记录是 kimi 宽松审图分数，**用户实际否决了**（「好丑」）——详见「封面迭代教训」。
1. **定风格套系**：从 视觉风格家谱.md（Obsidian 库 视觉风格参考/）挑风格家族，取其中英风格提示词做底色。小红书医学科研赛道已验证好用的：矢量扁平现代插画（深墨绿+金黄，斯坦福医学海报调性）、现代极简/包豪斯（米白+黑白+红点缀+网格）、点彩/半色调（米白纸底+朱红）。风格拓展渠道：Pinterest（pinterest_daily.py）+ Behance（behance_collect.py，浏览器提取项目封面 URL 喂入）——国外医学画风优先（编辑插画/科学水彩/瑞士国际主义/复古未来/等距/孟菲斯/装饰艺术/期刊封面）。
2. **建画布并绑定**：`libtv workspace create` → `libtv project create` → `libtv project use <uuid>`（在专门的工作目录执行，.libtv/project.json 落该目录）。
3. **上传参考图**：`libtv upload "参考图-xxx" -t image -f <path>`（原示例笔记上传为资源节点）。
4. **选引擎**：中文海报优先 doubao-seedream-5-0-pro（Seedream 5.0 Pro，原生多语言排版）；完整引擎对比见 references/libtv-image-generation.md。
5. **写提示词**：完整文案显式内嵌 + 【区域】定位 + 颜色用自然语言。模板见 templates/poster-prompt-template.md。
6. **抽卡生成**：`libtv node create "节点名" -t image -s "model=Seedream 5.0 Pro" -s ratio=3:4 -s quality=2K -s count=2 -s modeType=image2image --left "参考图-xxx" --prompt "..." --run`。**`--run` 是同步阻塞**，等待进程退出读 stdout JSON，不要包轮询。
7. **下载（无水印）**：**不要用 `libtv download`**——它会叠加「AI生成」+「LibTV」水印，且 `--without-ai-watermark`/`--vip`/`LIBTV_DOWNLOAD_IS_VIP=1` 实测全部无效。正解：`libtv node <节点名>` 查询拿 `data.url[]` 的 CDN 原 URL → curl/urllib 直接下载 = 无水印原图（已验证四角全干净）。批量脚本见 scripts/fetch_originals.py。文件落 cwd 下 `<节点名>_N.png`（按 count 编号）。
8. **目检评分**：**用 MiniMax 视觉审核（审美导向），不要用 OCR**——OCR 只能看文字、没有审美（用户明确纠正）。vision_analyze 逐张检查 风格还原度/衔接/配色协调/可读性/层级，记 10 分制。
9. **选优归档**：最优卡 cp 到 `精选_套系名/01_xxx.png...`，写 选版说明.md（每张评分+选择理由+备选清单+复盘记录）。
10. **复盘改进**：把 vN→vN+1 的提示词改动和效果写进选版说明，供下次直接复用。

## 提示词工程要点（实测）

- **不要把色号写进提示词**：`#0E4C4C` 会被引擎当正文渲染成乱码文字（v1 翻车主因之一）。
- **不要依赖引擎 OCR 参考图文字**：写"保持原图文案不变"会导致正文内容（列表/标签）整段丢失。完整文案必须逐条显式列出。
- **长文案易丢标点/错字**：实测出现"哪怕→哪帕"、"漏掉→掉漏"、逗号缺失。文字越多错率越高 → 抽 2 卡选优可有效规避（同提示词两张，一张 10/10 一张 7.5/10）。
- **【区域】定位法**：提示词里用【顶部】【标题区】【引导段】【信息卡N】【底部】【右侧装饰】描述版式位置，引擎遵循度高。
- **信息卡结构描述**："半透明白底卡片，左侧金色竖条，卡片内黄色小标题X，下接白字：..."，多卡同款可保证系列一致性。
- **系列一致性**：每张卡的提示词尾部统一贴同一段风格描述（配色+媒介+质感），整套才像一套。
- **成品要有「活人感」，别像 AI 一键生成的**（用户 2026-08 通过投喂「活人感封面」链接表达的审美倾向）：小红书信息流里「有烟火气、像真人随手做出来」的图点击率更高。手法：手写感/马克笔感标题（错落排布、不追求绝对对齐）、主体加白/主题色 cutout 描边（打破死板方框）、星星/箭头/对话框/小标签点缀、高对比撞色、允许"不规整"。反面：过于规整的工业感、完美对称、像素级对齐 = 「AI 感」。
- **文字穿插（text occlusion，2026-08 从「大字杂志感人物海报」笔记学到）**：把大字放到插画/人物「后面」，主体遮住字母一部分，平面瞬间变立体——这是 GQ/Vogue 封面用了几十年的老招，眼睛自动读出「背景字 → 人物 → 观者」三层 Z 轴纵深，被遮住的文字大脑会脑补、存在感反而更强。落地：HTML 层 z-index（插画最前、文字中、背景最后），或 libtv prompt 里描述遮挡关系。配合大字三件套（压缩字+重字重+斜体，少一个就弱一半）和文字贴边布置（竖排左缘+右上/右下小字形成外框，中间留给主体）。
- **JSON 结构化提示词**（2026-08 从 VigoCreativeAI 提示词学到）：style_name/style_summary + environment_variables（SUBJECT/MAIN_TEXT/LOCATION 等变量化）+ STYLE_FIDELITY_ANCHORS（必须保留的关键风格特征）+ SOURCE_CONTENT_TO_AVOID（禁止复刻的原始元素）+ ASPECT_RATIO。这套「变量 + 锚点 + 禁忌」结构比平铺描述更稳定，可套用到 libtv prompt。
- **视觉分析任务：只看风格不读文字**（用户 2026-08-07 明确纠正「从视觉风格的角度来分析哈，不是说让你提取文字什么的」）：分析参考图/样张的构图、留白、配色、质感、气质时，prompt 开头写「【只看视觉风格，不读图里任何文字】」，判断标准基于视觉元素（医学插画/细胞图形/学术版式/留白比例等），不要 OCR/转录图上文字。产出可复用 AI 生图提示词时同样只描述视觉特征。

## 关键坑

- **图生图必须显式 `-s modeType=image2image`**，否则校验失败："图片生成节点须为图生图模式才允许图片参考入边"。
- **批量脚本别用 bash 双引号包提示词**：提示词内常有半角双引号（如 `"STEP 01"`），外层再包 `"..."` 会提前闭合引号、整行被 shell 拆成命令（报 `command not found`、`No such file or directory`）。用**单引号**包提示词，或直接用 **Python subprocess 传参**（list 参数，彻底免疫；实测脚本从 bash 改 Python 后一次跑通）。
- **`-s model=` 只接受 modelName**（如 "Seedream 5.0 Pro"），传 modelKey 会报错；用 `libtv model search --type image` 查。
- **quality 各引擎范围不同**：doubao 只支持 1K/2K（传 4K 直接校验失败），seedream-4 支持 2K/4K。先 `libtv model <key>` 看 schema。
- **ratio=3:4** 是小红书竖版标准；引擎产出实际像素由引擎决定（doubao 2K = 1776×2368）。
- **下载文件名**：无水印下载（fetch_originals.py）输出 `<节点名>_N.png` 到 cwd，需手动 mv 进版本库并编号。
- **残余断行瑕疵**（词被切开、"被引频次"断行）：引擎通病，精选时可接受，发布级需分图层精排。
- **节点残留**：批量脚本中断后，已创建的节点可能只有部分 URL（生成没跑完），重跑前先 `libtv node delete <名>` 清掉，否则 `create` 报同名已存在。
- **去水印的失败路径（勿再走）**：① OpenCV inpaint（Telea/NS 各半径）对「文字下有内容」区域残留明显（5.5/10）；② libtv 编辑模型（qwen-edit / nebula-ultra / doubao-seedream）一律不执行水印擦除（1-3/10，品牌保护或策略保守）；③ LaMa（simple-lama-inpainting）权重是 CUDA trace 的 jit 模型，Mac CPU/MPS 加载报 NotImplementedError。唯一正解是步骤 7 的「查 URL + curl 下载原图」。
- **插画下方留白不能生硬**（用户明确要求）：留白区要与插画同色/同色系渐变过渡，不能是突兀的白色或异色块。反例 S4-p1（下方纯白与深蓝画面割裂）；好例 S2/S3（留白与画面同色系自然融合）。prompt 里写「下方留白区与画面整体同色系渐变过渡、自然融合」，不要只写「空白区」。
- **libtv 报错 1200000136「算力不足」= 云端 GPU 资源池瞬时状态，不是积分不足**（2026-08-07 实测纠正：用户确认「积分已经刷新」后 Seedream 5.0 Pro 仍连续报算力不足，切 **Seedream 4.6（20s 短耗时档）立即生成成功**；说明是资源池高峰占满而非账户欠费，且可能持续数十分钟）。处置顺序：① `libtv node delete <空节点>`（失败重试必先删，否则同名冲突）；② **切短耗时引擎**（Seedream 4.6 / Seedream 5.0 Lite / Z-image Turbo 等 10-25s 档，`libtv model search --type image` 查）——实测最快见效；③ 稍后（≥45s）重试原引擎；④ 都不行才走 MiniMax image-01 文生图兜底（不能图生图，但详细提示词重绘同风格可接近）。
- **内容合规**：提示词含「古典人体雕像」→ 生成图被 MiniMax 审 422 sensitive（小红书平台也会拦）→ 换纯医学物件（显微镜/细胞版画/DNA 分子网络/化学器皿/期刊元素），重生成后合规。
- **图片敏感审核 422 处置**：原图本身被判敏感时，灰度+224px 缩图也无法绕过（已实测）；正确做法是改 prompt 重生成内容，而不是缩放重试。
- **MiniMax 同画面「人物 vs 图形元素」风格割裂**（用户 2026-08-07 质疑「这个医生的形象和其它元素的画风在两个图层，根本格格不入吗」）：提示词同时描述「医生/人物」+「复古半调网点」时，MiniMax 对**人物执行照片写实优先**（真实肤色渐变、白大褂高光、光滑无颗粒、抠图贴图感），对图形元素执行风格优先 → 两种质感拼贴像两个图层。修复三步：① 人物改成**纯色平面剪影**（英文提示词写 `flat graphic silhouette, no face details, no skin tones, no realistic features`）；② 显式声明 `ALL elements rendered in the SAME <风格> with no exceptions`；③ 用**英文提示词**（MiniMax 对英文风格词遵循度远高于中文）。实测：写实医生版质感割裂 → 剪影版 47/50、质感统一 9/10。代价：剪影丢职业细节（听诊器/白大褂），无字背景层场景足够；要职业符号可加 `stethoscope silhouette` 等图形化元素。

## 相关

- 风格素材来源：visual-reference-pipeline（视觉风格家谱）
- 命令手册：libtv-cli（用户安装，勿改）
- 引擎细节与实测评分：references/libtv-image-generation.md（A 套系 + 失败模式表）
- AI 直出带文案整图（MiniMax 中文乱码实测 + libtv 积分耗尽判断 + gen_ai_fullposter.py）：references/ai-fullposter-direct.md
- 视觉审核模型选型（MiniMax-M3 vs Kimi-k2.5 实测 + 口径一致性规则 + k3 深度分析用途 + kimicode 端点/kimi-for-coding 对比 + 余额查询接口）：references/vision-review-models.md
- **vision_analyze 401（hermes 进程未重启、kimi 切换未生效）时的看图工具**：`python3 /Users/Jin/Documents/Hermes/kimi_see.py <图片路径> "<问题>"`——kimicode k3-256k 视觉问答，key 自动从 `Hermes/APIs/kimicode API.rtf` 读，max_tokens 默认 800（长分析传第 4 参）。2026-08-07 按 DRY 正式化沉淀（此前每次 401 都重写一遍），本会话实测 6+ 次可靠。
- k3 批量深度分析管线（排版参考/风格家谱 → 提示词倒推，41 任务断点续传；默认走 kimicode 端点 api.kimi.com/coding/v1 消耗 kimicode token，**模型首选 k3-256k**——256k 内效果与 k3 相同、消耗减半，用户 2026-08-06 拍板；审图用 kimi-k2.5 thinking disabled。**回写 Obsidian 必须表格内嵌、禁止表格后堆长文**——用户强纠正；含误删恢复路径与幂等教训）：references/prompt-reverse-engineering.md
- 套系B 实测评分与批量脚本教训：references/qa-scores-suite-b.md
- 构图/封面公式/杂志化词汇表（14 构图中英对照 + 封面 3 公式 + 知识卡片排版 + 配色 6 法 + 网感封面公式 + 系列超级符号色，prompt 直接引用）：references/composition-and-cover-vocabulary.md
- 高级配色方案（清新蓝主色+珊瑚橙互补装饰，实测 9/10，含 prompt 写法）：references/high-end-color-palettes.md
- 文字密集参考图读字工具（macOS Vision OCR，zh-Hans+en-US，本地免费）：scripts/ocr_vision.swift
- 提示词模板：templates/poster-prompt-template.md
- Canva 小红书模板批量扒取 + 官方主题分类（无需登录的公开页、og:image 实体反转义、签名 URL curl 下载、20 个 fTheme 枚举、官方/推断双标注）：references/canva-template-scraping.md
- 留白风格（留白六律 + 分析 prompt 模板 + 封面留白优化生成 prompt + 无字背景层引擎选择）：references/whitespace-design.md
- **封面迭代教训（v2→v5 全过程：kimi 倒推样张 > 反复重写 prompt、审图挑剔模式、单一强概念 vs 元素拼盘、留白颜色跟随主底色、机器高分≠用户满意）**：references/cover-iteration-lessons.md

## 排版参考库（用户持续投喂小红书链接）

用户会陆续发「我觉得不错」的小红书排版链接 → **逐条学习并沉淀到 Obsidian**：
`/Users/Jin/Documents/医时知识库/视觉风格参考/排版参考/`（学习笔记 .md + 样张/ 子目录）。

沉淀要点：
- 笔记正文（作者观点/思路）原文保留 + 逐图拆解（内容类型/排版特点/配色/技巧）+ 提炼可执行技巧清单 + **映射到本项目海报的改进方向**。
- **每份笔记必须附原图**（用户 2026-08 明确纠正："这些排版参考学习笔记里都要附上原图"）：多张样张用图网格（`<div style="display:flex;flex-wrap:wrap"><img src="样张/xxx.jpg" width="180" style="margin:4px;border-radius:6px"/>...</div>`，每行 4 张 180px 小尺寸不占地方）；单张用 `<img src="样张/xxx.jpg" width="260" align="right" style="margin:0 0 8px 16px"/>` 右浮动。**图片嵌入一律用 HTML `<img>` 标签 + `样张/` 相对路径，禁止 `![[wikilink|180]]` 竖线语法**（用户 2026-08-07 二次纠正：`![[样张/xxx.jpg|180]]` 生成的笔记被判「原图格式都是错的」；Obsidian 表格内尤其不能用）。逐张分析区每张再配大图 `<img src="样张/xxx.jpg" width="360" style="border-radius:8px"/>`。批量插入参考 排版参考/insert_gallery.py；frontmatter 用 `date:` 而非 `created:`，tags 规范化。生成笔记后自检：grep 确认零 `![[` 残留、img 数量 = 样张数×2（网格+大图）。
- 小红书正文/图片抓取（未登录，实测 9 次全通）：browser_navigate 打开笔记页 → browser_console 执行 `(() => { const s = document.querySelector('script[type="application/ld+json"]'); if (!s) return 'no'; try { const d = JSON.parse(s.textContent); return JSON.stringify({ headline: d.headline, desc: d.description, images: d.image }); } catch(e) { return 'err ' + e.message; } })()` → 拿到完整正文（desc，含全部分段）和 image[] URL → curl 下载（**http 换 https**，否则被拒）。注意脚本标签有两种：JSON-LD（`application/ld+json`，首选，headline/desc/images 都在）和 `window.__INITIAL_STATE__`（页面状态，含更多但不稳定）。图片 URL 路径有两种：`spectrum/`（多数笔记）和 `notes_pre_post/`（部分笔记），curl 下载均有效；单图笔记的 JSON-LD images 只有 1 个 URL。抓取流程图见 references/layered-composition.md 的「排版参考抓取」备注（本次 15 条链接全通）。
- **文字密集的参考图用 macOS Vision OCR 读字，MiniMax 只管审美**（用户 2026-08 建议，已实测）：提示词截图/信息图/梗图类，Vision OCR（VNRecognizeTextRequest，zh-Hans+en-US，accurate 级）逐字转录比 MiniMax 视觉准得多；MiniMax 视觉只用来评风格/版式/配色。脚本：`swift scripts/ocr_vision.swift <图>`（本 skill 自带，本地免费，多次实测中英混排梗图文案全部读对）。
- 先建文件夹结构再填内容：`排版参考/排版学习笔记_<主题>.md` + `排版参考/样张/排版参考_NN.jpg`。沉淀完更新 `00_索引.md`（笔记列表 + 跨笔记通用共识）。
- **k3 深度分析的回写格式：内嵌，不要追加**（用户 2026-08-06 强纠正，家谱和排版笔记同规则）：分析结果要放在每张样张对应的行/位置里，绝不能在文档末尾堆一大段不分图的长文。家谱表格用 k3_embed_table.py（表头加列+行内嵌单元格）；排版笔记若用 k3 重新分析，同样按样张对应内嵌，不要「k3 深度优化版」整段追加。详见 references/prompt-reverse-engineering.md 的「回写格式」。
- **家谱表格格式（用户 2026-08-06 再次强纠正「你还是没理解我的意思」）**：每个家族文档**只保留一个 4 列表格：样张｜名称｜元素｜风格提示词（中文）**。不要英文提示词列、不要 k3 深度分析列、不要表格后堆任何长文。风格提示词**全部用 Kimi 重新生成**（用户原话：「你的风格提示词要用kimicode重新分析生成…那就用kimi替代它啊」），脚本链：`Hermes/kimi_style_prompts.py`（逐张生成→`风格提示词_kimi.json` 即时落盘可断点续传）→ `kimi_style_prompts_retry.py`（空返回自动重试 3 次）→ `rebuild_family_tables.py`（重建 4 列表格，缺 kimi 的用旧值兜底并警告）。**kimi 批量调用偶发空返回**（非报错、content 为空，解剖/敏感图也会偶发，说明是瞬时错误不是拦截）——必须重试，重试后绝大多数成功；**短输出（<10字）是 max_tokens 截断，加大到 500 重生成**（2026-08-06 全量 340 张实测，详见 references/prompt-reverse-engineering.md「两类失败要区分处理」）。
- **批量处理脚本的备份/恢复铁律**（2026-08-06 事故）：`mv 备份 原目录` 会**消耗掉备份**，之后 `rm -rf 原目录` 就是删无备份——rm -rf 前必须确认备份真的存在（`ls` 验证）。恢复路径：家谱文档可从 `浏览器采集_识别结果.json`（340 条，Hermes/）用 `merge_family_doc.py` 全量重建，样张图在 vault 样张/ 不丢。表格行循环里**禁用 `continue` 跳过已处理行**（会跳过 `new_lines.append` 导致整行被删）；行级幂等检查「单元格已存在」（`'<td...>' not in line`），不能全文搜索（正文引用会误判）。
- **不要 import 别的生成脚本复用函数——会执行它的 main**（2026-08-07 事故）：为复用 `merge_family_doc.py` 的 classify() 用 `spec.loader.exec_module` import，结果整个脚本重跑，家谱文档被从「4 列 kimi 版」覆盖回「5 列 MiniMax 旧版」（340 张全退回）。教训：① 复用前先确认脚本无顶层副作用（`if __name__ == "__main__"` 保护）；② 稳妥做法是**复制函数体**而不是 import；③ 跑完任何「分类/重建」类脚本后必须抽查目标文档是否被意外改写（行数/列数/内容特征），本会话靠重跑 rebuild_family_tables.py 恢复。另外家谱表格 alt 无扩展名，从文档提取文件名分类时要扩展名探测循环（`.jpg/.png/.webp/.jpeg/.gif`，gif 易漏）。
- 封面发布前自检（来自「测封面」笔记）：缩略图 3 秒测试——把成品缩成信息流大小，检查标题在缩略图下是否清晰可读、对比是否足够（缩略图里看不清的字 = 无效字）；点击率标准 5% 优秀 / 3-5% 合格 / <3% 重做。

## Pinterest 医学风格素材采集（用户要求）

- 脚本：`Hermes/pinterest_daily.py`（Playwright + channel=chrome；**需要 `pip3 install playwright`**；originals 403 自动回退 736x）。
- 输出：`Hermes/Pinterest素材/YYYY-MM-DD/`（图片 + 清单.md，含 pin 链接与描述）。
- 之后：复制到 `本地资源库/浏览器采集/` 跑 visual-reference-pipeline 标准流水线（去重→识别→重命名→提示词→merge 家谱文档→归档）。
- 注意：学术会议海报类（信息密度高、多栏文字）不适合做小红书风格参考，识别时注意筛选。

## Behance 医学/科学视觉素材采集（2026-08-07 新增渠道）

- **渠道价值**：国外设计师高质量医学视觉（The Lancet 期刊封面、医学插画合集、科学海报、解剖图集），无需登录，搜索页 `https://www.behance.net/search/projects?search=<关键词>` 可直接 curl 200。
- **提取**：browser_navigate 搜索页 → browser_console 提取全部 `img` 的 src（filter `mir-s3-cdn-cf.behance.net/projects/`，排除 ribbon/badge 图标，去重），一次约 24 个/页。
- **原图**：URL 中 `/projects/404/` 缩略图段替换为 `/projects/original/` 即得原图（已验证）；**超长作品集图（高 >4000px 或 高宽比 >3.5）自动回退缩略图**，防止竖排长图污染参考库。
- **工具**：`Hermes/behance_collect.py`（DRY 沉淀，`python3 behance_collect.py "<JSON>" [输出目录]`，断点续传 + 超长回退 + py_compile 验证过）。
- 详情与实测关键词清单：references/behance-style-collection.md
- **风格拓展关键词库**（国外医学画风，避开国内 11 家族）：editorial medical illustration / scientific illustration watercolor anatomy / swiss design poster typography / memphis style poster design / retro futurism science poster / isometric medical illustration / collage art poster design / film grain texture poster design / nature journal cover art science / flat design medical illustration / minimalist medical poster design / art deco poster design。落盘 `Pinterest素材/YYYY-MM-DD_国外医学画风拓展/{behance,pinterest}/`。
