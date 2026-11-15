---
name: getnote-batch-upload
description: Use when 批量上传笔记/链接到得到大脑知识库（QPS限制、字符上限、断点续传）。
---

# 得到大脑批量上传

脚本：`/Users/Jin/Documents/Open Programs/getnote/philo_upload.py`（三阶段：串行提交→轮询拿note_id→kb add入库；state json断点续传）

## 实测硬参数（2026-09-14，2735条全量验证）

- **单篇内容上限 5 万字符**：4.9万成功，5.4万报「笔记内容超过限制」→ 超限文件必须拆分子笔记
- **提交是异步的**：save 即返 task_id，AI 生成在服务端并行
- **空 content 的 link 笔记无法入 kb**（failed_note_ids）→ 必须等 AI 总结生成完再入库
- **QPS 桶≈1**：串行 1.5-2秒/条稳定；并发触发 429 指数退避
- **上传链接比传文件优**：100%词条带官方URL时，提交URL让得到大脑抓取 → 不受5万限制（14万字原文照存）+自动中文AI总结
- **网络断开进程会僵死**（无超时socket）：设 socket 超时或用监控+重启；state 断点续传不丢进度
- **CLI 偶发空 stdout**（Expecting value）→ 重试即可
- 服务端偶发「生成笔记失败，请手动重试」（约 0.2%，5/2735）→ 重提交也失败 → 删空壳放弃（5条：法称/果让巴/优生学/仇恨言论/寂天，均 SEP）

## 流程

1. 建清单（url/title/source 去重）→ /tmp/xx_entries.json
2. 预填已提交记录到 state（防重复）
3. 小规模 3 条验证全链路 → 全量后台跑
4. 完成后对账：state.done vs `getnote kb <id> --all --no-content -o json` 实际条数
5. 抽查内容完整性（AI总结+原文都>0）

## 凭证

~/.hermes/.env 的 GETNOTE_API_KEY / GETNOTE_CLIENT_ID（不打印明文）；OpenAPI base https://openapi.biji.com，头 Authorization + X-Client-ID


## INBOX 批量经验补充（2026-09-16，30 条第二批）

- **TLPQ 开头的列表 = 动态 Mix 队列**：无固定成员，两次抓取结果不同，且 `yt-dlp`/API 均报「playlist does not exist」→ 让用户找真正的 PL 列表或直接贴链接
- **用户说列表"不存在"先问是不是设了私有**：转公开后 yt-dlp 立即可读（实测 1 例）
- **kb add 单批上限 20 条**：超过要分块
- **无字幕且得到大脑抓取失败的视频兜底链**：yt-dlp 拉字幕 → 无字幕则下载音频 → mlx-whisper 转写 → DeepSeek 摘要 → 纯文本笔记上传入库 → 删得到大脑空壳
- **纯影像视频**（whisper 只转出几秒）：用研究背景/官方简介生成概要，并在笔记开头注明"无解说词，基于简介的概要"
- 上传纯文本笔记后 kb add 前无需等（content 立即有值），link 笔记才要等 AI 总结
- **每次兜底入库后，立刻删除本次下载的全部素材**（webm 音频、wav、转写 json、字幕缓存）——用户强调（2026-09-16、2026-09-20 两次）：入库成功后随手删，不留到下次；whisper work/ 目录和 /tmp 都要检查
