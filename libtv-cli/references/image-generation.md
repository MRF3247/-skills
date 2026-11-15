# 一条龙生图：文生图 / 参考图风格迁移 / 编辑改图

适用：用户给一张参考图 + 一句话主题，要「同画风、换内容、指定比例」的成图；或纯文生图；或在成图上做局部修改。

## 0. 前置检查（按顺序，任一步失败先修再往下）

```bash
which libtv || bash <skill>/scripts/install-libtv-cli.sh   # 装到 ~/.libtv，需 export PATH
export PATH="/Users/Jin/.libtv:$PATH"
libtv account info      # 必须看到 memberAccount.effective=true；401=没登录，算力/会员看 memberName
```

登录：`libtv login phone -p <手机号>` → 用户回验证码 → `libtv login phone -p <手机号> -c <验证码>`。

## 1. 建画布并绑定目录（一次就够，之后所有命令不用带 `-p`）

```bash
mkdir -p <工作目录> && cd <工作目录>
cp <参考图> ./ref-style.png
libtv workspace list                    # 取 workspaceId
libtv workspace use <workspaceId>
libtv project create "<画布名>" -d "<简介>"   # 取 uuid
libtv project use <uuid>
libtv upload "参考图" -t image --resource ./ref-style.png
```

参考图不止一张时（画风图 + 真实人物照片）逐张 `libtv upload` 命名，生成节点用多个 `--left`，提示词里用「第一张参考图／第二张参考图」指明各自作用。

## 2. 先决定：重画（图生图）还是改图（编辑指令）

| 目标 | 做法 | 模型 |
| --- | --- | --- |
| **只要「风格像」，内容可以重画** | image2image + 画风段/内容段提示词 | `nebula-ultra`（General image Pro，quality 1K/2K/4K，image2image 0~7 张） |
| **要「画风+配色+构图都像」，只换局部元素** | 编辑指令：「保持…完全不变，只改这三处」 | `lib-image-2.5-s`（Lib Image 2.5 Pro，`quality=max`、`resolution=4K`、image2image 0~14 张） |
| **画风配色必须锁死，但构图要重排** | 「沿用第一张参考图的画风与配色，完全重新设计构图」+ 前景/中景/上方分区描述 | 同 `lib-image-2.5-s`（`quality=max`、`resolution=4K`）；**不要**退回 nebula-ultra |
| 中文文字/海报排版 | 文案整段内嵌 + 区域标签 | `doubao-seedream-5-0-pro`（Seedream 5.0 Pro，quality 只到 2K） |
| 极速试稿 | 单张参考图 | `z-image`（Z-image Turbo） |

要「同画风同配色换主题」时**直接走编辑指令那行**。图生图重画会连配色一起重新决定，用户按色值验收时会判为「差别极大」。`-s model=` 填 **modelName**。

## 3. 提示词写法

**编辑指令模式（保风格首选）**——三段固定结构：

1. 「保持第一张参考图的画风、配色、光线、构图、人物造型、所有物体形状完全不变，只做以下 N 处修改：」
2. 逐条编号写要改的东西（人物服装/长相、道具内容、印章）。改人物长相时写明「长相参考第二张照片里的人」，并列出可识别特征（发型、胡须、眼镜、衬衫颜色）。
3. 收尾兜底：「除此之外不要改动任何东西：<主色三色>的配色比例完全照原图，<画风关键词>不变，<关键物体>的位置不变。不要出现其它文字。」

**重画模式**（编辑做不到、或要完全新构图）——两段式：画风段（复述参考图可见特征）+ 内容段（上→中→下 / 左→右写主体动作、道具、背景）。

规则：

- 颜色一律自然语言，不写色号（会被渲染成乱码文字）。
- 要出文字就把文案整段内嵌；不要文字也要意识到模型会补英文（印章常被补 REJECTED/APPROVED）。
- 主题带真实人物时，先从源文档取该人照片当第二张参考图，别让模型自由发挥长相。

## 4. 发命令：用 Python subprocess 传参

提示词必带中文引号与括号，bash 双引号会被吃掉。写成脚本跑：

```python
import subprocess, os
env = dict(os.environ); env["PATH"] = "/Users/Jin/.libtv:" + env["PATH"]
cmd = ["libtv", "node", "create", "<节点名>", "-t", "image",
       "--left", "参考图", "--left", "人物照片",
       "-s", "model=Lib Image 2.5 Pro",
       "-s", "modeType=image2image",   # 有参考图入边就必须显式设
       "-s", "ratio=3:4", "-s", "quality=max", "-s", "resolution=4K",
       "-s", "count=1", "--prompt", PROMPT, "--run"]
print(subprocess.run(cmd, cwd=WD, env=env, capture_output=True, text=True).stdout)
```

