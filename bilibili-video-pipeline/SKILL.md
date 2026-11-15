---
name: bilibili-video-pipeline
description: "用户提交B站链接(单视频/UP主主页)时使用：下载→FunASR转写→LLM校对→评论→选题分析→Obsidian归档。"
version: 1.0.0
metadata:
  hermes:
    tags: [bilibili, video, funasr, asr, transcript, obsidian, content-strategy, 选题分析]
---

# B站素材工作流 (bilibili-video-pipeline)

用户提交 B站 链接时运行：单视频链接或 UP主主页链接 → 下载到素材库 → 本地 FunASR 转写 → LLM 校对 → 抓评论 → 选题分析 → 写入 Obsidian。

## 一键入口

```bash
cd /Users/Jin/Documents/Hermes/B站工作流
./bili.sh "https://www.bilibili.com/video/BVxxxx"        # 单视频全流程
./bili.sh "https://space.bilibili.com/123456"            # UP主全量（反扒间隔 10-25s/视频）
./bili.sh <链接> --max-videos 10 --no-analyze --no-proofread --force --limit N
./bili.sh --account <UID>                                # 按 .catalog 清单批量处理账号（播放≥2000 的视频）
./bili.sh --account <UID> --limit 20                     # 该账号只处理前 20 个
python enumerate_accounts.py                             # 枚举 accounts.yaml 所有账号，生成达标清单
python enumerate_accounts.py --level A --refresh         # 只枚举某级/强制刷新
```

账号清单在 accounts.yaml（15 个对标账号 A-E 五级，play≥2000 筛选）。枚举结果存 素材库/.catalog/{uid}.json，Obsidian 对标账号库笔记自动生成（含达标视频表格+处理进度）。
- 清晰度默认 360p（config.yaml max_height），够 AI 分析口播用、下载快。

## 得到大脑 API 通道（2026-08-05 起）

每天 100 次免费额度，抓 B站 链接一次调用（~25 秒）产出：AI 笔记（note.content 结构化摘要）+ 逐字稿（web_page.content 口播原声直转，未校对）。
- 凭证：~/.hermes/.env 的 GETNOTE_API_KEY / GETNOTE_CLIENT_ID（Authorization 裸 key + X-Client-ID，无 Bearer）
- 用法：note/save note_type=link + link_url → 轮询 task/progress → note/detail 取 web_page.content
- 分工：得到 API 出逐字稿（省 FunASR 转写），DeepSeek 校对（proofread.py 同款）；评论区分析得到 API 不做，需回原链接爬评论（fetch_comments.py）
- 归档：逐字稿/{账号}/标题.md 照旧规范，frontmatter 加「生成方式: 得到大脑API」；AI 摘要并入笔记头部
- 参考实现：getnote_test.py（单条演示）、getnote_pipeline.py（bvid → 逐字稿+校对 → Obsidian）
- 注意：额度按自然日重置，100/天；B站 视频若需会员/已失效会生成失败

## 每日自动批处理（cron）

cron job `daa6833e9aa7`（每晚 23:00，no_agent 纯脚本，不耗 LLM）运行 ~/.hermes/scripts/bili_cron_daily.sh：
- B级大号（解螺旋 254040065 / 统计之光 538894363）每账号 60 个/晚
- 其余账号每账号 30 个/晚
- pipeline --account 模式只取「未完成」视频（无 analysis.md 的），每晚自动推进、断点续传
- 日志: 工作流目录 logs/cron_daily.log；进度看 Obsidian 对标账号总览.md
- 处理中若有视频下载/转写/分析失败，批次不中断（跳过并汇总，重跑自动续传）
- 已跑完的账号每晚秒过（todo 为空），未来新视频会被自动捡起（需先重跑 enumerate_accounts.py 刷新清单）

## 路径速查

