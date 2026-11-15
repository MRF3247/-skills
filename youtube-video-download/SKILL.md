---
name: youtube-video-download
description: "Use when 下载视频/字幕到素材文件夹。yt-dlp 配方与报错补救。"
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [YouTube, yt-dlp, 素材, 下载, 字幕]
    related_skills: [video-asset-pipeline, youtube-content]
---

# 视频下载到素材文件夹

## When to use

用户丢一个 YouTube（或类似站点）链接，说「下载到素材文件夹 / 下下来做素材 / 要这条视频的画面」。
只想**要文字稿**时不要用本技能，走 `youtube-content`。
**付费/需登录的课程站（yt-dlp 拉不到、HLS+AES-128 加密）走 `token-gated-video-download`**，不是本技能。

## 0. 落盘位置判定（先想清楚再下）

| 情况 | 落盘目录 |
|---|---|
| 有正在做的剪辑项目（`~/Documents/剪辑项目/<项目>/素材/`，当天有改动） | 该项目 `素材/` |
| 通用/装饰类素材（音乐、字体、表情包、参考图） | `~/Documents/素材/<类别>/` |

判定线索：视频主题与该项目的主题一致（例：癌症疫苗视频 → `2.癌症疫苗的真相/素材/`，同目录已有 `Moderna IR Insights - Intismeran.mp4` 这类外采视频）。拿不准就下到最贴近的项目目录，并在回复里说明「放在了 X，需要移到 Y 说一声」——移动成本远低于重下。

## 1. 环境（本机已就绪，勿重装）

> 任何 `pip`/`uv pip install` 都加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`：本机默认源常见整页不动、超时返回 124，换清华源秒装。

```
~/Documents/Hermes/venvs/ytdlp/bin/yt-dlp     # 2026.08.19，Python 3.11
```

**必须用这个 venv。** 本机 `python3` 是 3.9，pip 会把 yt-dlp 卡在 2025.10.14（3.9 兼容的最后一版），那个版本对 YouTube 是坏的：报 `ERROR: [youtube] <id>: The page needs to be reloaded.` 或下到一半 `HTTP Error 403: Forbidden`。

重建命令（仅在 venv 丢了时用）：

```bash
python3.11 -m venv ~/Documents/Hermes/venvs/ytdlp && \
  ~/Documents/Hermes/venvs/ytdlp/bin/pip install -q --upgrade pip "yt-dlp[default]"
```

## 2. 下载

```bash
cd <目标素材目录> && ~/Documents/Hermes/venvs/ytdlp/bin/yt-dlp \
  --no-playlist --no-warnings \
  -f "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b" \
  --merge-output-format mp4 --write-thumbnail \
  -o "%(title)s [%(id)s].%(ext)s" "URL"
```

要点：
- `vcodec^=avc1` 强制 H.264 —— 默认可能挑到 AV1/VP9，剪辑软件与预览会挑食。
- **先只下视频，字幕单独第二次下**（见下）。把字幕和视频放一条命令里，字幕轨 429 会中断整个任务、视频根本没下。
- `--no-warnings` 压掉 impersonation 噪音；`No supported JavaScript runtime could be found` 警告可忽略（本机没 deno，仍能下）。
- 输出文件名里 YouTube 标题的 `:` 会被 yt-dlp 换成全角 `：`，正常现象，别手动改。

## 3. 字幕（可选，第二次单独跑）

```bash
~/Documents/Hermes/venvs/ytdlp/bin/yt-dlp --no-playlist --no-warnings \
  --skip-download --write-subs --write-auto-subs --sub-langs "en.*" \
  -o "%(title)s [%(id)s].%(ext)s" "URL"
