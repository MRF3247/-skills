---
name: libtv-cli
description: >-
  LibTV 官方 CLI（libtv）：在命令行里完整操作 / 运行 LibTV 画布。
  凡是和 LibTV 画布 / 项目 / 节点 / 模型 / 素材相关的操作，一律通过 libtv CLI 完成，
  不要自己捏造 HTTP 请求或绕到网页端步骤。本 skill 内即包含完整的 CLI 命令操作手册；
  常见场景见 examples/，安装/更新见 scripts/install.md。
---

# LibTV CLI（`libtv`）

`libtv` 的文档地图。子命令与选项权威文案以 `libtv --help` 与 `libtv <子命令> --help` 为准；当文档与 `--help` 不一致时，以 CLI 实际输出为准并修订本 skill。

**术语**：本 CLI 里 **画布（project）** 是真正的画布文件，**项目（workspace）= 工作区** 是装画布的容器，一个项目下可放多张画布。

**画布 / 分组范围**：在画布所在工作目录执行 `libtv project use <画布UUID>`，写入 `.libtv/project.json` 的 `projectUuid`；之后大多数子命令（`libtv node` / `libtv upload` / `libtv group`）在省略 `-p` / `--project` 时即使用该画布。需要限定到某个普通分组时，再执行 `libtv group use <分组>` 写入 `groupNodeKey`。详见 [commands/project.md](./commands/project.md)、[commands/group.md](./commands/group.md)。

**项目（工作区）绑定**：用 `libtv workspace use <项目ID>` 把目录绑定到一个项目（工作区），写入 `.libtv/project.json` 的 `workspaceId`，用于 `project create` / `project list` 的默认项目范围。`workspace use` 不设置默认画布，会清掉原 `projectUuid` / `groupNodeKey`；`project use` 会写入画布，并把该画布实际所属的 `workspaceId` / `teamId` 同步进本地状态。详见 [commands/workspace.md](./commands/workspace.md)。

## 文档地图

| 主题                                                                                  | 文件                                                             |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 一键安装 / 指定版本安装                                                               | [scripts/install.md](./scripts/install.md)（脚本与本文件同目录） |
| 管道（NDJSON）、stdout/stderr、嵌套 case                                              | [examples/pipes/README.md](./examples/pipes/README.md)           |
| 常见案例（场景化可复制命令集，**每个 case 一文件**）                                  | [examples/README.md](./examples/README.md)                       |
| `libtv login web` / `libtv login phone`                                               | [commands/login.md](./commands/login.md)                         |
| `libtv logout`                                                                        | [commands/logout.md](./commands/logout.md)                       |
| `libtv account`（含 `info` / `list` / `use`）                                         | [commands/account.md](./commands/account.md)                     |
| `libtv workspace`（项目/工作区，含 `create` / `list` / `update` / `use` / `unuse`）   | [commands/workspace.md](./commands/workspace.md)                 |
| `libtv project`（画布，含 `create` / `list` / `update` / `use` / `unuse` / 默认摘要） | [commands/project.md](./commands/project.md)                     |
| `libtv node`（含 `create` / `list` / `delete` / 默认用法）                            | [commands/node.md](./commands/node.md)                           |
| `libtv group`（含 `list` / `create` / `use` / `unuse` / 默认用法）                    | [commands/group.md](./commands/group.md)                         |
| `libtv upload`                                                                        | [commands/upload.md](./commands/upload.md)                       |
| `libtv image`（`shortcut list` / `shortcut <scene label> -n <node>`）                 | [commands/image.md](./commands/image.md)                         |
| `libtv script`（含 `storyboard`：从脚本节点生成分镜图组）                             | [commands/script.md](./commands/script.md)                       |
| `libtv model`（含 `search` / 默认完整 schema）                                        | [commands/model.md](./commands/model.md)                         |
| 画布节点类型（`-t` 枚举、对应 `-s` / `-u` 字段）                                      | [node-types/README.md](./node-types/README.md)                   |
| 模型 schema 字段（`properties` / `config` / `rules` / `modeType`）                    | [model-schema/schema.md](./model-schema/schema.md)               |
| **一条龙图生图 / 参考图风格迁移（命令序列 + 脚本骨架 + 模型速查）**                   | [references/image-generation.md](./references/image-generation.md) |

## 关键坑（实测踩出来的）

