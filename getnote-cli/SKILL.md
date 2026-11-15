---
name: getnote-cli
description: 得到大脑官方 CLI 操作：安装、doctor、读写删笔记与知识库。Use when 用户提到得到大脑。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [得到大脑, Get笔记, cli, 知识库, notes]
    related_skills: [getnote-api]
---

# 得到大脑 CLI（getnote）

## When to Use

用户提到「得到大脑 / Get笔记 / 我的笔记 / 知识库」且需要命令行读写笔记、批量归档、健康检查或删除时。CLI 优先于裸 OpenAPI（skill: getnote-api）；需要图片笔记/标签/订阅库等 CLI 未封装能力时回退 OpenAPI。

得到大脑官方 npm CLI（`@getnote/cli`，2026-09 本机已装 v1.5.7）。与裸 OpenAPI 同后端，但省去手写请求：命令封装好认证、分页、删除。

## 安装与配置

```bash
npm install -g @getnote/cli@latest   # npm prefix 是 ~/.local → bin 落在 ~/.local/bin/getnote（另有 gnote 别名）
getnote setup                        # 一次连接本机 AI 与得到大脑
```

- **setup 会复用已有凭证**：若 Hermes 环境变量 `GETNOTE_API_KEY`/`GETNOTE_CLIENT_ID` 已配（或本机已有登录态），setup 显示「账号已连接」，**无需浏览器授权**；还会顺带往 Windsurf/WorkBuddy 装 5 个 Skills（重启生效）。
- 健康检查：`getnote doctor -o json` → 看 `ready: true` + checks[]（cli/auth/api 全 ok 即通）。

## 常用命令

| 命令 | 作用 |
|---|---|
| `getnote notes --all` / `--limit N` | 列出最近笔记（分页用 `--cursor <last_id>`） |
| `getnote note <id>` | 笔记详情（标题/内容/标签/来源） |
| `getnote note delete <id> --yes` | 删除笔记（**移入回收站**，可恢复） |
| `getnote search "<词>"` | 语义搜索 |
| `getnote save` | 保存链接/文本/图片笔记 |
| `getnote kbs` | 列出知识库（含 note 数） |
| `getnote kb <topic_id> --all` | 列出库内笔记 |
| `getnote kb add <topic_id> <note_id>...` | 笔记加入知识库（每批 ≤20） |
| `getnote tag` / `getnote task` / `getnote quota` | 标签 / 异步任务进度 / API 配额 |

### 常用知识库 topic_id（用户侧固定映射，免每次 `getnote kbs` 现查）

| 知识库 | topic_id | 收什么 |
|---|---|---|
| INBOX | `nZK57r4Y` | 用户直接发来的视频/链接先落这里 |
| 医时选题库 | `07oPGma0` | 医学科研选题参考（稿件、工具书、在线课） |
| 医时会议 | `n1rvv1DY` | 会议纪要 |
| 内容运营 | `EJXeaLon` | 运营方法论 |
| 哲学 | `YM9k4LPY` | 百科词条（千条级） |

用户说「存进医时选题库」= 库 `07oPGma0`，根目录为 `默认目录`（无子文件夹，直接 kb add 即可）。

少量链接入库直接跑 `scripts/link_to_kb.py`（本技能自带，提交→轮询→抽查→入库一条龙）。

## 本地 Markdown 批量归档进「指定知识库文件夹」（实测 13 篇一遍过）

1. 读源文件去 frontmatter、把 Obsidian 双链 `[[X]]`→纯文本，写临时文件
2. `getnote save --content-file <f> --title "<标题>" --tag <标签> -o json`（**不要**带 `--topic-id`，否则笔记落在库根目录，之后要 remove+add 两步才能挪文件夹）；note_id 记 state.json，可幂等续跑，条目间 sleep 1.5s
2b. **标题命名（用户偏好，2026-09 实证）**：批量导入的系列笔记标题用「NN 章节名」（如 `03 选品体系`）——**不加来源/系列前缀**（如「谢无敌小红书手册 03 …」会被要求改回）。命名先算好再提交，事后改名要额外 13 次 update 调用。
2c. **改标题**：`getnote note update <id> --title "新标题" -o json`；只传 `--title` 不动正文（实测正文逐字符不变）；`--content`/`--tag` 才是替换型参数，需 `-y` 确认。
3. `getnote kb add <topic_id> <note_id>... --directory-id <dir_id> -o json` 一步进文件夹，核对 `success_count` 与 `failed_note_ids: []`
4. 核对：`getnote kb directories <topic_id> --directory-id <dir_id> -o json` → 该调用才返回**该文件夹内**的 resources 与 `total`（不带 `--directory-id` 只列根目录当前层，会误判成没进去）
5. 抽查内容：`getnote note <id> -o json` 的 content 字符数应与本地文件逐字符相等

