# 父代理核验：对比备份与成品，打印每篇硬指标与 [OK]/[异常] 判定。
# 核心是「子序列匹配」（cursor 前进）——不能用 new.index(l)+count==1 判断，
# 原文里 --- 等重复行会误报顺序异常。
# 检查项：原文零改动（保留数+子序列）｜translator 在 frontmatter 结束 --- 之前｜
# 译注署名在｜段译块>0｜无双重\r｜无错误前缀（> 译： 漏粗体）。

from pathlib import Path

VAULT = Path("/Users/Jin/Documents/Obsidian Vault/哲学百科/IEP词条/原文存档")
BAK = Path("/Users/Jin/.hermes/cache/scratch/iep-backups")

def is_subsequence(orig, new):
    cursor = 0
    for l in orig:
        try:
            i = new.index(l, cursor)
        except ValueError:
            return False
        cursor = i + 1
    return True

for bak in sorted(BAK.glob("*.md")):
    done = VAULT / bak.name
    if not done.exists():
        print(f"[缺失] {bak.name}"); continue
    raw = done.read_bytes().decode("utf-8")
    old = bak.read_text(encoding="utf-8").splitlines()
    new = raw.splitlines()
    orig = [l for l in old if l.strip()]
    kept = sum(1 for l in orig if l in new)
    seq = is_subsequence(orig, new)
    lines = raw.splitlines()
    fm_end = lines.index("---", 1) if len(lines) > 1 and lines[0].strip() == "---" else -1
    fm_ok = fm_end > 0 and any("translator: GLM 5.3 Flash" in l for l in lines[:fm_end])
    note = "全部中文译文由 GLM 5.3 Flash 翻译" in raw
    para = sum(1 for l in new if l.startswith("> **译**"))
    head = sum(1 for l in new if l.startswith("**译**"))
    cr_double = "\\r\\r" in repr(raw)  # 双重回车：换行符切分/join 不一致所致
    bad_prefix = sum(1 for l in new if l.startswith("> 译："))  # 译块前缀漏粗体
    ok = kept == len(orig) and seq and fm_ok and note and para > 0 and not cr_double and bad_prefix == 0
    print(f"{'[OK]' if ok else '[异常]'} {bak.name}｜原非空 {len(orig)}｜保留 {kept}｜段译 {para}｜标题译 {head}"
          f"｜顺序 {seq}｜FM结构 {fm_ok}｜署名 {note}｜双\\r {cr_double}｜错前缀 {bad_prefix}")
