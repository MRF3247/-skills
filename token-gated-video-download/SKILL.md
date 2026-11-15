---
name: token-gated-video-download
description: "Use when 下载付费登录课程站视频：HLS+AES-128 解密批量下载。"
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [视频下载, 课程, HLS, AES-128, ffmpeg, 解螺旋]
    related_skills: [youtube-video-download, video-transcript-pipeline]
---

# 登录态/加密课程站视频批量下载

## When to use

用户要下**付费课、网课、知识付费平台**的视频（解螺旋 helixlife、得到、各类培训站），而且 yt-dlp 拿不到（站点要登录 + 阿里云 VOD/HLS 加密）。
公开站（YouTube/B站）不要用本技能，走 `youtube-video-download`。
只要文字稿时下完接 `video-transcript-pipeline`。

## 0. 先找现成脚本，别从零写

用户经常直接丢一个 zip（别人写的脚本 + README）。先 `unzip -l` 看结构，`read_file` 读 README 和主脚本，把**鉴权链**画出来再动手。多数情况下改造它比重写快得多。

## 1. 鉴权链长这样（几乎所有同类站同构）

```
浏览器登录 → Bearer Token（cookie 的 token 字段 / 请求头 authorization）
    ↓
GET 课程 lessons API            → 节次列表 + video_id
    ↓
GET 播放鉴权 API                → 第三方云（阿里云 VOD 等）临时 STS 凭证
    ↓
云厂商 GetPlayInfo（STS 签名）  → m3u8 播放清单（AES-128 加密 HLS）
    ↓
GET decrypt_key（需 Bearer）    → 16 字节解密密钥
    ↓
改写 m3u8：key URI 指向本地文件、TS 补绝对地址
    ↓
ffmpeg -protocol_whitelist file,crypto,data,https,tcp,tls -i patched.m3u8 -c copy -movflags +faststart out.mp4
```

m3u8 的白话：一份播放清单，说明视频被切成多少小片、每片从哪取、用什么密钥解。ffmpeg 按清单一边拉一边解密，最后拼成一个文件。

## 2. 环境（macOS）

```bash
mkdir -p "/Users/Jin/Documents/Open Programs/<站点>-download" && cd "$_"
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -i https://pypi.tuna.tsinghua.edu.cn/simple <依赖>
```

