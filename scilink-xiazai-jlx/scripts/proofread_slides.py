"""
用 PPT 页面文字反校正逐字稿
==========================
思路：同一页上，PPT 上印的字是讲师照讲的内容，比 ASR 听话准得多。
把「该页 OCR 文字」和「该页口述句子」并排交给 LLM，只修被页面文字证实的错字。

用法：
  .venv/bin/python proofread_slides.py <逐字稿目录> [节号]
  例：proofread_slides.py <dir> 02    只处理 02 节；不填则全部

产出：<节>_final.json（segments 为最终版）+ <节>_final.md
"""

import difflib
import glob
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ENV = Path.home() / ".hermes/.env"
env = {}
for line in ENV.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
KEY = env["DEEPSEEK_API_KEY"]
BASE = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")

SYS = """你在校对一堂医学科研课程的字幕转写稿。

给你的材料有三种：
1. 每页 PPT 上印的文字（OCR 结果，基本准确，但可能有零星 OCR 错字）
2. 讲师在这一页的口述转写（语音识别，会有同音字/听错的地方，标点和断句也可能错）
3. 句子编号 i（必须原样返回）

任务与铁律：
1. **只修被页面文字明确证实的错字**：页面文字里出现的某词，在口述里被听成了同音/形近的错字 — 改。
   例：页面写「回溯至1966年」，口述是「回湖至1966年」→ 改；页面写「90%左右为英文文献」，口述是「黄文文献」→ 改。
2. 页面文字**没有涉及**的词，一律保持原样，哪怕你觉得它可能也错了。
3. 不合并、不拆分、不增删句子；条数和顺序与输入完全一致。
4. 不改语气、不润色、不补标点（只处理被证实的错字）。
5. 拿不准就不改。

输出：严格 JSON 数组，不要解释、不要代码块：
[{"i": 0, "text": "校对后的句子"}, ...]
若某句无需修改，也要原样返回。
"""


def llm(messages, max_tokens=8000, timeout=600):
    body = json.dumps({"model": "deepseek-chat", "messages": messages,
                       "max_tokens": max_tokens, "temperature": 0.1}).encode()
    req = urllib.request.Request(
        BASE + "/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    last = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(12)
    raise last


def build_batches(slides, segs, max_chars=5000):
    """按页分批：每批若干页，带该页 OCR + 该页句子"""
    batches, cur, cur_len = [], [], 0
    for sl in slides:
        mine = [(i, s) for i, s in enumerate(segs) if s.get("slide") == sl["idx"]]
        if not mine:
            continue
        block = {
            "page": sl["idx"],
            "ocr": (sl.get("text") or "").strip()[:1500],
            "sents": [{"i": i, "text": s["text"]} for i, s in mine],
        }
        blen = len(block["ocr"]) + sum(len(x["text"]) for x in block["sents"])
        if cur and cur_len + blen > max_chars:
            batches.append(cur)
            cur, cur_len = [], 0
        cur.append(block)
        cur_len += blen
    if cur:
        batches.append(cur)
    return batches


def main():
    D = sys.argv[1]
    only = sys.argv[2] if len(sys.argv) > 2 else ""

    files = sorted(glob.glob(os.path.join(D, "*_slides.json")))
    if only:
        files = [f for f in files if os.path.basename(f).startswith(only)]
    if not files:
        sys.exit("没有找到 slides json")

    for p in files:
        short = os.path.basename(p).replace("_slides.json", "")
        d = json.load(open(p, encoding="utf-8"))
        # 每次都从原始转写稿重置基准，保证可重复、不会越改越偏
        orig_p = os.path.join(D, f"{short}_proofed.json")
        if os.path.exists(orig_p):
            orig = json.load(open(orig_p, encoding="utf-8"))
            if len(orig.get("segments") or []) == len(d.get("segments") or []):
                for s, o in zip(d["segments"], orig["segments"]):
                    s["text"] = o["text"]
        slides, segs = d.get("slides") or [], d.get("segments") or []
        if not slides or not segs:
            continue
        batches = build_batches(slides, segs, 5000)
        print(f"[{short}] {len(slides)} 页 / {len(segs)} 句 → {len(batches)} 批", flush=True)

        new_text = {}
        changed = 0
        for bi, batch in enumerate(batches, 1):
            payload = [{"page": b["page"], "page_text": b["ocr"], "sentences": b["sents"]} for b in batch]
            try:
                raw = llm([
                    {"role": "system", "content": SYS},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ]).strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
                fixed = json.loads(raw)
                n = 0
                for x in fixed:
                    i, t = int(x["i"]), x.get("text", "")
                    if not t:
                        continue
                    # 只差空白/换行字符的「改动」是噪声，丢掉
                    if re.sub(r"\s+", "", t) == re.sub(r"\s+", "", segs[i]["text"]):
                        continue
                    # 防篡改闸门：真错字只占几个字，改动幅度过大说明模型在「用页面文字重写整句」，
                    # 必须回滚（实测出现过把整句换成页面上的无关文字的情况）
                    if difflib.SequenceMatcher(None, segs[i]["text"], t).ratio() < 0.6:
                        print(f"      ⚠️ 回滚疑似改写: {segs[i]['text'][:30]} → {t[:30]}")
                        continue
                    if t != segs[i]["text"]:
                        new_text[i] = t
                        n += 1
                changed += n
                print(f"  [{bi}/{len(batches)}] 改 {n} 句", flush=True)
            except Exception as e:
                print(f"  [{bi}/{len(batches)}] 失败 {type(e).__name__}: {e}", flush=True)
            time.sleep(2)

        for i, t in new_text.items():
            segs[i]["text"] = t
        d["text_final"] = "".join(s["text"] for s in segs)
        d["slide_corrected"] = True
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[{short}] 共修正 {changed} 句 → {p}\n", flush=True)


if __name__ == "__main__":
    main()
