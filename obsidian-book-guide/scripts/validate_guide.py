#!/usr/bin/env python3
"""导读成品自动验证脚本。

用法:
  python3 validate_guide.py "/Users/Jin/Documents/Obsidian Vault/读书/《书名》" [--source 源.md] [--expect-hash SHA256]

退出码: 0=全部通过(可有 WARN), 1=存在 FAIL。
只用于按本 skill 规范新产出的书; 库内历史旧格式书目不适用。
"""
import argparse, hashlib, os, re, sys
from datetime import date

ZH_NUMS = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]

fails, warns, passes = [], [], []

def fail(msg): fails.append(msg)
def warn(msg): warns.append(msg)
def ok(msg): passes.append(msg)

def parse_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    fm, cur = {}, None
    for ln in text[3:end].splitlines():
        if re.match(r"^\s*- ", ln):
            if cur:
                fm.setdefault(cur, [])
                if isinstance(fm[cur], list):
                    fm[cur].append(re.sub(r"^\s*- ", "", ln).strip())
        else:
            m = re.match(r"^([A-Za-z_]+):\s*(.*)$", ln)
            if m:
                cur = m.group(1)
                v = m.group(2).strip()
                fm[cur] = v if v else []
    return fm, text[end + 4:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book_dir")
    ap.add_argument("--source", help="源文件路径, 用于覆盖校验与哈希")
    ap.add_argument("--expect-hash", help="开工时记录的源文件 SHA-256")
    ap.add_argument("--no-overview", action="store_true", help="跳过知识全览检查(例外情况)")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()
    bd = args.book_dir
    if not os.path.isdir(bd):
        print(f"[FAIL] 目录不存在: {bd}"); sys.exit(1)
    base = os.path.basename(bd.rstrip("/"))
    m = re.match(r"^《(.+)》$", base)
    if not m:
        print(f"[FAIL] 目录名不符合《书名》格式: {bd}"); sys.exit(1)
    guide_path = os.path.join(bd, f"导读{base}.md")
    ov_path = os.path.join(bd, f"{base}知识全览.md")
    orig_dir = os.path.join(bd, "原文")

    # ---- 目录结构 ----
    expect = sorted({os.path.basename(guide_path), os.path.basename(ov_path), "原文"})
    for e in sorted(os.listdir(bd)):
        if e in expect:
            continue
        if e.startswith(".") or re.search(r"tmp|temp|log|pycache", e, re.I):
            fail(f"根层残留临时文件: {e}")
        else:
            warn(f"根层多出条目(规范只允许导读/知识全览/原文): {e}")
    for e in expect:
        if os.path.exists(os.path.join(bd, e)):
            continue
        if e == os.path.basename(ov_path) and args.no_overview:
            warn("按参数跳过知识全览")
        else:
            fail(f"缺少成品条目: {e}")
    if not os.path.exists(guide_path):
        print("\n".join("[FAIL] " + s for s in fails) or "[FAIL] 无导读文件")
        sys.exit(1)
    text = open(guide_path, encoding="utf-8").read()

    # ---- 原文层 ----
    bodies = {}
    if os.path.isdir(orig_dir):
        nums, bad_names = [], []
        for fn in sorted(os.listdir(orig_dir)):
            mm = re.match(r"^原文 (\d{2}) (.+)\.md$", fn)
            if not mm:
                bad_names.append(fn); continue
            nums.append(int(mm.group(1)))
            raw = open(os.path.join(orig_dir, fn), encoding="utf-8").read()
            if raw.startswith("---"):
                fail(f"原文文件含 YAML(应只有包装H1): {fn}")
            lines = raw.split("\n")
            if not lines or not lines[0].startswith("# "):
                fail(f"原文文件缺少包装 H1: {fn}")
                bodies[fn] = []
            else:
                bodies[fn] = lines[1:]
        if bad_names:
            fail(f"原文文件命名不符合 '原文 NN 章节名.md': {bad_names}")
        if nums and nums != list(range(len(nums))):
            fail(f"原文编号不连续: {nums}")
        elif nums:
            ok(f"原文 {len(nums)} 个文件, 编号 00-{nums[-1]:02d} 连续")

    # ---- 源文件覆盖与哈希 ----
    if args.source:
        if not os.path.exists(args.source):
            fail(f"--source 不存在: {args.source}")
        else:
            sha = hashlib.sha256(open(args.source, "rb").read()).hexdigest()
            if args.expect_hash and sha != args.expect_hash:
                fail(f"源文件哈希变化! 现 {sha[:12]} 不等于记录 {args.expect_hash[:12]}")
            else:
                ok(f"源文件 SHA-256 = {sha[:16]}")
            src_lines = open(args.source, encoding="utf-8").read().split("\n")
            if os.path.isdir(orig_dir):
                i, okcov = 0, True
                covered = [False] * len(src_lines)
                for fn in sorted(bodies):
                    bl = bodies[fn][:]
                    while bl and bl[0].strip() == "":
                        bl.pop(0)
                    while bl and bl[-1].strip() == "":
                        bl.pop()
                    if not bl:
                        continue
                    j = i
                    while j < len(src_lines) and src_lines[j].strip() == "":
                        j += 1
                    if j >= len(src_lines) or src_lines[j:j + len(bl)] != bl:
                        fail(f"原文覆盖断点: {fn} 在源行 {j} 附近与源不匹配")
                        okcov = False
                        break
                    for k in range(j, j + len(bl)):
                        covered[k] = True
                    i = j + len(bl)
                missed = [k for k, ln in enumerate(src_lines) if not covered[k] and ln.strip()]
                if okcov and missed:
                    fail(f"源文件有 {len(missed)} 个非空行未被覆盖, 首个在行 {missed[0]}")
                elif okcov:
                    ok("原文层覆盖校验通过: 所有非空源行恰好落入一个原文文件, 顺序一致")

    # ---- frontmatter ----
    fm, body = parse_fm(text)
    if fm is None:
        fail("导读缺少 YAML frontmatter")
    else:
        if fm.get("type") != "layered-reading-article":
            fail(f"type 应为 layered-reading-article, 实为 {fm.get('type')!r}")
        for k in ("book", "author", "created"):
            if not fm.get(k):
                fail(f"frontmatter 缺 {k}")
        if fm.get("created") != args.today:
            warn(f"created={fm.get('created')} 不等于今天 {args.today}")
        tags = fm.get("tags", [])
        if isinstance(tags, list) and any(str(t).startswith("#") for t in tags):
            warn("tags 不应带 # 前缀")
        ok(f"frontmatter: book={fm.get('book')!r}, created={fm.get('created')}")

    total = len(text)
    if total < 20000:
        fail(f"总字符 {total} < 20000")
    else:
        ok(f"总字符 {total:,} ≥ 20000")

    # ---- 知识全览链接 ----
    link = re.search(r"^> 全书知识点速查：\[.+?\]\(<(.+?)>\)", text, re.M)
    if not link:
        fail("导读缺少 '> 全书知识点速查：' 知识全览链接行")
    elif not os.path.exists(os.path.join(bd, link.group(1))):
        fail(f"知识全览链接目标不存在: {link.group(1)}")
    else:
        ok("导读到知识全览链接有效")

    # ---- 问题链 ----
    mq = re.search(r"^## 本书的问题链\s*$", text, re.M)
    mf = re.search(r"^## 正式导读\s*$", text, re.M)
    if not mq:
        fail("缺少 '## 本书的问题链'")
    if not mf:
        fail("缺少 '## 正式导读'")
    if mq and mf:
        if mq.start() > mf.start():
            fail("问题链应位于正式导读之前")
        qseg = text[mq.end():mf.start()]
        found = re.findall(r"^### 问题([一二三四五六七八九十])：", qseg, re.M)
        if found != ZH_NUMS:
            fail(f"问题链应为中文编号问题一~问题九且顺序一致, 实为 {found}")
        else:
            ok("问题链: 9 问, 中文编号, 顺序正确")
        qparts = re.split(r"^### .+$", qseg, flags=re.M)[1:]
        for idx, part in enumerate(qparts):
            lm = re.search(r"^读原文：\[(.+?)\]\(<(.+?)>\)", part, re.M)
            if not lm:
                fail(f"第{idx + 1}问缺 '读原文:' 尖括号链接")
                continue
            n_links = len(re.findall(r"读原文：", part))
            if n_links != 1:
                fail(f"第{idx + 1}问读原文链接数 {n_links} != 1")
            if not os.path.exists(os.path.join(bd, lm.group(2))):
                fail(f"第{idx + 1}问链接目标不存在: {lm.group(2)}")
            stem = lm.group(1)
            if stem != os.path.splitext(os.path.basename(lm.group(2)))[0]:
                warn(f"第{idx + 1}问链接文字与文件名不一致: {stem!r}")
            ans = part[:lm.start()].strip()
            al = len(ans)
            if al < 200:
                fail(f"第{idx + 1}问回答 {al} 字 < 200")
            elif al > 460:
                fail(f"第{idx + 1}问回答 {al} 字 > 460")
            elif al > 400:
                warn(f"第{idx + 1}问回答 {al} 字, 超出目标区间 200-400")
            if re.search(r"^\s*(?:[-*+]|\d+[.、)])\s", ans, re.M):
                warn(f"第{idx + 1}问回答含列表行, 应为连续散文")
        ok("问题链回答字数与链接检查完成")

    # ---- 正式导读 ----
    if mf:
        formal = text[mf.start():]
        flen = len(formal)
        if flen < 16000:
            fail(f"正式导读 {flen:,} 字符 < 16000")
        else:
            ok(f"正式导读 {flen:,} 字符 ≥ 16000")
        if re.search(r"^### ", formal, re.M):
            fail("正式导读含 ### 子标题")
        list_lines = [ln for ln in formal.splitlines() if re.match(r"^\s*(?:[-*+]|\d+[.)])\s", ln)]
        if list_lines:
            fail(f"正式导读含 {len(list_lines)} 个列表行, 首个: {list_lines[0][:40]!r}")
        if not re.search(r"^# 导读：.+《.+?》", formal, re.M):
            warn("正式导读 H1 不符合 '# 导读：副标题——读作者《书名》' 格式")
        parts = re.split(r"^(## .+)$", formal, flags=re.M)
        mains, sups, unknown = [], [], []
        for i in range(1, len(parts), 2):
            title = parts[i][3:].strip()
            b = parts[i + 1]
            b = b.split("\n", 1)[1] if "\n" in b else ""
            blen = len(b.strip())
            if re.match(r"^\d+\.\s", title):
                mains.append((title, blen))
            elif re.match(r"^\d+\.\d+\s", title):
                sups.append((title, blen))
            elif title != "正式导读":
                unknown.append(title)
        for t, l in mains:
            if l < 300:
                fail(f"主节[{t[:24]}] {l} 字 < 300")
            elif l > 650:
                fail(f"主节[{t[:24]}] {l} 字 > 650")
            elif l > 600:
                warn(f"主节[{t[:24]}] {l} 字, 超出目标区间 300-600")
        for t, l in sups:
            if l < 100:
                fail(f"补充节[{t[:24]}] {l} 字 < 100")
            elif l > 500:
                fail(f"补充节[{t[:24]}] {l} 字 > 500")
            elif l > 400:
                warn(f"补充节[{t[:24]}] {l} 字, 超出目标区间 100-400")
        if unknown:
            warn(f"正式导读含非编号 H2: {unknown}")
        if mains:
            if "思想座标" not in mains[-1][0]:
                fail(f"最后一个主节不是思想座标: {mains[-1][0][:30]}")
            else:
                ok(f"主节 {len(mains)} 个, 补充节 {len(sups)} 个, 以思想座标收尾")
        if "---" not in formal:
            warn("正式导读未见 '---' 分隔线")

    # ---- 知识全览 ----
    if os.path.exists(ov_path):
        ov = open(ov_path, encoding="utf-8").read()
        ovfm, _ = parse_fm(ov)
        if ovfm is None or ovfm.get("type") != "knowledge-overview":
            t = ovfm.get("type") if ovfm else None
            fail(f"知识全览 type 应为 knowledge-overview, 实为 {t!r}")
        for h in ("全书结构地图", "概念索引"):
            if f"## {h}" not in ov:
                fail(f"知识全览缺少 '## {h}'")
        back = re.search(r"^> 深入阅读：\[.+?\]\(<(.+?)>\)", ov, re.M)
        if not back:
            fail("知识全览缺少 '> 深入阅读：' 回链")
        elif not os.path.exists(os.path.join(bd, back.group(1))):
            fail(f"知识全览回链目标不存在: {back.group(1)}")
        else:
            ok("知识全览回链有效")
        # 结构地图表中每个原文文件一行
        mapseg = re.search(r"^## 全书结构地图.*?(?=^## )", ov, re.M | re.S)
        if mapseg and os.path.isdir(orig_dir):
            fnames = [fn for fn in sorted(os.listdir(orig_dir)) if fn.endswith(".md")]
            missing_rows = [fn for fn in fnames if fn[:-3] not in mapseg.group(0)]
            if missing_rows:
                warn(f"全书结构地图缺 {len(missing_rows)} 个原文文件的行: {missing_rows[:3]}")
            else:
                ok("全书结构地图覆盖全部原文文件")
    elif not args.no_overview:
        fail("缺少知识全览文件")

    # ---- 汇总 ----
    print()
    for s in passes:
        print(f"[PASS] {s}")
    for s in warns:
        print(f"[WARN] {s}")
    for s in fails:
        print(f"[FAIL] {s}")
    print(f"\n===== 结果: {len(passes)} PASS / {len(warns)} WARN / {len(fails)} FAIL =====")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