| 用途 | 路径 |
|---|---|
| 工作流脚本 | /Users/Jin/Documents/Hermes/B站工作流/ |
| 视频素材库 | /Users/Jin/Documents/本地资源库/B站参考/{UP主}/{标题}/ |
| Obsidian 逐字稿 | /Users/Jin/Documents/医时知识库/B站素材库/逐字稿/{UP主}/ |
| Obsidian 选题分析 | /Users/Jin/Documents/医时知识库/B站素材库/选题分析/{UP主}/ |
| 素材索引 | /Users/Jin/Documents/医时知识库/B站素材库/素材索引.md（自动重建） |
| yt-dlp | /Users/Jin/Documents/GitProgram/yt-dlp/.venv/bin/yt-dlp |
| FunASR venv python | /Users/Jin/Documents/GitProgram/FunASR/.venv/bin/python |
| ASR 模型 | /Users/Jin/Documents/GitProgram/FunASR/models/（~2GB，含 paraformer-large+fsmn-vad+ct-punc-large） |
| 运行日志 | 工作流目录 logs/pipeline_*.log |

## 断点续传 / 幂等

每个视频目录里缓存中间产物：mp4、audio.wav、`*.info.json`、asr_raw.json、proofread_paras.json、comments.json、analysis.md。重跑自动跳过已有步骤；`--force` 强制重做转写/校对/评论/分析（下载本身由 .archive.txt 去重，永远不重下）。
单视频下载后中途失败 → 重跑同 URL，会按 BV 号找回已下载目录继续处理。

## 关键陷阱（都踩过坑）

1. **MODELSCOPE_CACHE 环境变量**：FunASR 1.4.1 下载模型时忽略 cache_dir 参数，只认 `MODELSCOPE_CACHE`。transcribe.py 已在 import funasr 前设置它指向 GitProgram/FunASR/models。若模型被重复下载（出现在 ~/.cache/modelscope），说明环境变量没生效。
2. **ffmpeg 不在 PATH**：yt-dlp 需要 `--ffmpeg-location` 才能合并 DASH 分离的音视频流；bili_download.py 已用 imageio-ffmpeg 的二进制路径传入。若下载后目录里残留 `.f100026.mp4`+`.f30280.m4a` 分离文件，extract_audio 会自动合并。
3. **yt-dlp 的 info.json 文件名是 {标题}.info.json 而非 info.json**：读取用 bili_download.find_info_json()。
4. **B站风控(412)**：下载/评论接口都可能触发。缓解=浏览器 UA + 请求间隔 + cookies（已全部内置）。cookies 文件在 /Users/Jin/Documents/Hermes/APIs/www.bilibili.com_cookies.txt（config.yaml 的 download.cookies_file 已指向它）；下载和评论抓取都会自动带上。cookie 会过期（SESSDATA），失效后下载掉清晰度/频繁 412 时让用户重新导出覆盖同一路径即可。
5. **未登录下载**：默认最高 1080P（4K/高码率需大会员），无 cookies 通常 480p-1080p 之间浮动，属正常。
6. **LLM key**：复用 ~/.hermes/.env 的 DEEPSEEK_API_KEY（deepseek-v4-pro 校对/分析，flash 兜底）。脚本只读不显示密钥。无 key 时校对/分析会失败，转写不受影响。

## 配置（config.yaml）

- `download.sleep_*`：反扒间隔，默认 1.5s/请求、10-25s/视频。UP主全量几十个视频会跑很久，属预期。
- `asr.device`：cpu（默认）或 mps（Apple Silicon 可试）。
- `analysis.max_comments` 默认 200；`llm.proofread` 默认开。

## 验证步骤（工作流跑完后）

1. 素材库目录有 mp4 + audio.wav + *.info.json
2. Obsidian 两个笔记 + 素材索引存在，frontmatter/链接正常
3. 转写质量抽查：逐字稿开头几段，错字/标点/分段是否 OK
4. 分析质量抽查：赛道/主题/情绪/评论焦点/借鉴 五节是否齐全、评论引用是否真实（模型可能幻觉，引用要对得上 comments.json）

## 相关

- 分析框架对齐 skill: video-content-strategy（赛道分层/泛×身份/对标拆解）
- Obsidian 笔记格式遵循 obsidian-markdown（frontmatter + wikilinks + callouts）
