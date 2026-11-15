# 核验命令、判读阈值与无效口径

## 提帧

```bash
# 首帧（macOS 自带，无需 ffmpeg）
sips -s format png g1.gif --out g1_f.png

# 时间轴 5-9 帧（帧号按总帧数铺开）
ffmpeg -y -i g1.gif -vf "select='eq(n,0)+eq(n,10)+eq(n,20)+eq(n,30)+eq(n,40)+eq(n,50)'" \
  -vsync vfr -frames:v 6 a_%d.png

# 最后 1 秒（验结尾状态，必须单独做）
ffmpeg -y -sseof -1.0 -i g1.gif -vsync vfr e_%d.png
# 只要最后一帧
ffmpeg -y -sseof -0.06 -i g1.gif -vsync vfr -frames:v 1 lastend.png
```

⚠️ `select='eq(n,N)'` 里 N 超出总帧数时**静默少出图**：请求 7 张可能只出 6 张且不报错。脚本里若按预期文件名列表发问，会 FileNotFoundError 白跑一轮——先 `ls` 实际文件。

## 量规格

```bash
# 时长 / 分辨率 / fps
ffmpeg -i g1.gif 2>&1 | grep -E "Duration|Stream #0"
# 实测帧数（别用 时长 × fps 算）
ffmpeg -i g1.gif -f null - 2>&1 | tail -3   # 读 frame= N
```

## 位移探针判读

`/Users/Jin/Documents/Hermes/venvs/huashu/bin/python3 scripts/gif_motion_probe.py <gif> [暗阈值=110] [区域=x0,x1,y0,y1]`

- 区域用 0-1 比例。**默认 0,1,0,0.6（全宽+上部 60%）适合看头部**；整帧质心会被身体/背景稀释，头部质心用裁切区域才敏感。
- 判读：数百 px 画面里极差 **<3px ≈ 无整体位移**；几十 px 才是明显位移。
- **目标化变体（推荐先试）**：全帧“暗区”会被衣服/背景稀释，探针应打在**颜色可区分的部位**上——人脸用肤色（R>150, G>105, B<135, R>G>B 且 R−B>40），动物头用深色毛块。经验值：暗阈值 80 在小图上零匹配，100~140 才有信号；肤色块在 350px 宽画面上留下 3.55px（≈1%）的平滑往返（203→206→204）＝“极轻微摆动/近静帧”；4~8px／246px（≈2~3%）＝“轻摇”。
- **数字只写幅度，不替动作下结论**：px 与占比照实写（便于用户判断能不能用），措辞停在“趋近静帧 / 轻摇”，**不要写成“它在摇头”**；细微动作的决定性结论靠裁切放大后的多帧视觉核验。
- **只能证伪大位移，不能证明「绝对没动」**；细微位移要靠裁切放大后让视觉模型逐帧比。
- ❌ **不要用相邻帧差分定位动作**：GIF 调色板抖色让每个像素都在抖，差异区竖直跨度会接近整帧（实测 350/372px），结论永远是「全身在动」。
- ❌ 暗区在画面顶部被边框/深色背景占满时，「暗区上沿」这类口径会退化成常数（每帧都取到同一条 y=0/5 边框），换质心口径。

## 出处回查

```bash
# oembed：比抓页面稳，返回 title / author_name / width / height
curl -sL "https://giphy.com/services/oembed/?url=https%3A%2F%2Fgiphy.com%2Fgifs%2F<ID>"
```

oembed 的 `author_name` 只显示平台名（如 GIPHY）→ 等于原页没有上传频道，写「原页未标注出处」。
页面正文抓取有时只返回关联推荐、不含频道块，两种口径都试一次再说「查不到」。

## 读角标/水印与画面内小字

```bash
# 只裁目标角落 + 4 倍放大，再从放大图读（全图问模型读小字必错）
/Users/Jin/Documents/Hermes/venvs/huashu/bin/python3 zoom_crop.py <图> --box 0,0.7,0.6,1 --scale 4 --out wm.png
```

- 水印/台标/版权字是台账必填项（决定素材能不能进成片），用**裁角+放大**转写，别在整图上问。
- 转写要在台账注明辨识度（如“首个账号名辨识度有限”）；两次识读不一致就整段不采信（见 SKILL.md §3）。

## 台账对账的文本口径

- macOS 文件名是 **NFD**、README 文本多为 **NFC**：直接字符串比较会把同一名字判成不匹配、假报错位。**先 `unicodedata.normalize('NFC')` 归一化**再比。
- 条目正则（README 逐行登记）：`^- \*\*<子目录>/([^*]+)\*\*`。
- 输出四件事：条目数 vs 文件数、有登记无文件、有文件无登记、重名 + 体积 Top5。
- 正反两向都可能有错位（既可能有孤儿登记，也可能有未登记文件），**不要默认某一侧是对的**。
