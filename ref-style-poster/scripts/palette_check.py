"""比对参考图与成图的主色板，输出逐色 ΔRGB，判定画风/配色是否对上。

用法: python palette_check.py ref.png out.png [--colors 8]
"""
import sys
import collections
from PIL import Image


def palette(path, n):
    im = Image.open(path).convert("RGB")
    q = im.quantize(colors=n, method=Image.MEDIANCUT).convert("RGB")
    cnt = collections.Counter(q.getdata())
    total = im.width * im.height
    return [(c, v / total) for c, v in cnt.most_common(n)]


def dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / 3


def main():
    ref_path, out_path = sys.argv[1], sys.argv[2]
    n = 8
    if "--colors" in sys.argv:
        n = int(sys.argv[sys.argv.index("--colors") + 1])
    ref = palette(ref_path, n)
    out = palette(out_path, n)
    print(f"REF  {ref_path}")
    for c, p in ref:
        print(f"  #{c[0]:02X}{c[1]:02X}{c[2]:02X}  {p*100:5.1f}%")
    print(f"OUT  {out_path}")
    for c, p in out:
        print(f"  #{c[0]:02X}{c[1]:02X}{c[2]:02X}  {p*100:5.1f}%")
    print("\n每个参考主色 -> 成图最近色 / ΔRGB:")
    worst = 0
    for c, p in ref[:4]:
        best = min(out, key=lambda oc: dist(c, oc[0]))
        d = dist(c, best[0])
        worst = max(worst, d)
        flag = "OK " if d <= 25 else ("WARN" if d <= 40 else "FAIL")
        print(f"  #{c[0]:02X}{c[1]:02X}{c[2]:02X} ({p*100:4.1f}%) -> "
              f"#{best[0][0]:02X}{best[0][1]:02X}{best[0][2]:02X}  Δ={d:5.1f}  {flag}")
    print(f"\n最差 ΔRGB = {worst:.1f}  (<=25 OK, <=40 WARN, >40 需重生成或单色相校正)")


if __name__ == "__main__":
    main()