## ⚠️ 实测陷阱（2026-09）

- **判断能力面先看 CLI 子命令表，别拿 OpenAPI 文档当全集**：`getnote kb --help` 列出 `directory-create/update/delete`、`bloggers/lives/blogger-follow` 等 OpenAPI 未暴露的命令，`getnote note --help` 有 `update/share/transcript/todos/original`。用户问「能不能放进知识库文件夹」这类问题时先扫一遍 `--help`，据 OpenAPI 文档断言「做不到」会被用户直接打回（错失一个全自动方案）。
- **库内组织结构服从用户在 App 里建好的文件夹**：归档前先 `getnote kb directories <topic_id>` 看用户已建的目录，按既有文件夹归类（kb add 带 --directory-id 即可）；**不要为「分类」自建平行知识库**——知识库没有删除接口，建错只能用户手删。
- **`kb add --directory-id <id>` 可把笔记直接归入库内文件夹**（directories 接口拿文件夹 id）。已入库（根目录）的笔记再 add 会进 failed_note_ids——改文件夹 = 先 remove 再带 --directory-id add，两步走。
- **`kb directories -o json --no-content` 会把 resources 列表整个吞掉**（只余目录），统计资源数必须省略 --no-content；响应带 total 字段可核对。
- **根目录/详情的 total 计数含已被服务端丢弃的任务**（隐形条目：App 可见、directories 接口读不出、detail 全 0 字节）。这类空壳直接 note/delete（进回收站）+ 清状态重交，是最快解法；总数对账用「knowledge/notes 全量翻页 vs 各文件夹 resources」的差集，别信 total。
- **Mac 合盖睡眠会冻住后台上传进程**（CPU 时间几乎不涨、日志停摆，开盖自动续）。长时间批量任务要么防睡眠，要么按「日志卡住 + CPU 不涨」识别后杀掉重跑（幂等续传无损失）。
- **`getnote kb directories` 对已入库笔记改目录必拒（failed_note_ids）**：改文件夹 = remove → 带 `--directory-id` add，两步；remove 后 add 遇 30000 会悬在根目录，稍后重试即可。
- **探针与正式上传不可并存**：额度恢复时探针成功会再拉起一个上传进程 → 双进程重复提交。拉起正式上传前先 pkill 探针。
- **知识库没有删除接口**（API/CLI 都无），误建的库只能用户在 App 里手动删。
- **链接笔记（note_type=link）提交有约 1000 条/天的滚动隐性上限**（用户实测确认）。触顶症状：save 接口持续 429 而读接口全正常；疯狂重试反而像攻击、可能延长封锁。正确姿势：停正式脚本，改「10 分钟一次探针」轻敲，解封自动拉起续传。knowledge/note/batch-add 不占这个额度，封锁期间归档照常能跑。触顶后服务端**仍会继续给已提交的笔记生成 AI 总结**——封锁期正是 harvest+archive 收割归档的窗口，别干等。
- 单条笔记 add/remove 持续回 30000(dependency_failure) 时是服务端临时卡住：该条会悬在根目录，勿反复硬重试，留到最后统一收尾。
- 收割异步 note_id 别逐条调 detail：`note/list` 自带 content 字段，翻页一遍即可同时拿 ID + 判断 AI 总结是否生成（非空=ready）。
- **知识库互斥：一条笔记只能属于一个知识库**。已归属 A 库的笔记 batch-add 到 B 库会进 `failed_note_ids`（顶层仍 success:true）。「从旧库迁到新库」= 先 `getnote kb remove <A> <note_id>... --yes` 再从 A 移出，再 `getnote kb add <B> ...` 加入，两步走。
- **判断「未分类」笔记的统计口径**：一条笔记在多个库？不会——互斥。未分类 = 全量 note/list 减去各库内笔记的**并集**。⚠️ 库内笔记分页**没有 total 字段**（`GET knowledge/notes` 响应不含 total）：用 `page*20 >= total` 判断翻页会在第一页就 break，把已在库第二页及以后的笔记全误算成未分类（曾把 792 条「未分类」里大部分其实是已分类的）。正确翻页：读到 `notes` 为空数组才停。
- **content 为空的 link 笔记无法加入任何知识库**（OpenAPI 与 CLI 都拒绝，返回 failed_note_ids）——这类「只有链接没抓到正文」的笔记（水刊广告、测试保存）只能删除或忽略，重试无意义。
- 删除命令是 `getnote note delete <id> --yes`；顶层 `getnote delete` **不存在**（unknown command）。
- 服务端限流：连续请求会 HTTP 429（qps_bucket_exceeded），批量操作用 for 循环加 `sleep 1-8` + 重试；`dependency_failure`(30000) 是服务端临时错误，稍等重试即可。**例外**：删除某条笔记持续回 30000、而 `getnote note <id>` 已回 note_not_found、库内也查无此条时，是幽灵记录（detail 本就返回空）——删除效果已达成，停止重试。
- **`getnote save <url>` 会同步等待异步任务**：链接笔记（尤其长视频/大页面）必超时报 `note task timed out`——**任务其实已受理**（返回里有 task_id/note_id，用 API 轮询 task/progress 拿结果）。链接类批量一律走 OpenAPI 脚本提交+轮询，别用 CLI save。
- 笔记 ID 是 64 位 int64，一律当字符串处理（CLI 已处理，脚本里勿 parseInt）。
- **`getnote save --content-file` 的 JSON 输出尾部看不到 note_id**（body 被 note 详情淹掉）：入库前用 `getnote notes --limit 3 -o json` 取最新一条的 id，别去 grep save 的 stdout。
- **AI 总结只覆盖被抓取的那一页**：在线书/文档站入链接库时，只有落地页内容会被总结（章节页全丢）——判据是总结里全是「前言/本书缘起/作者简介」这类落地页文字。此时补一条章节目录索引笔记，别指望换个 URL 再提交。
- **入库前的长度体检**：链接笔记 content <300 字符基本等于没抓到正文（站点模板/公众号空壳），先查 URL 是否需登录或反爬，再决定删掉重交。
- API Key 从本地 rtf 提取时：key 内含小数点（`gk_live_xxx.xxx`），正则须含 `[A-Za-z0-9_.\-]`，否则截断导致 401。

