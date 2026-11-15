<!-- 由 bilibili-benchmark-catalog 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/media/bilibili-benchmark-catalog -->

---
name: bilibili-benchmark-catalog
description: "整理B站对标账号库时使用：枚举筛选、查UID、爬互动数据、生成Obsidian账号文档。"
version: 1.0.0
metadata:
  hermes:
    tags: [bilibili, 对标账号, obsidian, 枚举, 数据整理]
---

# B站对标账号库整理 (bilibili-benchmark-catalog)

与 `bilibili-video-pipeline`（下载→转写→分析）互补：本技能管「账号库整理」——账号清单维护、稿件枚举筛选、互动数据采集、Obsidian 账号文档生成。用户常先整理账号库、暂停分析，整理完再开批处理。

## 入口与脚本（工作目录 /Users/Jin/Documents/Hermes/B站工作流/）

| 脚本 | 用途 |
|---|---|
| accounts.yaml | 账号清单（110 个：level/name/uid/fans/videos/category/recent_months/exclude_keywords；新增账号直接追加行 `- {level: E, name: X, uid: '...', fans: N, videos: M, category: 类别, recent_months: 12}`） |
| enumerate_accounts.py | 枚举全部账号稿件 → 素材库/.catalog/{uid}.json；`--uid`/`--level`/`--refresh` |
| search_users.py | wbi 签名搜索接口批量查 UP主 UID（返回粉丝/认证/简介），一次一个关键词，间隔 1.5s |
| fetch_stats.py | 爬全部稿件互动数据（view/like/coin/favorite/share/reply/danmaku）写回 catalog，断点续传 |
| obsidian_writer.py | write_account_notes(cfg, sort_by='play'|'pubdate') 重建 96 个账号文档 + 总览 |
| build_video_notes.py | 生成每条视频一个笔记 + 视频库.base 数据库（**用户明确要求建库时才用**，默认不建） |

## 筛选口径（enumerate_accounts.py 内置默认，用户可调）

两段式：`--since 2025-01-01` 之后发布 → `--min-views 2000`；更早 → `--old-min-views 10000`；`--max-duration 40`（分钟）；账号级 `exclude_keywords` 排除标题关键词（例：医嘉研排除 zotero）。
**catalog 必须存 `all_videos` 全量字段**（不只 selected）——账号文档要列全部稿件，筛选逻辑随时改，全量数据避免反复重枚举。

## Obsidian 账号库文档规范（用户明确要求，见 references/obsidian-account-library-format.md）

- 文件名：`{NN}-{账号名}（粉丝{xx.xx万}）.md`，NN=按粉丝量降序编号（01-96）
- 粉丝数、播放量、互动数统一 xx.xx万 格式（_fmt_fans/_fmt_views，两位小数去尾零：543000→54.3万、8105799→810.58万、48→0万）
- 表格列：播放 | 点赞 | 投币 | 收藏 | 转发 | 评论 | 标题 | 时长 | 发布 | 链接 | 逐字稿 | 选题分析
- 排序两种可切换：'play'=播放量降序（默认）/ 'pubdate'=发布时间从新到旧，文档标题与 frontmatter 标注当前排序
- 选题分析目录同名规范：`选题分析/{NN}-{账号名}（粉丝xx.xx万）/`
- 总览：96 账号按粉丝降序 + 稿件数 + 已处理进度；重建前先清理旧账号文档防残留/重复编号

## 用户偏好（本会话纠偏，必须遵守）

1. **不要自作主张做标题规则分类**：曾用系列标签+主题词典自动分类，用户认为「不严谨」要求恢复——统一用简单表格（全部稿件按播放量降序）即可，分类需求由用户主动提出。
2. 数据格式统一：粉丝/播放/互动一律万为单位，禁止混用完整数字。
3. 用户说「先别建库」就删掉已生成的数据（视频库 .base + 2 万条笔记曾生成后按指示删除）；建库前需先爬齐互动数据。
4. 先整理账号库、暂停分析是常态节奏：整理期间不要启动批处理分析，等用户明确「开始分析」。

## 关键陷阱

1. **枚举进程竞态**：--refresh 全量枚举在后台跑时，若中途删了账号，旧进程仍按启动时列表重新生成已删账号的 catalog → 每次枚举/删号后统一清理：扫 .catalog/*.json，账号不在 accounts.yaml 的删除，再重建账号库。
2. **write_account_notes 先清旧文件**：生成前删除对标账号库目录下所有非「总览/总清单」的 .md，否则编号变更后新旧文件并存（曾出现 02- 两组文件）。
3. **API 类型容错**：B站 接口偶发返回字符串/空值（play/pubdate），筛选和排序一律过 `_to_int`/`_duration_min`，否则 `>= not supported between str and int` 崩溃（深读视频踩过）。
4. **search_users 同名混淆**：搜索结果常有多人同名，取粉丝量+认证（official_verify.desc）判断主号；未解析的账号标注原因不硬凑。
5. **wbi 搜索接口**：web_search 查 B站 UID 不可靠（搜到字典释义），用 api.bilibili.com/x/web-interface/wbi/search/type?search_type=bili_user 直接查。
6. **互动数据爬取节奏**：view 接口单视频单请求，2 万稿件 ≈ 4-5 小时；带 cookie + 随机间隔(0.8s+0.5s 抖动) + -412 退避 45s；失败不写 stats 留待重跑（断点续传判断依据是 v 里有没有 "stats" 键）。
7. **必须用 FunASR venv 的 python 运行工作流脚本**（`/Users/Jin/Documents/GitProgram/FunASR/.venv/bin/python`，即 bili.sh 里的 $PY）：系统 python3 缺 yaml 等依赖（踩过 ModuleNotFoundError: yaml）。新增账号完整流程（已实测，枚举无风控问题）：追加 accounts.yaml → `enumerate_accounts.py --uid <uid> --refresh` 逐个拉 catalog → `obsidian_writer.write_account_notes(cfg)` 自动重建全部账号笔记（编号按粉丝降序全量重排）+ 总览 + 索引。未解析 UID 的账号不硬凑，直接告知用户原因。

## 相关

- 视频处理管线（下载/转写/分析）见 skill: bilibili-video-pipeline
- Obsidian 笔记格式遵循 obsidian-markdown；数据库视图方案（.base）见 obsidian-bases
- 账号文档完整格式规范（frontmatter/表格/排序/命名/链接逻辑）见 references/obsidian-account-library-format.md
