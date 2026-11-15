# 解螺旋 helixlife.cn 下载笔记

## 已落地脚本（macOS 版，改造完成）

`/Users/Jin/Documents/Open Programs/jlx-download/`

| 文件 | 说明 |
|---|---|
| `download_course.py` | 改造后脚本：`--course` / `--index` / `--token` / `--list` / `--start` / `--end` / `--out` / `--dry` |
| `jlx_login.py` | camofox 账号密码自动登录 → 抓 Bearer Token 写 `token.txt` |
| `list_courses.py` | 扫全平台课 → 按 play_auth 筛出有权限的 → 写 `course_index.json`（`--print` 打清单） |
| `course_index.json` | 编号索引 `{no, title, uuid, videos}`，按节数降序 |
| `.venv/` | aliyun-python-sdk-vod + aliyun-python-sdk-core + requests（清华源装） |
| `token.txt` | Token 落点（`jlx_login.py` 自动写入；也可用户自己粘） |
| `login.txt` | 账号密码两行（用户自己填，脚本读，不打印） |
| `README.md` | 原作者的原理说明（含后续 RAG/ASR 转知识库设想） |

默认输出目录：`~/Documents/视频/解螺旋`

```bash
cd "/Users/Jin/Documents/Open Programs/jlx-download"
.venv/bin/python list_courses.py --print                       # 刷新可下清单
.venv/bin/python download_course.py --index 6 --list            # 看某门课节次
.venv/bin/python download_course.py --index 6 --start 1 --end 1 # 单节试跑
.venv/bin/python download_course.py --index 6,12,55             # 批量，各建 06_课程名/ 子目录
.venv/bin/python download_course.py --course "<课程URL或UUID>"   # 单门直下
```

## 端点与参数

| 项目 | 值 |
|---|---|
| lessons 列表 | `https://api.helixlife.cn/api/v1/edu/courses/{course_uuid}/lessons` |
| 播放鉴权 | `https://api.helixlife.cn/api/v1/public/upload/play_auth?f=<encoded>` |
| f 参数编码 | `base64( url_encode( json({"video_id":"..."}) ) )`（json 无空格：`separators=(',',':')`） |
| video_id 来源 | `lesson.path.path`（= 阿里云 VOD VideoId） |
| 解密 key | `https://admin.helixlife.cn/api/v1/public/video/decrypt_key?CipherText=...`（需 Bearer，返回 16 字节） |
| PlayAuth 解析 | `json.loads(base64.b64decode(PlayAuth + '=='))` → AccessKeyId/Secret/SecurityToken/Region/VideoMeta.VideoId |
| m3u8 域名 | `vod-jlx.ciiczhaopin.com`；TS 分片无鉴权，直连 HTTPS |
| 课程 UUID 来源 | `https://www.helixlife.cn/edu/study/courses/{UUID}` 或 `/edu/courses/{UUID}/learn` |
| 必需请求头 | `authorization: Bearer <token>`, `platform: pc`, `source: PC`, `referer: https://www.helixlife.cn/` |

## 字段结构

- `GET lessons` → `{success, code, message, data:[{number, title, type, path:{path}}]}`，只保留 `type == "video"`。
- 清晰度优先 HD > SD > LD：按 `Definition` 排序取第一个 PlayURL。

## 登录页结构（passport.helixlife.cn）

首页 `.login-a` 点击后跳：`https://passport.helixlife.cn/login?cb_url=https%3A%2F%2Fwww.helixlife.cn%2F`

| 项目 | 值 |
|---|---|
| 登录方式 | 左侧微信扫码；右侧「账号登录」（手机号/邮箱 + 密码，**无图形验证码/无滑块**）/「验证码登录」 |
| 账号框 | `input[placeholder='请输入手机号或邮箱']` |
| 密码框 | `input[type=password]` |
| 登录按钮 | 选中 `button.login-btn:not([disabled]):not(.disabledBtn)`——页面上共 3 个文字为「登录」的按钮（账号/验证码两套面板各一个，其中一个 disabled），不收紧 selector 会 422 strict mode violation |
| 协议弹窗 | 未勾协议点登录会弹「温馨提示：请阅读并同意…」+「同意并继续」，不点它登录请求不发 |
| 失败提示 | 页面上出现「账号或密码错误」 |

自动登录脚本：`.venv/bin/python jlx_login.py`（凭证读 `login.txt`，成功写 `token.txt`）。通用做法见 `auto-login.md`。

## 课程清单与权限判定（实测跑通）

| 项目 | 值 |
|---|---|
| 课程列表 | `https://api.helixlife.cn/api/v1/edu/courses?type=mine&page=N&page_size=100` |
| 返回结构 | `data.meta = {current_page, last_page, total, page_size}`，`data.data[]` 每项有 `uuid/title/lesson_count/is_vip/user_course` 等 |
| 筛选参数 | **全部被忽略**：`type=mine` / `is_buy=1` / `type=bought` 与不带参数返回同一批（全平台 ~189 门）；`type=mine&status=all` 直接 `参数有误` |
| lessons | 对任何课都返回节次列表，**不校验权限**（无权限课也拿得到 42 节） |
| **权限判据** | 调 `play_auth`（第一节 video_id）：成功=`{#title}成功`；无权限=`该视频您无权限观看！` |
| 扫描耗时 | 189 门 × (lessons + play_auth)，`ThreadPoolExecutor(4)` ≈ 52s |
| 实测结果 | 该账号 89 门有权限 / 1641 节（粗略按 50MB/节 ≈ 80GB） |

不要在 lessons 层判断权限，也不要用 `user_course` 非空当「已购」——有过学习记录的只有 12 门，实际有权限 89 门。

## 实测状态（2026-10 全链路跑通）

- 已验证：依赖可导入；假 UUID + 假 token 请求 lessons 返回 `HTTP 200 {"success":true,"data":[]}`（该端点不校验 token）。
- 已验证：假凭证填表 → 提交 → 「账号或密码错误」，证明自动化链路通。
- 已验证：**真凭证登录成功**：勾协议 → 点登录 → 弹「温馨提示」→ 点「同意并继续」→ 跳回 `https://www.helixlife.cn/`；token 落在 `document.cookie` 的**非 httpOnly** `token` 字段（56 字符，形如 `数字|串`），`urllib.parse.unquote` 后直接可用。
- 已验证：`play_auth` 成功/无权限两种返回。
- **尚未实测**：`GetPlayInfo → decrypt_key → ffmpeg` 这一段真正下出 mp4（下次先单节 `--start N --end N` 试跑，再 `ffmpeg -i` 查音视频轨）。

## 后续用途

原作者打算把 mp4 转 RAG 知识库（FunASR 本地转录 → 分块带时间戳 → embedding → ES 混合检索）。本机已有转录管线：`Open Programs/whisper`，接 `video-transcript-pipeline`。
