"""
批量转写：一次加载模型，循环跑整个目录的 wav
============================================
用法：
  .venv/bin/python batch_transcribe.py <wav目录> <输出目录> [hotwords]

每个 wav 输出同名 .json（text + 带时间戳的句子）。
已存在且非空的 json 会跳过，可断点续跑。
"""

import glob
import json
import os
import sys
import time

from funasr import AutoModel

DEFAULT_HOTWORDS = " ".join([
    "PubMed", "知网", "CNKI", "生信", "生物信息学", "解螺旋", "检索式",
    "摘要", "关键词", "主题词", "自由词", "MeSH", "Web of Science",
    "Embase", "Cochrane", "影响因子", "循证医学", "队列研究", "Meta分析",
    "泛读", "精读", "文献", "科研",
])

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else src
hot = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_HOTWORDS
os.makedirs(dst, exist_ok=True)

wavs = sorted(glob.glob(os.path.join(src, "*.wav")))
print(f"共 {len(wavs)} 个音频，输出到 {dst}", flush=True)

t0 = time.time()
model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    device="cpu",
    disable_update=True,
    log_level="ERROR",
)
print(f"模型加载完成 {time.time()-t0:.0f}s", flush=True)

done = skip = fail = 0
for i, wav in enumerate(wavs, 1):
    stem = os.path.splitext(os.path.basename(wav))[0]
    out = os.path.join(dst, f"{stem}.json")
    if os.path.exists(out) and os.path.getsize(out) > 500:
        print(f"[{i}/{len(wavs)}] {stem} 已存在，跳过", flush=True)
        skip += 1
        continue
    t1 = time.time()
    try:
        res = model.generate(input=wav, batch_size_s=300, hotword=hot, sentence_timestamp=True)
        r0 = res[0] if isinstance(res, list) else res
        text = r0.get("text", "")
        sents = r0.get("sentence_info") or []
        segs = [
            {"start": round(s.get("start", 0) / 1000.0, 2),
             "end": round((s.get("end") or 0) / 1000.0, 2),
             "text": s.get("text", "")}
            for s in sents
        ]
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"text": text, "segments": segs, "language": "zh",
                       "model": "paraformer-zh+fsmn-vad+ct-punc",
                       "elapsed_s": round(time.time() - t1, 1)},
                      f, ensure_ascii=False, indent=1)
        print(f"[{i}/{len(wavs)}] {stem} ✓ {time.time()-t1:.0f}s | 段={len(segs)} 字={len(text)}", flush=True)
        done += 1
    except Exception as e:
        print(f"[{i}/{len(wavs)}] {stem} ✗ {type(e).__name__}: {e}", flush=True)
        fail += 1

print(f"\n完成：成功 {done} / 跳过 {skip} / 失败 {fail}，总耗时 {(time.time()-t0)/60:.1f} 分钟", flush=True)
