# libtv 生图引擎细节（2026-08 实测）

数据源：`libtv model search --type image` + `libtv model <modelKey>`（schema 权威）。中文海报任务的核心选型依据。

## 引擎总表

| modelKey | modelName | 定位 | 中文文字 | quality 范围 | count | ratio 含 3:4 | 实测 |
|---|---|---|---|---|---|---|---|
| doubao-seedream-5-0-pro | Seedream 5.0 Pro | 精准交互式编辑、原生多语言排版 | **强（首选）** | 1K/2K | 1/2/4 | ✅ | 8.5~9.3/10 |
| seedream-4 | Seedream 4.0 | 极速高质、支持中文文字与海报设计 | 中（OCR 依赖重） | 2K/4K | 1/2/4 | ✅ | 3.5/10（文案丢失） |
| seedream-4.5 / jimeng-4.6 / seedream-5 | Seedream 4.5 / 4.6 / 5.0 Lite | 中式风格、人像一致 | 未测 | 各异 | 1/2/4 | ✅ | — |
| nebula-ultra | General image Pro | 最强图片编辑、一致性 | 未测（编辑向） | 1K/2K/4K | 1/2/4 | ✅ | — |
| nebula-2-flash | General image V2 | 联网搜索、文字准确 | 未测 | 各异 | — | — | — |
| lib-image-2 | Lib Image | 长文本能力突出 | 未测 | 各异 | — | — | — |
| qwen | Qwen Image | 文字排版能力强 | 未测 | auto | 1/2/4 | ✅ | — |
| mj-v8.2 / mj-v8.1 / mj-v7 / mj-niji7 | 悠船系列 | 电影感/美学 | 弱（西文向） | — | — | — | 不适合中文海报 |
| z-image | Z-image Turbo | 极速、真实感 | 弱 | — | — | — | — |

## 验证过的关键命令

```bash
# 列引擎
libtv model search --type image
# 看某引擎 schema（count/ratio/quality/modeType/settings）
libtv model doubao-seedream-5-0-pro
# 抽卡生成（图生图改风格：参考图连左侧）
libtv node create "节点名" -t image \
  -s "model=Seedream 5.0 Pro" -s ratio=3:4 -s quality=2K -s count=2 \
  -s modeType=image2image \
  --left "参考图-xxx" --prompt "完整文案提示词" --run
# 下载节点产物（落 cwd：<节点名>_1.png、_2.png）
libtv download -n "节点名"
```

## schema 关键字段语义

- `properties.count`：出图张数（抽卡数），doubao/seedream-4 均 [1,2,4]
- `properties.ratio.enum`：比例列表；小红书竖版用 `3:4`
- `properties.quality.enum`：分辨率档位，**各引擎不同**（doubao 无 4K，传了会校验失败）
- `properties.modeType.items.image2image`：`[min, max]` 允许的参考图数量范围（doubao [0,10]）
- `config.settings`：可拍平写顶层的表单字段（quality/ratio）
- `config.advancedSettings`：高级设置（如 sequential 组图开关；默认开，可能让引擎自作主张拆组图，海报任务建议关）

## 实测评分记录（套系A「矢量扁平医学风」）

引擎 doubao-seedream-5-0-pro，图生图 + 完整文案内嵌，抽 2 卡选优：

- v1 seedream-4（"保持原图文案不变"）：3.5/10 —— 五步列表丢失、色号 #0E4C4C 被渲染成乱码文字
- v2 doubao（文案内嵌）：单卡 7.5~9.3，精选后 8.5~10
- 同提示词两张卡差异大（10/10 vs 7.5/10）→ 抽卡是刚需
- 高频错字模式：形近字（哪帕/哪怕、掉漏/漏掉）、长句丢逗号

## 失败模式速查

| 报错 | 原因 | 修复 |
|---|---|---|
| 入边组合校验失败：图片生成节点须为图生图模式 | 有参考图入边但没设 modeType | 加 `-s modeType=image2image` |
| params.settings.quality="4K" 不在允许范围 | 引擎不支持该档位 | `libtv model <key>` 看 enum，doubao 用 2K |
| 模型只接受 modelName | 传了 modelKey | 用 search 输出里的 modelName（如 "Seedream 5.0 Pro"） |

## 节点/画布命令备忘

- 画布 UUID 与 项目ID 不同：`libtv project create` 输出 `projectMeta.uuid`；`workspace create` 输出 `workspaceId`（整数）
- `libtv project use <uuid>` 把 cwd 绑定到画布（写 .libtv/project.json），后续省略 -p
- `libtv upload "名字" -t image -f <path>` 建资源节点，输出 nodeKey + cdnUrl
- `libtv node create ... --run` 同步阻塞，stdout 终态 JSON 里有 `data.url[]` 和 `resourceMeta.items[].width/height`
- 画布网页查看：`https://www.liblib.tv/canvas?projectId=<画布UUID>`