- **批量生成脚本别用 bash 双引号包提示词**：提示词内部常有半角双引号（如 `"STEP 01"`），外层再包 `"..."` 会提前闭合引号、整行被 shell 拆成命令执行（报 `command not found`）。用单引号包裹提示词，或直接用 Python subprocess 传参（推荐，彻底免疫）。
- **图生图必须显式设 `-s modeType=image2image`**：image 节点连了参考图入边但没设 modeType 时，校验报「图片生成节点须为图生图模式才允许图片参考入边」。
- **提示词里不要写色号（如 `#0E4C4C`）**：会被生图引擎当成正文文字渲染成乱码（实测出现 "0E4C4" 残留字样）。颜色一律用自然语言描述（"深墨绿色"）。
- **生图引擎 OCR 原图文字不可靠**：提示词写"保持原图文案不变"会丢正文（五步列表全丢）。长文案必须显式内嵌在提示词里 + 用【顶部】【中部】等区域标签描述版式位置，文字越多越要逐条列出。
- **抽卡选优是刚需**：同一提示词 count=2 的两张图，可能一张 10/10 一张 7.5/10（错字/丢标点随机）。文字密集的海报至少抽 2 卡。
- **画布准备三连**：`libtv workspace use <文件夹id>` → `libtv project create "名字"` → `libtv project use <uuid>`，再 `libtv upload` 参考图、`libtv node create ... --run`。
- **中文海报首选 doubao-seedream-5-0-pro**（Seedream 5.0 Pro，原生多语言排版）：「完整文案内嵌+区域描述」策略下实测 7.5~9.3 分，明显优于 seedream-4（3.5/10）。
- **`-s quality` 取值范围因模型而异**：doubao-seedream-5-0-pro 只收 1K/2K，seedream-4/jimeng 收 2K/4K，nebula-ultra 收 1K/2K/4K。传错报「不在允许范围」。
- **AI 生成水印**：Liblib 生图自带「AI生成」标签 + 右下角 LibTV logo。**去水印正解：`libtv node <节点>` 查询拿 `data.url[]` 的 CDN 原 URL，用 curl/urllib 直接下载 = 无水印原图**（CLI `libtv download` 会叠加水印；`--without-ai-watermark`/`--vip`/`LIBTV_DOWNLOAD_IS_VIP=1` 实测未生效）。OpenCV inpaint、编辑模型（qwen-edit/nebula-ultra/doubao）去水印均实测失败，勿再试。
- **登录优先用 `libtv login phone -p <11位手机号>`，再用 `-c <验证码>` 收尾**：`login web` 依赖浏览器自动回调本机端口，回调不落地时进程只在 stderr 打「等待浏览器回调超时」而 `credentials.json` 不生成，`libtv account info` 继续报 401；手机号链路一步到位、无回调依赖。`login web` 超时后必须重新发起（端口会变），旧链接作废。
- **报「算力不足 [1200000136]」先查是否登错账号**：该错误对所有模型、所有 quality 一律返回，不是模型或参数问题。先 `libtv account info` 看 `memberAccount.memberName` / `accountLevel`，确认是不是有额度的那个号。
- **换账号后旧画布/工作区全部失效**：画布 UUID 与 workspaceId 是账号作用域内的，`logout` → 重新 `login` → `workspace list` 取新账号的 workspace → `workspace use` → `project create` → `project use` → **重新 `upload` 参考图**（旧节点的 `i-xxx` nodeKey 与 CDN URL 属于旧账号，复用会失败）。
- **`-s model=` 只认 modelName，不认 modelKey，且空格敏感**：`nebula-ultra` 是 `General image Pro`，`doubao-seedream-5-0-pro` 是 `Seedream 5.0 Pro`，`z-image` 是 `Z-image Turbo`。传 key、或少写一个空格（`Seedream5.0 Pro`）都报「未找到模型名字」。
- **`libtv model <modelKey>` 打印的 `schema.modelName` 可能是无空格写法，不能直接拿去用**：实测同一条 seedream 5.0 pro，`model <key>` 的 schema 里印成 `Seedream5.0 Pro`，照抄就报「未找到模型名字」；`libtv model search <关键词> -t image` 返回的 `modelName`（`Seedream 5.0 Pro`）才是能传的值。**两处冲突时信 `model search`**；`model <key>` 那一份仍可用来查 `ratio` / `quality` / `modeType.items` 的允许值。
- **4K 的 3:4 实际输出 3584×4800（比值 0.7467）**：4K 档按长边取整，不会精确等于 0.75。验收比例时按 0.74~0.75 判断，不要判为比例错误。
- **提示词写「不要任何文字」并不能保证零文字**：模型仍会给印章、标签自行补英文单词（例如给圆形印章补 `REJECTED`）。要指定文案就显式写进提示词，不要只靠「不要文字」这句否定。
- **「保留参考图的画风与配色」不能用图生图（image2image）做**：以参考图入边 + 「画风段 + 内容段」提示词生成（nebula-ultra / Seedream 5.0 Pro 都试过），产出会自行重绘光线与色相——蓝色偏灰青、背景奶油黄偏土、明度整体压低，被用户一眼判为「色值差别极大」。正确做法是**编辑指令模式**：用 `lib-image-2.5-s`（modelName `Lib Image 2.5 Pro`）配 `-s quality=max -s resolution=4K`，提示词写成「保持第一张参考图的画风/配色/光线/构图/物体形状完全不变，只改这三处：①…②…③…，除此之外一切不变」。实测主色逐色吻合参考图（奶油黄 #FEF8D7→#FDF8D6、主蓝 #62A1BB→#619AB4、深蓝 #14447F→#244877）。完整流程与验收方法见 [references/image-generation.md](./references/image-generation.md)。
- **别用后处理色彩迁移去补救配色**：Reinhard LAB 均值/方差对齐会被参考图自带的灰绿调带跑，整图发绿（蓝→绿青）；「限定色板重映射」会保住红标记却把肤色当成红色保留，人物脸上全是红斑，整体退化成复古丝印感。配色不对就换模型/换模式重出，不要在像素上拧。
- **编辑指令改一处会连带漂相邻属性**：只说「背景去黄、脸提亮」，实测蓝色从 #62A1BB 亮到 #88C7F8。指令结尾必须逐项列「其余不动」（主色、印章红、画风），交付时主动报出漂移项并给「要不要拉回」的选项，别等用户自己发现。
- **换构图不等于换模型**：画风配色要锁死、只是重排人物站位时，仍用 `lib-image-2.5-s` 并以参考图作画风锚，提示词写「沿用画风配色 + 完全重新设计构图」再按前景/中景/上方分区描述，不要退回 nebula-ultra（会连配色一起重画）。写法模板与多轮迭代路径见 [references/image-generation.md](./references/image-generation.md) §7。
