# 转写 / 校对 / 抽帧 / OCR

## 抽音频

```bash
ffmpeg -i 01.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le 01.wav
```

16kHz 单声道，FunASR 的标准输入。一小时视频约 110MB wav。

## FunASR 转写

`batch_transcribe.py` 输出 `trans/NN.json`，时间戳字段是 **`segments`**（不是 `sentences`）：

```json
{
  "text": "全文",
  "segments": [{"start": 0.0, "end": 3.2, "text": "..."}],
  "language": "zh",
  "model": "paraformer-zh+fsmn-vad+ct-punc",
  "elapsed_s": 483.1
}
```

数句数、挂抽帧时间戳，都读 `segments`。去查 `sentences` 会拿到 0，别据此判定转写失败。

速度：8 小时音频约 87 分钟（Apple Silicon，CPU）。量级参考：4.6 小时音频 → 6.7 万字 / 941 段。

**热词必须按课程领域重写。** 第三个参数是热词串，内置那份是给文献检索课调的（PubMed/MeSH/检索式…），换领域不换热词，专有名词会错一片：

```bash
.venv/bin/python batch_transcribe.py <wav目录> <输出目录> \
  "临床研究 证据金字塔 随机对照试验 队列研究 病例对照研究 横断面研究 混杂因素 选择偏倚 统计推断 置信区间 效应量 分类结局 连续结局"
```

## DeepSeek 校对（关键参数）

**每批最多 3000 字 / 150 句。**

6000 字会撞 `max_tokens`，返回被截断的 JSON → `JSONDecodeError: Unterminated string` → 整批静默回退原文，看起来「校对成功」其实没校。

```python
BATCH_CHARS = 3000
BATCH_SENTS = 150
```

常见修正：

| ASR 错字 | 正确 |
|---|---|
| 解罗旋 / 解解蟔旋 / 解罗学 | 解螺旋 |
| 深性研究 | 生信研究 |
| 挑圈联靠 | 挑圈连靠（或按品牌规则处理）|
| 监讨学术 / 线套学术 | 仙桃学术 |

**每门课配一份自己的术语表**，作为第三个参数传入：

```bash
.venv/bin/python proofread.py in.json out.json /tmp/terms_<课程>.txt
```

文件格式一行一条，`正确写法（不是 错法1/错法2）`：

```
随机对照试验（不是 随机对照实验/随即对照试验）
混杂因素（不是 混扰因素/混杂因子）
Logistic回归（不是 逻辑回归的/Logistic回规）
```

先在未校对的 `segments` 里搜一遍可疑词，再写表；凭空列术语命中率低。

## 抽帧

**必须先有逐字稿。** 调用式是 `extract_slides.py <视频mp4> <逐字稿json> <输出目录> [阈值]`——第二个参数就是转写 json，脚本按每页的时间区间把句子挂到页上。所以硬顺序是 转写 → 抽帧 → OCR，不能先抽帧再补稿。

参数：场景检测阈值 `0.08`，首帧 `t=0.5s`，aHash + dHash 双哈希去重。

输出 `slides/NN_slides.json` + `slides/NN_001.jpg...`

### 演示类课程的去重陷阱

纯 PPT 课去重效果很好（220 页→220 页无重复）。但**演示实操课**（录屏浏览器 / WPS 操作）相邻帧差异极大，955 页按 OCR 文本相似度只删得掉 4 页。

结论：演示类不强去重，保留全部帧作上下文参照，**但不用于教材配图**（会暴露课程界面）。

## OCR

macOS Vision（`ocr_vision.swift` 编译后调用），速度约 1.5 秒/页。

```bash
cd <课程>/slides
<funasr>/.venv/bin/python ../ocr_slides.py
```

**必须在 slides/ 目录内执行**，否则 json 路径对不上，输出 0 页。

按坐标剔除噪声：

```python
if y + h > 0.94:  # 页脚（版权信息、课程 logo）
    continue
if y < 0.035:    # 顶栏
    continue
```

这条过滤很重要：页脚常有「上海尤里卡信息科技有限公司」「解螺旋」logo，**OCR 文字会在后续步骤被误当成正文素材**。

输出写回 `NN_slides.json` 的 `text`（整页合并）与 `lines`（按行）。

## 页面文字反校逐字稿

`proofread_slides.py`：把 PPT 页面 OCR 文字当权威，反校逐字稿里的同音错字。

三道闸门防误改：

1. 候选词与原文长度相近（±1）
2. 在页面文字里出现的上下文 ≥ 3 字重合
3. 关键词白名单（专业术语不轻易改）

第一本书 220 页收敛到 61 处修改。

## 知识点提取

`extract_book_points.py`：用 DeepSeek 从每章提炼知识点，输出 `points.json`。

**注意**：知识点只用于内部目录规划，**不要写进成品目录**——用户明确嫌罗列太繁琐。
