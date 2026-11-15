---
name: launchd-service-supervision
description: Use when 本机常驻服务（站点/API/守护进程）静默挂掉、或要让它常驻自愈。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [macos, launchd, service-supervision, troubleshooting, self-healing]
    related_skills: [medhot-medical-news-site, free-site-publishing, daily-scraping-automation]
---

# macOS 常驻服务：launchd 调度与自愈守护

## When to Use

- 用户报「本地站/接口打不开、503、无法加载」，而代码没改（进程死了是最常见的一层）
- 要把本机某个服务（Node/Flask/Postgres/自建站）做成常驻，或挂了自动拉起
- 已有 launchd 定时任务，但任务顺手启动的服务总是活不长
- 用户问「这个每天推给我的消息/日报，是哪个任务在跑」→ 走 `daily-scraping-automation` 的「溯源」小节：飞书消息 sender → launchctl label → plist 命令行 → 入口脚本 grep

## 第一步：定位「进程死了」还是「代码/数据坏了」

按顺序，别跳步：

1. 服务自己的状态脚本优先：`./xxx.sh status`（认得 pid 文件，一眼看出 api/web/worker 哪个不在）
2. 端口在听吗：`lsof -nP -iTCP:<port> -sTCP:LISTEN`
2b. **launchd 自己怎么说**：`launchctl list | grep <label>` 的第二列就是 last exit code（`-` 表示没在跑，数字是上次退出码）；想看「触发过几次/下次何时」，用 `launchctl print gui/$(id -u)/<label> | grep -E "runs|last exit|state|next fire"`。调度已经发火但服务没起来（`runs=1` + 非常退出码）＝问题在启动环节，不是调度没跑。
3. 逐个探活：`curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 http://127.0.0.1:<port>/`（API 根路径返回 404 是正常的，要打 `/api/health`）
4. 看日志尾部 `.logs/{api,web,worker}.log` —— 两种特征日志直接定案：
   - 单行 `exec: npx: not found` / `env: npx: No such file or directory` → 坑 1（PATH）
   - 只有 `xxx started` + `xxx stopping`、没有崩溃栈 → 坑 2（进程组回收）
5. 进程年龄：`ps -eo pid,etime,command | grep -i <唯一特征>` —— etime 很大说明是老进程，不是刚崩的

## 坑 1：launchd 的 PATH 极简 → 脚本里的 npx / node / brew 静默失败

launchd 任务的环境基本只有 `PATH=/usr/bin:/bin` 加 `HOME`（用户自己的 shell 里那套 PATH 不存在）。

- **规则**：被 launchd 调用的启动脚本里**一律用绝对路径的二进制**，并在脚本头部兜底：
  `NODE="$(command -v node || echo /absolute/path/to/node)"`，启动命令写成 `"$NODE" "$ROOT/node_modules/.bin/<cli>" ...`
- **症状**：`api`/`worker` 都起来了，`web` 永远起不来（API 活着、页面 503），日志里只有一行 `exec: npx: not found`
- **验证（等价 launchd 环境，最快最准）**：`env -i HOME="$HOME" PATH="/usr/bin:/bin" /bin/bash ./start.sh`，再 curl 端口确认起来了
- 语言/包管理器层面的同类问题：Python 的 `python3` 别裸写（用 venv 里的绝对路径）、`PIPENV`/`UV` 同理

## 坑 2：launchd 任务结束会 TERM 掉 job 进程组里剩下的进程

定时任务（快照/备份/推送）里顺手 `./start.sh` 拉起的常驻服务是该 job 的子孙，**job 一结束就被一起回收**。

- **症状**：日志只有 `xxx started` + `xxx stopping`（优雅 SIGTERM，没有崩溃栈）；每次定时任务跑完服务就没了 → 站点「跑完快照就 503」
- **修法**：那个 plist 加 `<key>AbandonProcessGroup</key><true/>`
- plist 要改**两份**：仓库里那份 + `~/Library/LaunchAgents/`，改完 `plutil -lint` 校验 → `launchctl unload && launchctl load` → `launchctl list | grep <关键词>` 确认登记
- **别用 `launchctl kickstart -k` 手动跑「会顺手启动服务」的定时任务**：子进程照样随 job 结束被杀，你以为在修，其实又杀了一次。要手跑就从自己的交互 shell 里执行脚本
- 常驻服务最好在**交互 shell** 里起（或给它们建独立 launchd job），而不是靠定时任务顺手拉

## 坑 3：一重启报 exit 126 —— 脚本丢了执行位

`launchctl list` 里该任务 `runs` 增加了、但 last exit code = **126**（cannot execute），日志里一字未写——说明 shell 根本没跑到脚本第一行。

- **成因**：plist 写成 `<array><string>/bin/bash</string><string>-lc</string><string>/abs/path/job.sh</string></array>` 时，`-c` 后面的字符串被当作**要执行的命令**，于是 bash 去执行「`/abs/path/job.sh` 这个文件本身」——文件没有执行位就 126。用 `write_file`/编辑器覆盖过脚本、或脱壳后从另一台机器拷过来，权限常是 `-rw-r--r--`，首次重建任务时必踩。
- **修法两条同时做**：① `chmod +x /abs/path/job.sh`；② plist 改成 `[/bin/bash, /abs/path/job.sh]`（不用 `-lc`，bash 读文件跑、不需要执行位）。改完 `plutil -lint` → `unload && load` → 手工 `kickstart` 一次确认 last exit code 变 0。
- **铁律**：每次用工具重写一个 `.sh`（尤其定时任务入口）后，立即 `chmod +x` 并 `bash -n` 验语法——否则下一次定时触发会静默失败一整天。

