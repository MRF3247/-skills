#!/usr/bin/env python3
"""表情包库查重（2026-08-18 实测）：dHash 感知哈希初筛 → 输出重复簇报告。
用法: python3 emoji_dedup.py [--thresh N]   (默认 BASE=素材/表情包, 阈值 10)
注意: dHash 只做初筛！阈值 ≤10 会把「同系列不同内容」误判为重复
（负鼠三部曲 3 张不同场景被聚成一簇；「未读/已读洋鬼子文献」配套梗被误判）。
初筛后必须逐簇拼对比图让 KIMI 判断「内容是否完全相同」，判「重复」才删。
保留规则: 分辨率优先、文件大小次之（脚本已排序，第一个为应保留）。
PIL 依赖: hermes venv 的 PIL _imaging 可能损坏 →
  uv venv /tmp/dedup_env && uv pip install --python /tmp/dedup_env/bin/python pillow
"""
import os, sys
from PIL import Image

BASE = "/Users/Jin/Documents/素材/表情包"
THRESH = 10
if "--thresh" in sys.argv:
    THRESH = int(sys.argv[sys.argv.index("--thresh") + 1])

def dhash(img):
    img = img.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(img.getdata())
    bits = 0
    for i in range(8):
        row = px[i*9:(i+1)*9]
        for j in range(8):
            bits = (bits << 1) | (1 if row[j] > row[j+1] else 0)
    return bits

def hamming(a, b):
    return bin(a ^ b).count("1")

def main():
    files = []
    for root, dirs, names in os.walk(BASE):
        for n in sorted(names):
            if not n.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            p = os.path.join(root, n)
            try:
                with Image.open(p) as im:
                    w, h = im.size
                d = dhash(Image.open(p))
            except Exception as e:
                print(f"SKIP {p}: {e}")
                continue
            files.append({"path": p, "hash": d, "w": w, "h": h, "size": os.path.getsize(p)})

    clusters = []
    for f in files:
        for c in clusters:
            if any(hamming(f["hash"], m["hash"]) <= THRESH for m in c):
                c.append(f)
                break
        else:
            clusters.append([f])

    dups = [c for c in clusters if len(c) > 1]
    print(f"总文件 {len(files)}，重复簇 {len(dups)} 个，涉及 {sum(len(c) for c in dups)} 张（阈值 {THRESH}）")
    print(">>> 下一步：每簇拼对比图（保留|待删并排）→ KIMI 逐簇判断「内容是否完全相同」→ 判重复才删\n")
    for i, c in enumerate(sorted(dups, key=lambda c: -max(m['size'] for m in c)), 1):
        c_sorted = sorted(c, key=lambda m: (-m["w"]*m["h"], -m["size"]))
        keep = c_sorted[0]
        print(f"=== 簇{i}（候选保留: {os.path.relpath(keep['path'], BASE)} {keep['w']}x{keep['h']} {keep['size']//1024}KB）")
        for m in c_sorted[1:]:
            print(f"    候选删除: {os.path.relpath(m['path'], BASE)} {m['w']}x{m['h']} {m['size']//1024}KB")

if __name__ == "__main__":
    main()
