"""
从课程视频里提取 PPT 页并在转写 JSON 里建立对应
================================================
做法：
  1. ffmpeg 场景检测（scene>阈值）切出候选帧 + 时间戳
  2. 相邻帧做感知哈希（aHash）去重，合并 PPT 动画/光标抖动造成的重复页
  3. 每页得到 [start, end) 时间区间
  4. 把逐字稿每句挂到它所在区间的 PPT 页上（segment.slide = 页号）

用法：
  .venv/bin/python extract_slides.py <视频mp4> <逐字稿json> <输出目录> [阈值]

输出：
  <输出目录>/slides/XX_001.jpg          PPT 截图
  <输出目录>/XX_slides.json             页列表 + 逐句挂载
"""

import glob
import json
import os
import subprocess
import sys
import tempfile


def ahash(path, size=8):
    """8x8 均值哈希"""
    from PIL import Image

    img = Image.open(path).convert("L").resize((size, size))
    px = list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())
    avg = sum(px) / len(px)
    bits = 0
    for i, p in enumerate(px):
        if p > avg:
            bits |= 1 << i
    return bits


def dhash(path, size=8):
    """8x8 差分哈希（对版式变化敏感，比 aHash 更能区分「加了标注的同一页」）"""
    from PIL import Image

    img = Image.open(path).convert("L").resize((size + 1, size))
    px = list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())
    bits = 0
    k = 0
    for r in range(size):
        for c in range(size):
            if px[r * (size + 1) + c] < px[r * (size + 1) + c + 1]:
                bits |= 1 << k
            k += 1
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


def same_page(h1, h2):
    """双哈希判同页：aHash 极近（整体一致）或 dHash 极近（渐变条纹一致）"""
    return hamming(h1[0], h2[0]) <= 8 or hamming(h1[1], h2[1]) <= 6


def main():
    video = sys.argv[1]
    trans_json = sys.argv[2]
    out_dir = sys.argv[3]
    thresh = float(sys.argv[4]) if len(sys.argv) > 4 else 0.08
    stem = os.path.splitext(os.path.basename(video))[0]
    short = stem.split("_")[0]
    slide_dir = os.path.join(out_dir, "slides")
    os.makedirs(slide_dir, exist_ok=True)
    # 清掉上一次跑的旧图，否则页数变少时会残留孤儿文件（拼图/引用都会错）
    for old in glob.glob(os.path.join(slide_dir, f"{short}_*.jpg")):
        os.remove(old)

    tmp = tempfile.mkdtemp()
    print(f"[{stem}] 场景检测中（阈值 {thresh}）…", flush=True)
    cmd = [
        "ffmpeg", "-y", "-i", video,
        "-vf", f"select='gt(scene,{thresh})',showinfo",
        "-vsync", "vfr", "-q:v", "2",
        os.path.join(tmp, "f_%04d.jpg"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    times = [
        float(l.split("pts_time:")[1].split()[0])
        for l in proc.stderr.splitlines() if "pts_time:" in l
    ]
    frames = sorted(glob.glob(os.path.join(tmp, "f_*.jpg")))

    # 首帧（t=0）单独特写：开场往往静止不动，不触发场景切换
    first = os.path.join(tmp, "f_0000.jpg")
    subprocess.run(["ffmpeg", "-y", "-ss", "0.5", "-i", video, "-frames:v", "1",
                    "-q:v", "2", first], capture_output=True)
    if os.path.exists(first):
        frames = [first] + frames
        times = [0.0] + times
    print(f"[{stem}] 候选帧 {len(frames)} 张", flush=True)
    if not frames:
        print("没有检测到画面切换")
        return

    # 去重两道闸：
    #   ① 时间上紧挨着（<1.5s）的多半是同一次切换的动画/淡入过程
    #   ② 哈希几乎一样（汉明距离 <= 6）也是同一页
    def hashes(p):
        return (ahash(p), dhash(p))

    kept = [(times[0], frames[0], hashes(frames[0]))]
    for i, f in enumerate(frames[1:], start=1):
        t = times[i] if i < len(times) else times[-1]
        h = hashes(f)
        if t - kept[-1][0] < 1.5:
            continue
        # 和最近 2 页比：动画/抖动会连出 2-3 帧相似图，但讲师真翻回旧页要保留
        if any(same_page(h, k[2]) for k in kept[-2:]):
            continue
        kept.append((t, f, h))

    # 计算每页时间区间（注意：本机 ~/.local/bin/ffprobe 其实是 ffmpeg 的软链，
    # 用 ffprobe 参数会拿到空值，所以直接让 ffmpeg 打印 Duration 再解析）
    dur = 0.0
    info = subprocess.run(["ffmpeg", "-i", video], capture_output=True, text=True).stderr
    for line in info.splitlines():
        if "Duration:" in line:
            try:
                hms = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = hms.split(":")
                dur = int(h) * 3600 + int(m) * 60 + float(s)
            except Exception:
                pass
            break
    if not dur:
        dur = json.load(open(trans_json, encoding="utf-8")).get("segments", [{}])[-1].get("end", 0)
    slides = []
    for i, (t, f, _) in enumerate(kept):
        end = kept[i + 1][0] if i + 1 < len(kept) else dur
        name = f"{short}_{i+1:03d}.jpg"
        subprocess.run(["cp", f, os.path.join(slide_dir, name)], check=True)
        slides.append({
            "idx": i + 1,
            "start": round(t, 2),
            "end": round(end, 2),
            "img": f"slides/{name}",
        })
    print(f"[{stem}] 去重后 {len(slides)} 页", flush=True)

    # 逐句挂 PPT 页
    data = json.load(open(trans_json, encoding="utf-8"))
    for s in data.get("segments", []):
        mid = (s.get("start", 0) + s.get("end", 0)) / 2
        s["slide"] = next((sl["idx"] for sl in slides if sl["start"] <= mid < sl["end"]), len(slides))

    data["slides"] = slides
    data["video_file"] = os.path.basename(video)
    out_json = os.path.join(out_dir, f"{short}_slides.json")
    json.dump(data, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{stem}] → {out_json}", flush=True)

    # 清理临时帧
    for f in frames:
        os.remove(f)
    os.rmdir(tmp)


if __name__ == "__main__":
    main()