## 批量归档工作流（视频/链接 → 知识库）

1. 内容获取：YouTube 用字幕（skill: youtube-content）；B站无 CC 字幕时 yt-dlp 下载音频 → ffmpeg 16k wav → FunASR 转写（skill: local-asr-funasr）。
2. 组织 markdown 笔记（一句话总结 + 📑智能总结 + 分点），标题用原稿标题。
3. `getnote save` 或 OpenAPI note/save（plain_text 同步返回 note_id）。
4. `getnote kb add <topic_id> <note_id> -o json` 入库并**核对 success_count**。
5. 用户侧 Obsidian 归档惯例见对应素材 pipeline 技能（B站素材库/逐字稿/<NN-UP主>/<原稿标题>.md + frontmatter + 素材索引.md 追加行）。

## 单篇/少量稿件 → 指定知识库（链接入库，实测 2-3 条一遍过）

默认做法：**只交链接，内容由服务端抓网页 → 生成 AI 结构化总结**。不要本地转写正文再传，除非服务端抓不到。

1. 确认目标库 topic_id（见上表），`getnote kb directories <topic_id> -o json` 看有无现成文件夹
2. 提交：`POST /open/api/v1/resource/note/save`，body `{note_type:"link", link_url, title, tags:[<库名>]}` → 取 `tasks[0].task_id`
3. 轮询 `POST /open/api/v1/resource/note/task/progress {task_id}` 拿 `note_id`（公众号文章约 1-2 分钟内出）
4. **抽查正文**：`GET /open/api/v1/resource/note/detail?id=<note_id>`，看 `content` 长度与首尾——确认抓到的真是正文而不是站点模板
5. `getnote kb add <topic_id> <note_id> -o json`，核对 `success_count` 与 `failed_note_ids: []`
6. 用 `getnote kb directories <topic_id> -o json` 的 total 跟用户报数