```

- 4 条同义轨（`en` / `en-orig` / `en-GB` / `en-en-GB`）里，**人工轨通常是无逐词标签的那条**（`en-GB`）→ 干净、可读、拿来做逐字稿；带 `<00:00:02.000><c>` 的是自动生成轨。
- 429 就少要几条（`--sub-langs en-GB`）或隔几分钟重试。

## 4. VTT → 干净 SRT（ffmpeg 直接转会留 `\h` 垃圾）

`ffmpeg -i x.vtt x.srt` 会在每行尾留下字面量 `\h` 和断行，不能直接用。走 `scripts/vtt_to_clean_srt.py`：

```bash
~/Documents/Hermes/venvs/ytdlp/bin/python scripts/vtt_to_clean_srt.py "<某条.vtt>"
```

它会去掉 `<c>`/时间标签、`&nbsp;`、`\h`，把折行并成一句，写成同名 `.srt`。

## 5. 收尾（用户的归档习惯）

1. 同目录写一份 `<标题> [<id>] 来源信息.txt`：标题 / 账号 / 频道链接 / 视频链接 / 发布时间 / 时长 / 播放量 / 点赞（**标快照时间**）/ 画面规格 / 随附文件清单 / 版权与「科普视频不能当证据源」提示。
2. 用 `ffmpeg -i <mp4> 2>&1 | grep -E "Duration|Stream"` 自检真的下成了（分辨率、时长、音视频轨都在）。
3. 删掉重复字幕轨，只留「干净 .srt + 一条自动 .vtt」。
4. 向用户报：落在哪、分辨率/时长/大小、随附了什么、播放量快照时间。

## 坑清单

- **本机 `ffprobe` 不能用**：`--show_entries` 会报 `Unrecognized option`；读规格一律用 `ffmpeg -i`。
- **看下载进度别用 `tail`**：yt-dlp 的进度行用 `\r` 不换行，`tail -2 log` 会把整行几万字符全吐出来。用 `tr '\r' '\n' < log | tail -3` 或直接看 `ls -la *.part` 的字节数。
- **VPN/代理抖动是长视频下载的头号杀手**：小文件（字幕）一次性下完，GB 级正片会在中途 `Connection to rrX---sn-*.googlevideo.com timed out` 后整个任务退出。别反复手动重试，写一个**探测 + 续传**循环脚本丢后台跑：
  每轮先 `curl -sS -o /dev/null --max-time 10 https://www.youtube.com/` 探测；通了才跑 `yt-dlp --continue --socket-timeout 30 --retries 20 --fragment-retries 20`；没通就 `sleep 60` 下一轮；循环里先判 `ls *.mp4` 存在就退出。`--continue` 会从 `*.fNNN.mp4.part` 断点接着下，中断不丢进度。
  诊断顺序：`curl -o /dev/null -w "%{http_code}" --max-time 8 https://www.youtube.com/` → `http=000` 就是代理不通，别怀疑命令。
- **长视频优先降规格而不是硬刚**：4 小时以上片子，1080p 约 2.1GB、720p 约 0.5GB（视频轨）+ 25MB 音频。代理不稳定时换 720p，剩余量小一半以上、一次下完概率高得多；断点文件不通用（`f137.part` 与 `f136.part` 是两个文件），换规格会在目录里留孤儿 `.part`，记得问用户要不要删。
- **只能拿到自动字幕时，逐字稿怎么做**：YouTube 自动字幕**不含任何标点**（可用 `json3` 里 `.` 的计数验证，通常只出现在网址里）。别用「cue 词后加句号」的启发式补标点——会把 `but. The book` 这种假标点写进引文，后续引用会与原片不一致。正确做法：下 `--sub-format json3 --sub-langs en-orig`，按**静默间隔（≥0.9s）或单段长度上限（~360 字符）**断段，段首保留 `[HH:MM:SS]`，明确告诉用户「无标点、未改写」。
- pip 装出来的 yt-dlp 版本号看着新但其实是 3.9 天花板 → 永远用 venv 的 `python3.11`。
- `--extractor-args "youtube:player_client=android_vr"` 能拿到元数据、但下载会 403；不要靠它绕过，先升级 yt-dlp。
- 中途 403/429 失败会留下 `*.f137.mp4` `*.part` 残片，重下前 `rm -f *.f137.* *.f140.* *.part *.ytdl`。
- 别把下载的视频复制到多个素材目录（1080p 一条 60MB+），给路径即可。
- 视频里的机制/数据是科普口径，不是证据源；用于医学稿件时要回到原始论文/监管原文核实。