- **装包一律加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`**：本机默认 PyPI 源常见整页不动、`uv pip install` 干跑 3 分钟超时返回 124，换清华源秒装。别以为是依赖坏了。
- ffmpeg 用系统的 `shutil.which("ffmpeg")`，**不要** `import imageio_ffmpeg`（别人脚本里为 Windows 内置的重包，本机 `/Users/Jin/.local/bin/ffmpeg` 已有）。
- 脚本落 `~/Documents/Open Programs/<站点>-download/`，依赖进同目录 `.venv`（用户偏好本地工具固定装这里）。

## 3. 改造成本机版的三条硬要求

1. **Token 不进聊天**：`resolve_token()` 按 `--token` → 环境变量 → 同目录 `token.txt` 顺序取；先建一个空 `token.txt` 让用户自己粘，并用 `open -R token.txt` 把 Finder 定位过去。用户明确不愿意在对话/终端里看密钥明文。
2. **先 `--list` 再下载**：加 `--list` 只请求一次 lessons 打印节次，验证 token 和课程 UUID 都通、再进全量；再加 `--start/--end` 以便单节试跑。不要写完直接跑整课。
3. **断点续传**：输出文件存在且 > 100KB 就跳过。全课中途失败重跑不重下。

## 4. 先把「可下载课程清单」交给用户，让他报编号

课程站用户手里通常有几十上百门课。**别让他去翻课程页复制 URL**——他会直接说「把列表列给我」。所以拿到 token 后的第一个交付物是一张清单，不是下载命令：

1. 拉全量课程列表（分页取完，见站点笔记的列表端点）。**筛选参数常被后端忽略**——带 `type=mine&page_size=1` 和不带返回同一批数据，就别指望服务端帮你筛「我的课」；`lessons` 端点也基本不校验权限。
2. **权限判据 = 下载链路第一步能不能过**：调播放鉴权接口换 PlayAuth，成功=有权限，失败文案通常是「该视频您无权限观看！」。这是唯一可靠的判据，`user_course`/`is_vip`/详情字段都不等于有权限。**探测必须取前 3 个 `is_free == false` 的节，任一成功即算有权限**——只试第一节会把免费试看当成有权限，只试最后一节会把后加的单独售卖课当成整课无权限（两个方向都误报过，详见坑清单）。
3. 逐门探测用 `ThreadPoolExecutor(max_workers=4)`：单门 ~0.7s，200 门以内的平台约 1 分钟扫完；并发别超过 4，课程站有风控。
4. 结果落 `course_index.json`（`no / title / uuid / videos`），下载器物化 `--index`：`--index 6` / `--index 6,12,55` / `--index all`，多课各建 `NN_课程名/` 子目录。
5. 交付格式（用户明确要求）：**表格逐条列全，一条不许省**；按节数降序编号；每行给「编号 | 节数 | 课程名」；末尾给总课程数、总节数、**体积粗估（节数 × 50MB）** 并主动建议先挑几门，别默认整平台全下。

## 5. 验证顺序（缺 token 时做到第 2 步为止，别假装跑通）

1. `import` 依赖，SDK 能导入。
2. 用**假 UUID + 假 token** 打 lessons 端点，确认网络可达、返回结构符合脚本预期（这一步不需要真凭证）。
3. 拿到登录态后（用户给 token，或自动登录脚本 `jlx_login.py` 写出的 `token.txt`）：先 `--list`，核对节数与标题。
4. 单节 `--start N --end N` 下完 → `ffmpeg -i out.mp4 2>&1 | grep -E "Duration|Stream"` 自检有音视频轨。
5. 全量。跑完一门再进下一门；多课批量前把「先单节验，再整课」这句话告诉用户，他才会放心让你通宵跑。

**输出位置**：脚本默认 `~/Documents/视频/<站点>`。用户说「保存到下载文件夹」就用 `--out ~/Downloads/<课程名>`；**单课直接 `--course <uuid|URL> --out <目标目录>`**（`--index` 会自己建 `NN_课程名/` 子目录，单课再套一层目录就多余了）。整课跑完再逐文件 `ffmpeg -i` 抓 `Duration`/`Stream`，把时长与平台标注（lessons 的 `length` 字段）对一遍再报完工——这是用户验你「真下载了还是嘴巴说下载了」的地方。

## 坑

- **同一个站点可能有多个 token，只有 cookie 里那个带课程权限**。解螺旋实测：localStorage 的 `token`（passport 域登录产生，值形如 `{"data":"3969271|xxx"}`）能列课程列表、对**部分**课能换到 play_auth，但对新购的课一律返回「该视频您无权限观看」；而 `www.helixlife.cn` 的 **document.cookie** 里那个 token 才是网页实际在用的、有全部权限的那个。两者值不同（前缀数字都不同），长度都是 56。诊断信号：网页里课程页显示「已学 1% / 继续学习 / 学习耗时 20 秒」就能确认账号真有权限，此时不要再怀疑购买状态，直接去读 cookie。

- **登录后 cookie 写入有延迟**，登录瞬间读 `document.cookie` 常常还没有 token（只有 `_c_WBKFRo` / `sensorsdata` 这几个）。要轮询 8 次×2 秒再读，不能读一次就回退到 localStorage。

- **play_auth 报「无权限」不一定真没买**。判断顺序：① 先确认网页能不能播（看学习进度 / 耗时）；② 再对比 cookie 与 localStorage 两个 token 哪个能换到 PlayAuth；③ 两者都不行才基本可以判定账号无权限。直接报“你没买”容易误伤。清单

- ⚠️⚠️ **同一账号重新登录会让旧 Token 立即失效**（是单点登录）。失效后的症状不是 401，而是 play_auth 回 `请先进行登录！`（code 400002）——很容易误读成「没买课」。**抓一次 Token 就用到失效，期间绝不重跑登录脚本**；下载/扫描报「请先登录」时，先怀疑 Token 被后来的登录顶掉，而不是去重扫权限。现在这份 token 就存在浏览器 `document.cookie` 的 `token` 里（前端 `TOKEN_NAME="token="`，`get_cookie()` 直接 substring 取），56 字符、形如 `396893|xxxx`。
- ⚠️⚠️ **权限是「按节」授予的，扫课时不能只试一节**。两个反方向都踩过：第一节常是免费试看（`is_free: true`）→ 拿它验会把「没买」误判成「有权限」（189 门误报 89 门）；最后一节可能是后加的单独售卖课 → 拿它验会把「已买」误判成「无权限」（29 门，真值 47 门）。**正确判据：取前 3 个 `is_free == false` 的节，任一节能换到 PlayAuth 即算有权限**。总之一门课里可能有的节能看有的不能，下载时必须逐节容错而不是整课失败。
- **play_auth 的请求头三件套**：`authorization: Bearer <token>` + `platform: pc` + `source: PC`（前端 axios 拦截器写死的，见下文）。f 参数确实是 `base64(urlencode(json({"video_id":...})))`，和原脚本一致，不是这里错。
- **浏览器里 hook fetch/XHR 抓不到 play_auth**：主文档和 iframe 都试过、注入了也不进记录（aliplayer 自带请求层绕过了全局 hook）。想看真实请求用 `performance.getEntriesByType('resource').map(e=>e.name)`——能拿到 play_auth、GetPlayInfo、m3u8 的完整 URL（包括 STS AccessKeyId/Signature）；请求头逻辑则去 `/child/edu/js/chunk-*.js` 里 grep `play_auth`/`Bearer`/`TOKEN_NAME`。
- **节号（lesson.number）在章内重复**：多章节课程里十几个节都叫 `01`，只按 number 命名会互相覆盖。用平台给的 `path.name`（形如 `第三章 示例操作.mp4`，自带章节号且唯一），前面再加全局序号保证排序。

- **解密 key 长度不是 16 字节 = Token 过期**。key 接口过期后返回的是 JSON 错误体（几十~几百字节）而不是报错码，直觉容易误判成加密算法问题。
- **lessons 端点可能不校验 token**：假 token + 假 UUID 也返回 `success:true, data:[]`。所以「列表是空的」不等于「课不存在」，先排除 token/权限问题再怀疑 UUID。
- **别默认「登录态只能用户给」**：站点支持账号密码登录且无图形验证码/滑块时，camofox 能代填表登录、脚本自己抓 token，用户只把凭证写进本地 `login.txt`（第一行账号、第二行密码）——凭证不进对话。完整 recipe 见 `references/auto-login.md`；只有验证码/微信扫码/滑块登录才退回让用户给 token（F12 → Network → Fetch/XHR → 任一个站内 GET 请求的 `authorization`，去掉 `Bearer ` 前缀）。
- **必须加 `-movflags +faststart`**：不加，Windows 自带播放器报 `0xC00D36C4` 而 VLC 能播——别当成下载失败。
- **`-protocol_whitelist file,crypto,data,https,tcp,tls` 是解密必需**：漏 `crypto` 解不开 AES-128；漏 `file` 读不到本地密钥。
- **`login.txt` 里的 `#` 注释行会被当成账号密码**：给了带注释的 `login.txt.example` 模板，用户会连着注释一起复制，脚本读到前两行是注释 → 拿注释当账号登录失败，而报错看起来像「密码错」。取凭证时过滤 `x and not x.startswith("#")`；模板本身也尽量只留两行纯值。
- 落盘前把标题里的 `\ / : * ? " < > |` 换成下划线。
- **版权口径**：写成「本人已购课程的个人离线备份」，不做二次分发。一句话点到为止，不说教。

