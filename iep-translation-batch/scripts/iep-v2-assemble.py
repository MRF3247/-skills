"""IEP 逐段中英对照 v2：parent 侧组装+校验器。
用法：from iep_v2_assemble import assemble
  assemble(src_path, out_path, parent_inserts, sec_files, eol='\r\n', write=True)
  parent_inserts: [(after_line_no, text)]（frontmatter 3 行/译注 callout/正题译/导言段译/目录译块）
  sec_files: 各段 sec-N.json（[{"after": N, "text": "插入行"}]，按段号数值排序传入）
校验电池：原非空行全保留且为子序列、行数=原+插入、无双重CR、无孤立LF、frontmatter translator 行、译行邻接抽查。
内嵌换行的插入文本会自动拆成同 anchor 多条单行条目（保序），不需要预处理。
"""
import json
from collections import defaultdict
from pathlib import Path


def load_secs(sec_files):
    inserts = []
    split_ct = 0
    for sf in sec_files:
        data = json.loads(Path(sf).read_text(encoding="utf-8"))
        for it in data:
            text = str(it["text"])
            if "\n" in text or "\r" in text:
                # 子代理把多行块塞进一个 text：拆成同 anchor 多条单行（保序），防止成品混入孤立 LF
                parts = [p for p in text.replace("\r", "").split("\n") if p.strip()]
                for p_ in parts:
                    inserts.append([int(it["after"]), p_, Path(sf).name])
                split_ct += len(parts)
            else:
                inserts.append([int(it["after"]), text, Path(sf).name])
    if split_ct:
        print(f"[load_secs] 拆分内嵌换行 {split_ct} 行")
    return inserts


def verify(orig_lines, final_lines, n_inserted, eol="\r\n"):
    ok, msgs = True, []
    orig_nonempty = [l for l in orig_lines if l.strip()]

    kept = sum(1 for l in orig_nonempty if l in final_lines)
    msgs.append(f"原非空行 {len(orig_nonempty)}，成品保留 {kept}")
    ok &= kept == len(orig_nonempty)

    cursor, seq = 0, True
    for l in orig_nonempty:
        try:
            cursor = final_lines.index(l, cursor) + 1
        except ValueError:
            seq = False
            break
    msgs.append(f"顺序子序列: {seq}")
    ok &= seq

    expect = len(orig_lines) + n_inserted
    msgs.append(f"行数 final={len(final_lines)} = orig {len(orig_lines)} + 插入 {n_inserted} → {'OK' if len(final_lines)==expect else 'MISMATCH'}")
    ok &= len(final_lines) == expect

    joined = eol.join(final_lines)
    crd = "\r\r" in joined
    msgs.append(f"双重CR: {crd}")
    ok &= not crd

    lonely = joined.replace(eol, "").count("\n")
    msgs.append(f"孤立LF: {lonely}")
    ok &= lonely == 0

    para = sum(1 for l in final_lines if l.startswith("> **译**"))
    head = sum(1 for l in final_lines if l.startswith("**译**"))
    msgs.append(f"段译行(> **译**) {para}｜标题译行(**译**) {head}")

    # frontmatter 校验
    fm_ok = final_lines[0].strip() == "---"
    if fm_ok:
        fm_end = final_lines.index("---", 1)
        fm_ok = any("translator: GLM 5.3 Flash" in l for l in final_lines[:fm_end])
    msgs.append(f"frontmatter translator 行: {fm_ok}")
    ok &= fm_ok

    # 插入邻接抽查：每个插入行的前一行必须是原文行或同一插入块的延续
    orig_set = set(orig_lines)
    bad_adj = 0
    for i, l in enumerate(final_lines):
        if l.startswith(("> **译**", "**译**", "> 注：")) and i:
            prev = final_lines[i-1]
            if prev not in orig_set and not prev.startswith(("> ", "**译**")):
                bad_adj += 1
    msgs.append(f"邻接异常 {bad_adj}")
    ok &= bad_adj == 0
    return ok, msgs, {"para": para, "head": head}


def assemble(src_path, out_path, parent_inserts, sec_files, eol="\r\n", write=True):
    src = Path(src_path)
    orig_lines = src.read_bytes().decode("utf-8").split(eol)

    inserts = [[a, t, "parent"] for a, t in parent_inserts] + load_secs(sec_files)
    inserts.sort(key=lambda x: x[0])  # 稳定排序：同 anchor 保提交序

    by_after = defaultdict(list)
    for a, t, _tag in inserts:
        by_after[a].append(t)

    final, n_ins = [], 0
    for i, l in enumerate(orig_lines):
        final.append(l)
        for t in by_after.get(i + 1, []):
            final.append(t)
            n_ins += 1

    orphan = n_ins != len(inserts)
    ok, msgs, stats = verify(orig_lines, final, n_ins, eol)
    if orphan:
        ok = False
        msgs.append(f"[异常] 有插入未落位（{len(inserts)-n_ins} 条 anchor 超界）")

    if ok and write:
        Path(out_path).write_bytes(eol.join(final).encode("utf-8"))
        msgs.append("已写回")
    return ok, msgs, stats