各模型 settings 键不同：nebula-ultra / seedream 用 `quality=1K|2K|4K`；lib-image 系用 `quality=low|medium|high|xhigh|max` + `resolution=1K|2K|4K`，混用会报「不在允许范围」。

`--run` 是同步阻塞命令，内部已轮询到终态；不要再包一层轮询，也不要后台跑。改已有节点参数后重跑：`libtv node "<节点名>" -s quality=2K --run`。

## 5. 取图 + 双重自检

`--run` 的 stdout 终态 JSON 里 `data.url[]` 就是 **CDN 原图（无水印）**：

```bash
curl -sSL -o final.png "<data.url[0]>"
python3 -c "from PIL import Image;im=Image.open('final.png');print(im.size, round(im.size[0]/im.size[1],4))"
python3 -c "from PIL import Image;im=Image.open('final.png');im.thumbnail((900,1200));im.convert('RGB').save('preview.jpg',quality=90)"
```

**自检 A（视觉）**：把 `preview.jpg` 送 vision 模型，逐项问：人物数量与肢体有无畸形、有无乱码/多余文字、印章上到底是哪个单词、画风有没有跑偏、服装是否符合主题（医生服 vs 科研衬衫）。

**自检 B（配色，保风格任务必做）**：量化主色板与参考图逐色对比，别靠肉眼说"接近"：

```python
import collections
from PIL import Image
def palette(p, n=8):
    q = Image.open(p).convert('RGB').quantize(colors=n, method=Image.MEDIANCUT).convert('RGB')
    c = collections.Counter(q.getdata())
    return ['#%02X%02X%02X' % k for k, _ in c.most_common(n)]
print('ref', palette('ref-style.png'))
print('out', palette('final.png'))
```

两行色板并排看：出现「参考图没有的色系」（例如参考图无灰绿而输出主色是 #63969E）、或同色相明度差一档，就是配色漂移，换编辑指令模式重出，**不要在像素上做后处理补偿**。

## 6. 交付

- 原图存 `<工作目录>/<主题>-<比例>-<档位>.png`；正面用 `MEDIA:<绝对路径>` 给出，另给一张「参考图 | 成图」并排对比图，用户要对照画风。
- 回话报：像素尺寸 + 实际比值（3:4 记 0.74~0.75）、模型、色板对照表、自检发现的问题（印章英文、残留眼镜等）+ 一句「要不要改」的可选项。
- 多轮迭代时每轮都给「上一版 | 新版」并排图，**并主动报出本轮副作用**（改了 A 结果 B 也变了），再给「要不要拉回」的选项——不要等用户自己发现。

## 7. 换构图 / 多轮迭代

**要换构图（人物站位、镜头关系全变），但画风配色不许动**：仍用 `lib-image-2.5-s`，参考图只当画风锚，提示词里**绝不能**出现「保持构图不变」，改成：

```
沿用第一张参考图的画风与配色，完全重新设计构图，画一张竖版 3:4 的编辑插画。
【画风与配色照抄参考图，一点都不能改】<画风关键词>；配色只用这几只颜色：<主色 3~4 个自然语言色名>；禁止深色压场、禁止其它色系。
【构图】
前景右侧（画面下方三分之一，全身像）：<主角> 穿<具体服装>，<姿态>，<表情/情绪>。
中景左侧（稍小、在主角身后）：<配角> 正在<动作>，身体前倾、<细节>，表情<情绪>。
画面上方（占上半幅三分之一）：<漂浮/铺满的道具>，<动势方向>，背景是<底色>。
【细节】人物比例正常；两者情绪对比强烈；有前后景层次，主角最大最靠前。
【不要】<要排除的旧设定>；除 <指定英文> 不要出现别的文字。
```

分区写「前景/中景/上方」+ 明确情绪对比（如得意 vs 焦急），一次就能出到用户能接受的程度。

**多轮局部迭代**：把上一版成图 `libtv upload "v5构图" -t image --resource ./v5.png`，生成节点 `--left v5构图 --left 人物照片 --left 参考图`，指令写成「保持构图、人物位置与姿态、画风完全不变，只做以下两处修改：①…②…」，最后补一句「其余全部保持原样：<逐项点名>」。

**坑：改一个属性会连带漂相邻属性**。指令只说「背景去黄、脸提亮」，实测蓝色也从参考图的 #62A1BB 亮到 #88C7F8。所以「其余不动」清单要逐项点名（含主色、印章红），验收时对每一项单独跑一次色板比对；漂了就再出一版，或明说副作用让用户挑。