## 站点笔记

- 解螺旋 helixlife.cn 的端点、参数编码、已落地脚本位置见 `references/helixlife.md`。

## 解螺旋账号密码自动登录（camofox，实测通）

用户有账号密码时不必让他手抠 Token——camofox 走登录页自动登录：

1. `POST /tabs` 建 tab → navigate `https://passport.helixlife.cn/login?cb_url=...`（登录页是独立子域），等 3-4s。
2. 页面是 Element-UI：账号 `input[placeholder='请输入手机号或邮箱']`、密码 `input[type=password]`。**用 `/tabs/{id}/type`（mode=fill）填，不要自己用 JS setter**——fill 走真实输入事件，v-model 才吃。
3. 勾协议：`input[type=checkbox]` 里排除 `value='记住密码'` 的那个，点它的 `.el-checkbox__inner`。
4. 点登录：`button.login-btn:not([disabled]):not(.disabledBtn)`（页面上有 3 个「登录」按钮，多 tab 切换面板 + 一个 disabled，直接 `button:has-text('登录')` 会 strict mode 冲突）。
5. **点了登录还会弹「温馨提示 → 同意并继续」，必须再点一次才真正提交**。这一步不点，页面不动、cookie 里也没有 token，看着像登录失败。
6. 成功后跳到 `https://www.helixlife.cn/`，`document.cookie` 里出现 `token`（56 字符，形如 `1|xxxx`），直接 unquote 写进 `token.txt`。

凭证放同目录 `login.txt`（两行：账号/密码）。**注意用户会照抄示例文件里的注释行**——读文件时必须过滤 `#` 开头的行，否则把注释当账号/密码发出去。全程只打印「已填表/成功/token 长度」，不打印凭证。

## 列「你有哪些课」

- 课程列表端点 `/api/v1/edu/courses?type=mine`（`type=mine` 参数服务端忽略，返回全平台 189 门，分页 `page_size=100`、`data.meta.last_page`）。要拿「真正能下的」必须逐门验 play_auth（见坑清单第一条），189 门 ×2 请求、4 线程约 50 秒。
- 落成 `course_index.json`（no/title/uuid/videos），下载器用 `--index 6` 或 `--index all` 选课。
- camofox 代填表登录拿 token 的通用做法（先探登录方式 → 真实输入 → 假凭证验链路 → token 落点探测）见 `references/auto-login.md`。
