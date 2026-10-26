#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小红书图文成稿机械自检：字数、标题字数、tag、AI 句式黑名单、缩写首现。

用法：
    python3 xhs_check.py draft.md                     # 只查字数和黑名单
    python3 xhs_check.py draft.md --title "标题文本"   # 加查标题 ≤20 字
    python3 xhs_check.py draft.md --tags-any          # 不强制 5 个 tag
    python3 xhs_check.py draft.md --json              # 机器可读

约定：草稿最后一行以 # 开头的行视为 tag 行，其余为正文。
退出码 0 = PASS（可带 WARN），1 = FAIL（必须回改）。
"""
import sys, json, re, argparse

MAX_TOTAL = 1000      # 小红书正文上限（含标点、含 tag、不含换行）
WARN_TOTAL = 900      # 接近上限提醒
MAX_TITLE = 20
TAG_COUNT = 5
LAST_TAG = "#刀客轻研"

# level: FAIL 必须改 / WARN 建议改 / INFO 人工确认
RULES = [
    # —— 硬造动词：把中性事实改成有情绪的比喻
    (r"撑起|换来(?=[^来])|撬开|追着跑|炸出|焊死|卷到|卷成|翻车|长出|撕开|砸出|摆平", "硬造动词/强行形象化", "FAIL"),
    # —— 结构换分量：三个典型 AI 句式
    (r"真正[^。！？\n]{0,8}的是", "「真正…的是…」句式", "FAIL"),
    (r"比[^。！？\n]{0,14}多一", "「比 X 多一 Y」句式", "FAIL"),
    (r"不只是[^。！？\n]{0,20}(而是|，更是)", "「不只是…而是…」句式", "FAIL"),
    # —— 套话
    (r"值得注意的是|值得留意的是|本质上是|说白了|先看数据|不得不说|细思极恐|耐人寻味|令人深思|令人感慨|堪称|毋庸置疑|某种意义上|某种程度上|这意味着|换句话说|归根结底|一句话说|真相是", "AI 套话", "FAIL"),
    # —— 读者指令 / 劝导腔（新闻稿不用）
    (r"别把[^。！？\n]{0,12}当成|记住[，,]|你应该|你要学会|一定要|不妨", "对读者下指令", "WARN"),
    (r"你", "出现第二人称「你」", "WARN"),
    # —— 弱信号
    (r"其实|反而|显然|也就是说|顺便说", "口水连接词", "WARN"),
    (r"离谱|魔幻|炸裂|封神|逆天|狠狠|破防|泪目", "网络情绪词", "WARN"),
    (r"⚠️|✨|🔥|💡|🚨", "emoji 分类标记", "WARN"),
    (r"^\s*(先|再)?(说|看|聊)[一二三]?[:：]|^\s*[一二三四五]、", "小标题式分节", "WARN"),
]

# 允许直接出现、不必给中文名的通用缩写
ABBR_OK = {"SCI", "AI", "APP", "URL", "DOI", "PDF", "CT", "MRI", "IF", "OA", "API", "ID"}


def split_draft(text):
    lines = [l.rstrip() for l in text.strip().splitlines()]
    nonempty = [l for l in lines if l.strip()]
    if nonempty and nonempty[-1].lstrip().startswith("#"):
        tags = [t for t in re.split(r"\s+", nonempty[-1].strip()) if t]
        body = "\n".join(nonempty[:-1])
        return body, tags
    return "\n".join(nonempty), []


def scan_rules(body):
    hits = []
    for pattern, label, level in RULES:
        for m in re.finditer(pattern, body, flags=re.M):
            s = max(0, m.start() - 15)
            ctx = body[s:m.end() + 15].replace("\n", " ")
            hits.append({"level": level, "rule": label, "hit": m.group(0), "ctx": ctx})
    # 「不是 X，而是 Y」按密度判定：≤1 允许，2 提醒，≥3 判死
    n = len(re.findall(r"不是[^。！？\n]{0,25}[，,]?\s*而是", body))
    if n >= 3:
        hits.append({"level": "FAIL", "rule": "「不是…而是…」≥3 次", "hit": f"{n} 次", "ctx": ""})
    elif n == 2:
        hits.append({"level": "WARN", "rule": "「不是…而是…」2 次", "hit": "2 次", "ctx": ""})
    # 缩写首现是否带中文名
    seen = set()
    for m in re.finditer(r"\b([A-Z][A-Za-z&.\-]{1,14})\b", body):
        tok = m.group(1)
        if not re.search(r"[A-Z]{2,}", tok) or tok in ABBR_OK or tok in seen:
            continue
        seen.add(tok)
        if "（" not in body[max(0, m.start() - 2):m.start()]:
            hits.append({"level": "INFO", "rule": "缩写首现未带中文名",
                         "hit": tok, "ctx": body[max(0, m.start() - 20):m.end() + 10].replace("\n", " ")})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--title", default=None)
    ap.add_argument("--tags-any", action="store_true", help="不强制 5 个 tag")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    text = open(a.draft, encoding="utf-8").read()
    body, tags = split_draft(text)
    body_chars = len(body.replace("\n", ""))   # 空格也算字，平台就是这么数的
    total = len((body + "\n" + " ".join(tags)).replace("\n", ""))

    report = {"body_chars": body_chars, "total_chars": total,
              "tags": tags, "tag_count": len(tags), "title": a.title,
              "checks": [], "hits": scan_rules(body)}

    def add(level, msg):
        report["checks"].append({"level": level, "msg": msg})

    add("PASS", f"正文 {body_chars} 字（不含 tag）") if body_chars <= WARN_TOTAL else \
        add("WARN", f"正文 {body_chars} 字，已超 {WARN_TOTAL}，建议删到 900 以内")
    if total > MAX_TOTAL:
        add("FAIL", f"正文 + tag 共 {total} 字，超平台上限 {MAX_TOTAL}")
    else:
        add("PASS", f"正文 + tag 共 {total} 字 ≤ {MAX_TOTAL}")

    if a.title is not None:
        tl = len(a.title.replace(" ", ""))
        add("PASS", f"标题 {tl} 字") if tl <= MAX_TITLE else \
            add("FAIL", f"标题 {tl} 字，超 {MAX_TITLE} 字上限")

    if not a.tags_any:
        if len(tags) != TAG_COUNT:
            add("FAIL", f"tag 有 {len(tags)} 个，应为 {TAG_COUNT} 个")
        else:
            add("PASS", f"tag {TAG_COUNT} 个")
        if tags and tags[-1] != LAST_TAG:
            add("FAIL", f"最后一个 tag 必须是 {LAST_TAG}，现在是 {tags[-1] if tags else '空'}")
        elif tags:
            add("PASS", f"末位 tag 为 {LAST_TAG}")

    fails = sum(1 for h in report["hits"] if h["level"] == "FAIL")
    warns = sum(1 for h in report["hits"] if h["level"] == "WARN")
    report["verdict"] = "FAIL" if (fails or any(c["level"] == "FAIL" for c in report["checks"])) else "PASS"

    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"== 字数 ==\n正文 {body_chars} 字 / 含 tag {total} 字（上限 {MAX_TOTAL}）")
        print(f"== tag ==\n{len(tags)} 个：{' '.join(tags) if tags else '（缺 tag 行）'}")
        if a.title:
            print(f"== 标题 ==\n{a.title}（{len(a.title.replace(' ', ''))} 字 / 上限 {MAX_TITLE}）")
        print("== 黑名单 ==")
        if not report["hits"]:
            print("无命中")
        for h in report["hits"]:
            print(f"[{h['level']}] {h['rule']}：{h['hit']}  ← …{h['ctx']}…")
        print("== 结论 ==")
        for c in report["checks"]:
            print(f"[{c['level']}] {c['msg']}")
        print(f"→ {report['verdict']}（FAIL {fails} / WARN {warns}）")
    sys.exit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