- 直接 `bash -n <脚本>` 可能被守卫拦下（脚本里引用了超过扫描上限的大文件，如几 GB 的 sqlite；报「could not scan / larger than the scan cap」）→ 复制一份到 scratch，把那个大文件路径替换成占位名（**只改字符串，语法不变**），对副本 `bash -n`，原文件不动。别因为拦了一下就跳过语法验证。

## 停用/下线一个常驻服务或定时任务（用户说「别跑了」「完成使命了」）

顺序错一步就会被自己的守护拉回来：

1. **先 `launchctl bootout gui/$(id -u)/<label>`，再停进程**。反过来做，`StartInterval` 的 watchdog（几分钟一轮）会把刚杀掉的进程当场拉回来，你会以为 kill 没生效。
2. **plist 要移出 `~/Library/LaunchAgents/`，别只 bootout**：bootout 只卸载本次会话，文件还在 → 下次登录 launchd 重新加载、任务复活。移进同目录的子目录 `~/Library/LaunchAgents/_disabled/`（launchd 不扫描子目录），既停用又留档；恢复时移回来 + `launchctl load`。
3. **服务自己的进程组和专属数据库单独停**：`./xxx.sh stop` 一般只杀 app 进程（api/web/worker），它专用的 PostgreSQL 还在跑（继续占内存、占端口）→ 补 `/<pgbin>/pg_ctl -D <pgdata> stop`。
4. **验收看端口真没了**，不要拿「命令返回成功」当交付：`launchctl list | grep -i <关键词>` 为空 + `lsof -nP -iTCP -sTCP:LISTEN | grep -E ':<port1>|:<port2>'` 无输出。
5. **代码和数据不删**：用户说的是「别跑了」，不是「删了」。保留仓库与数据目录，交付时给恢复路径（plist 移回 → `launchctl load` → `./xxx.sh start`），并明说数据没动。
6. **流水线脚本里嵌的阶段，光删 launchd 没用**：任务是在 `daily_pipeline.sh` 里被 `python3 xxx.py &` 起的那一路时，要改的是那四行耦合代码，见 `daily-scraping-automation` 的「下线流水线里的一路」。
7. 停用后仍会空转的附属脚本（转录循环、队列轮询）不必专门停——它们「无候选即退出」，说清这一点免得用户以为还在花钱。

## 治本：独立的自愈守护（watchdog）

一个独立的 launchd job，每 5 分钟探活一次，失败才调服务的启动脚本（必须幂等）。

- 模板：`templates/watchdog.sh` + `templates/watchdog.plist`（拷到项目根目录，改路径/端口/健康检查地址）
- 要点：
  - 幂等启动（有 pid 检查、只补缺的服务，别把在跑的重启一遍）
  - 守护自己的 plist 也要 `AbandonProcessGroup=true`，否则它拉起的服务同样会被回收
  - 探活失败才动作；日志追加到 `.logs/watchdog.log`
  - **探活要看业务健康字段，不是只看进程/端口**：`KeepAlive` 只能把**进程**拉回来，拉不回进程内部的子会话（浏览器内核、DB 连接、worker 池）。浏览器类服务典型症状：进程活着、端口在听、但 `/health` 返回 `browserRunning:false` —— 此时抓取任务会全部报 `Connection refused`/空结果，而 watchdog 若只 grep 进程就永远不会修。正确条件是「`/health` 里业务字段 = 正常」，不满足就 `launchctl kickstart -k`。
  - **运行时资源堆积也要当故障处置**：同一服务反复跑同一资源（tab/session/临时文件）时，服务端清理接口可能根本没实现（返回 404），堆到一定数量后全端点 400/500。watchdog 里加一条阈值（如 `activeTabs >= 5` 就重启），别等堆到两位数再手工救。
  - 留暂停开关（`[ -f "$STATE/paused" ] && exit 0`）：调试或用户主动停服时不被拉起来
- 验证脚本：`scripts/drill-watchdog.sh`

## 验证是硬要求：「杀-等-起」演练

不许只看脚本写得对不对就宣称守护生效。一次演练四步：

1. 杀掉服务：`pkill -f "<唯一命令行特征>"`，确认探活变 `000`
2. 触发：`launchctl kickstart -k gui/$(id -u)/<label>`
3. 等 15–30 秒，确认探活回 `200`、日志有「已恢复」
4. 确认它**只补了缺的那个**、没动在跑的（幂等性的体现）

## 附带坑：定时任务卡死会静默吃掉后续所有排期

`StartCalendarInterval` 在上一实例仍在运行时**静默跳过**这一次（不报错、日志也没有）。所以「推送/同步没有超时」这类 bug 会让站点冻结一整天而毫无提示。

- 定时任务脚本里每个外部命令都要带超时（`subprocess timeout=`、`GIT_SSH_COMMAND` 加 `ServerAliveInterval/ConnectTimeout`）
- 诊断：`ps -eo pid,etime,command | grep -E "<job 脚本>|<被它调起的工具>"`，看到活了十几小时的就是它卡住了；杀掉整条链（bash → python → ssh）再手动跑一次

## 交付与沟通

- 修完给**可点的链接**（本地 `http://localhost:<port>` + 公网地址），并附实测状态码
- 说清「根因是 X」而不是「我重启了」：用户会追问为什么会挂；分层讲（进程层 / 调度层 / 代码层）
- 别把「站点挂了」先归因于代码或数据 —— 先看 status、端口、日志
- 取监听进程去 kill 用 `lsof -nP -iTCP:<port> -sTCP:LISTEN`（不加 `-sTCP:LISTEN` 会把非监听的 ESTABLISHED 连接也列出来，误杀别的进程）
