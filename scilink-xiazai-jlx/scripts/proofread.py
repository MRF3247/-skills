"""
FunASR 转写稿 → DeepSeek 术语校对
==================================
只改「听错的字」，不改写、不润色、不合并句子；保留每句原时间戳。

用法：
  .venv/bin/python proofread.py <in.json> <out.json> [term_file]

term_file（可选）：每行一条 `错写法 -> 正确写法` 或单独一个正确术语。
默认内置解螺旋医学课常见术语表。
"""

import json
import os
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

DEFAULT_TERMS = """
解螺旋（不是 解罗旋/解罗玄/解模学/解螺学/解螺旋的）
PubMed（不是 拍卖的/拍外的/泡卖/拍外/power mind/拍wer de/拍，）
MEDLINE（不是 麦拉/麦德拉/麦当兰/mghelline/meet line/met line/梅德拉）
MeSH（不是 mesh 之外的写法；注意"主题词"就是 MeSH 词）
中国知网 / 知网（不是 中国之网/中国智网/中国网网）
CNKI
生信 / 生物信息学（不是 生性/生心）
检索式（不是 检索师/检索室）
摘要（不是 专要）
关键词
主题词
自由词
Web of Science
Embase
Cochrane
泛读（不是 贩读）
精读
影响因子
循证医学
队列研究
Meta 分析
解螺旋学员（不是 解模学学员）
晨曦（讲师名，不是 陈希/晨希）
争渡者（不是 争度者/检读者）
精卫填海（不是 惊畏填海）
怠惰感（不是 怠多感）
高效科研小工具（不是 高校科研小工具）
生信篇（不是 生信片）
冠心病（不是 关心病）
心血管（不是 新学官）
"""

SYS = """你是中文语音转写稿的校对员，文稿来自医学科研课程（文献检索与阅读）。

铁律：
1. **只改识别错的字词**（同音字/近音字错误、专有名词），除此之外一个字都不许动。
2. 严禁改写句子、润色、合并、拆分、增删内容；没听错的句子必须**原样返回**，包括重复字、口误、语病。
3. 每句必须原样返回，条数和顺序完全一致。
4. 拿不准的地方保持原样，不要臆造。
5. **允许的唯一例外**：转写工具的标点常插在词中间（如「期，刊」「数据，库」「拍，外」），
   这类情况请把标点移到词后或删掉，使词恢复完整。只在明显是词被打断时才这样做。

术语对照（左错右对，务必据此纠正）：
{terms}

输出格式：严格返回 JSON 数组，不要任何解释、不要 markdown 代码块：
[{{"i": 0, "text": "校对后的句子"}}, ...]
"""


def llm(messages, max_tokens=8000, timeout=600):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    last = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(12)
    raise last


def main():
    inp, out = sys.argv[1], sys.argv[2]
    terms = DEFAULT_TERMS
    if len(sys.argv) > 3 and os.path.exists(sys.argv[3]):
        terms = Path(sys.argv[3]).read_text(encoding="utf-8")

    data = json.load(open(inp, encoding="utf-8"))
    segs = data.get("segments") or []
    if not segs:
        print("没有 segments，跳过")
        return

    # 分批：每批 ~3000 字（6000 字时 LLM 输出常被 max_tokens 截断，JSON 解析失败整批回退原文）
    batches, cur, cur_len = [], [], 0
    for s in segs:
        cur.append(s)
        cur_len += len(s["text"])
        if cur_len > 3000 or len(cur) >= 150:
            batches.append(cur)
            cur, cur_len = [], 0
    if cur:
        batches.append(cur)

    print(f"{len(segs)} 句 → {len(batches)} 批", flush=True)
    result = []
    for bi, batch in enumerate(batches, 1):
        payload = [{"i": i, "text": s["text"]} for i, s in enumerate(batch)]
        msg = [
            {"role": "system", "content": SYS.format(terms=terms)},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        try:
            raw = llm(msg)
            txt = raw.strip()
            if txt.startswith("```"):
                txt = txt.split("\n", 1)[1].rsplit("```", 1)[0]
            fixed = json.loads(txt)
            by_i = {int(x["i"]): x["text"] for x in fixed}
            for i, s in enumerate(batch):
                result.append({**s, "text": by_i.get(i, s["text"])})
            print(f"  [{bi}/{len(batches)}] ok {len(batch)} 句", flush=True)
        except Exception as e:
            print(f"  [{bi}/{len(batches)}] 失败 {type(e).__name__}: {e} → 保留原文", flush=True)
            result.extend(batch)
        time.sleep(2)

    outdata = {
        **{k: v for k, v in data.items() if k != "segments"},
        "segments": result,
        # 保留转写原文，校对版由 segments 逐句拼接（避免整段重排后标点错位）
        "text_proofed": "".join(s["text"] for s in result),
        "proofread": True,
    }
    json.dump(outdata, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"DONE {out} | {len(result)} 句", flush=True)


if __name__ == "__main__":
    main()