### 多页站点（在线书/文档站/教材）必须补一条索引笔记

服务端只抓**落地页**：AI 总结会完整覆盖前言/简介，但整站章节一条都抓不到。用户问「这个能不能存进库」时，只入一条链接笔记 = 存了个封面。

做法（两条一起入同一库）：
1. 链接笔记照上面 1-5 步入库（拿到这本书「是什么/给谁看/配套资源/许可证」）
2. 抓章节清单：`curl -s <站点首页> | grep -oE 'href="[^"]+"'` 过滤出相对页；对每个页面取 `<title>`（多线程 + 重试 3 次，静态站常有零星 TLS 超时）
3. 生成 `plain_text` 笔记：一句话总结 + 来源/配套资源 + **逐章标题带上可点直达链接** + 许可证 + 「可复用选题角度」几行，`getnote save --content-file` 后 kb add
4. 交付时说明「为什么是两条」——一条是书本身，一条是章节目录，别让用户以为重复

### 内容层面的附加义务（用户会核对）

- **营销/软文稿**：入库后在回复里标一句利益冲突与事实边界（例：移民中介的「挂名即可」是中介口径，不是科研规范），别把软文结论当选题事实。
- **版权**：CC BY-SA 类开源书在笔记里保留署名 + 原链 + 同协议要求，用户后续要改编做内容。

## 大规模链接词条入库管线（千条级，实测 2735 条跑通）

把整站百科批量做成链接笔记归档，四件套脚本 + 单一 state 台账。参考实例（IEP/SEP 词条→「哲学百科」库，脚本可复制改路径复用）：`/Users/Jin/Documents/Open Programs/getnote/`（philo_upload.py / philo_harvest.py / philo_archive.py / philo_probe.py + launchd watchdog）。

1. **entries.json** 清单（title/url/source/file）+ **state.json** 台账：`submitted{url→task_id/note_id/ready/error}`，`done[]` 只记确认成功入库的
2. **submit**：串行提交链接（间隔 ≥2.5s），废记录（有 error/bailed 且无 note_id）启动时删除以触发重交；阶段 3 入库按 source 分文件夹、失败退回重试
3. **harvest**：翻页 `note/list`（自带 content，非空=ready）收割 note_id——**必须同时复查「已收割未就绪」的**，只查无 ID 的会漏掉服务端陆续生成完的大批（曾一复查就绪数 792→1949）
4. **archive**：就绪未入库的按 source 归档（幂等可反复跑，每批核对 failed_note_ids）
5. **probe + watchdog**：额度封锁期停正式脚本，改 10 分钟一次探针轻敲，解封自动拉起；launchd 只在探针和上传都不在时拉探针

- **交付对账以服务器为准**：`kb directories -o json` 的 total + 根目录剩余，逐项核对本地 done 数——本地台账 ≠ 服务端事实（done 曾虚记 3 条）
- 汇报进度用准确机制词：「提交链接，由得到大脑自己抓网页生成」，别说「上传笔记」——用户会核对实际机制

## 与 getnote-api skill 的关系

- `getnote-api`（用户自建，OpenAPI 裸接口）覆盖更底层能力：图片笔记三步、标签增删、订阅库只读、async task 轮询等 CLI 未完全封装的细节。
- CLI 够用场景优先 CLI；需要裸接口能力时回退 OpenAPI。

---

## 已合并的同类技能（2026-09-23 归并）

以下技能内容已并入本技能，原文存档在 `references/`，脚本/模板在 `scripts/<名称>/`、`templates/<名称>/`。技能清单里不再单独出现它们；需要时读对应文件。

| 原技能 | 适用范围 | 原文 |
|---|---|---|
| `getnote-api` | 得到大脑（Get 笔记）OpenAPI：读写笔记、知识库、语义搜索。Use when 用户提到得到大脑。 | `references/merged-getnote-api.md` |
