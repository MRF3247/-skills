"""
helixlife.cn（解螺旋）课程视频批量下载 —— macOS 版
=====================================================
原理与原版一致：
  Bearer Token → lessons 列表 → play_auth 换 STS → 阿里云 VOD GetPlayInfo
  → m3u8（AES-128）→ decrypt_key 拿 16 字节密钥 → ffmpeg 解密合并

用法：
  # 1) 只看课程目录（不下载）
  python download_course.py --course <UUID或课程URL> --list
  # 2) 下载整门课
  python download_course.py --course <UUID或课程URL>
  # 3) 只下第 3 到第 5 节
  python download_course.py --course <UUID> --start 3 --end 5

Token 三种给法（优先命令行）：
  --token "xxx|yyy"          直接传
  环境变量 HL_TOKEN
  同目录 token.txt 放一行 token（推荐，不进 shell 历史）

依赖已在 .venv 里，运行用：.venv/bin/python download_course.py ...
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import StsTokenCredential
from aliyunsdkvod.request.v20170321 import GetPlayInfoRequest

API = "https://api.helixlife.cn/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "_aes_key.bin")
TMP_M3U8 = os.path.join(HERE, "_tmp.m3u8")
DEFAULT_OUT = os.path.expanduser("~/Documents/视频/解螺旋")


def resolve_token(cli_token):
    if cli_token:
        return cli_token.strip()
    env = os.environ.get("HL_TOKEN", "").strip()
    if env:
        return env
    tf = os.path.join(HERE, "token.txt")
    if os.path.exists(tf):
        with open(tf, encoding="utf-8") as f:
            t = f.read().strip()
        if t:
            return t
    sys.exit("缺少 Token：用 --token 传，或写进 token.txt，或设 HL_TOKEN")


def parse_course(s):
    """支持 UUID 或完整课程 URL"""
    m = re.search(r"/([0-9a-fA-F-]{20,})", s)
    return m.group(1) if m else s.strip()


def api_get(url, token):
    headers = {
        "authorization": f"Bearer {token}",
        "platform": "pc",
        "source": "PC",
        "referer": "https://www.helixlife.cn/",
        "user-agent": "Mozilla/5.0",
    }
    req = urllib.request.Request(url, headers=headers)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def get_play_url(video_id, token):
    """video_id (= lesson.path.path) → 阿里云 m3u8 播放地址"""
    data = json.dumps({"video_id": video_id}, separators=(",", ":"))
    f = base64.b64encode(urllib.parse.quote(data).encode()).decode()
    resp = api_get(f"{API}/public/upload/play_auth?f={f}", token)
    if not resp.get("success"):
        msg = resp.get("message") or ""
        msg = msg.replace("{#title}", "")
        if "无权限" in msg:
            raise RuntimeError("这节你没买/没权限（不是 token 问题）")
        raise RuntimeError(f"play_auth 失败: {msg}（Token 多半过期了，重跑 jlx_login.py）")

    auth = json.loads(base64.b64decode(resp["data"]["PlayAuth"] + "=="))
    cred = StsTokenCredential(
        auth["AccessKeyId"], auth["AccessKeySecret"], auth["SecurityToken"]
    )
    client = AcsClient(region_id=auth["Region"], credential=cred)

    req = GetPlayInfoRequest.GetPlayInfoRequest()
    req.set_VideoId(auth["VideoMeta"]["VideoId"])
    req.set_AuthTimeout(3600)
    response = json.loads(client.do_action_with_exception(req))

    plays = response["PlayInfoList"]["PlayInfo"]
    plays.sort(key=lambda x: {"HD": 0, "SD": 1, "LD": 2}.get(x.get("Definition", "LD"), 9))
    return plays[0]["PlayURL"]


def build_patched_m3u8(m3u8_url, token):
    """下载 m3u8 → key URI 换成本地密钥文件 → TS 补全成绝对地址"""
    content = urllib.request.urlopen(m3u8_url, timeout=20).read().decode()

    key_match = re.search(r'URI="(https://[^"]*decrypt_key[^"]*)"', content)
    if key_match:
        headers = {"authorization": f"Bearer {token}", "user-agent": "Mozilla/5.0"}
        req = urllib.request.Request(key_match.group(1), headers=headers)
        key = urllib.request.urlopen(req, timeout=20).read()
        if len(key) != 16:
            raise RuntimeError(
                f"解密 key 长度 {len(key)} 字节（应 16），Token 可能已过期"
            )
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        content = re.sub(
            r'URI="https://[^"]*decrypt_key[^"]*"', f'URI="{KEY_FILE}"', content
        )

    base = m3u8_url.rsplit("/", 1)[0] + "/"
    content = re.sub(
        r"^(?!#)(\S+\.ts)$",
        lambda m: base + m.group(1),
        content,
        flags=re.MULTILINE,
    )
    with open(TMP_M3U8, "w", encoding="utf-8") as f:
        f.write(content)
    return TMP_M3U8


def download_lesson(num, title, video_id, out_path, token, ffmpeg):
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1024 * 100:
        mb = os.path.getsize(out_path) // 1024 // 1024
        print(f"[{num:02d}] 已存在({mb}MB)，跳过  {title}")
        return True

    print(f"[{num:02d}] 下载中… {title}", flush=True)
    try:
        play_url = get_play_url(video_id, token)
        patched = build_patched_m3u8(play_url, token)
        r = subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                "-protocol_whitelist", "file,crypto,data,https,tcp,tls",
                "-allowed_extensions", "ALL",
                "-i", patched,
                "-c", "copy", "-movflags", "+faststart",
                out_path,
            ],
            capture_output=True,
            timeout=1800,
        )
        if r.returncode == 0 and os.path.exists(out_path):
            mb = os.path.getsize(out_path) // 1024 // 1024
            print(f"       完成 {mb}MB", flush=True)
            return True
        print(f"       ffmpeg 失败: {r.stderr[-300:].decode('utf-8', 'ignore')}")
        return False
    except Exception as e:
        print(f"       错误: {e}")
        return False


def run_course(uuid, title, out_dir, token, ffmpeg, start=0, end=10**6, list_only=False):
    """跑一门课：拉 lessons → 逐节下载"""
    resp = api_get(f"{API}/edu/courses/{uuid}/lessons", token)
    if not resp.get("data"):
        print(f"⚠️ {title}: 没拿到 lessons（{resp.get('message')}）")
        return 0, 0
    lessons = [x for x in resp["data"] if x.get("type") == "video"]
    print(f"【{title}】共 {len(lessons)} 节视频")

    if list_only:
        for x in lessons:
            print(f"  [{x['number']:02d}] {x['title']}")
        return 0, 0

    os.makedirs(out_dir, exist_ok=True)
    print(f"  输出: {out_dir}\n")
    ok = fail = 0
    for gi, x in enumerate(lessons, 1):
        if not (start <= gi <= end):
            continue
        # 用平台原始文件名（自带章节号，节号会重复，不能只用 number）
        raw = (x.get("path") or {}).get("name") or f"{x['number']:02d}_{x['title']}.mp4"
        if not raw.lower().endswith((".mp4", ".m4v", ".mov")):
            raw += ".mp4"
        safe = re.sub(r'[\\/:*?"<>|]', "_", raw)
        out_path = os.path.join(out_dir, f"{gi:02d}_{safe}")
        mins = x.get("length", 0) // 60
        if download_lesson(gi, f"{x['title']} ({mins}分)", x["path"]["path"], out_path, token, ffmpeg):
            ok += 1
        else:
            fail += 1
        time.sleep(0.3)
    return ok, fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", default="", help="单个课程 UUID 或课程页 URL")
    ap.add_argument("--index", default="", help="按 course_index.json 的编号选课，如 1,3,5 或 all")
    ap.add_argument("--token", default="", help="Bearer Token")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出目录")
    ap.add_argument("--list", action="store_true", help="只列节次，不下载")
    ap.add_argument("--start", type=int, default=0, help="起始节号")
    ap.add_argument("--end", type=int, default=10**6, help="结束节号")
    ap.add_argument("--dry", action="store_true", help="只看会下哪些课，不联网")
    args = ap.parse_args()

    if not args.course and not args.index:
        sys.exit("要么 --course <UUID/URL>，要么 --index <编号|all>")

    token = resolve_token(args.token)
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    if not args.list and not os.path.exists(ffmpeg):
        sys.exit("找不到 ffmpeg，先 brew install ffmpeg")

    # 选课清单
    if args.index:
        idx_path = os.path.join(HERE, "course_index.json")
        if not os.path.exists(idx_path):
            sys.exit(f"缺 {idx_path}（先跑 list_courses.py 生成）")
        idx = json.load(open(idx_path, encoding="utf-8"))
        if args.index.strip().lower() == "all":
            picked = idx
        else:
            want = {int(x) for x in re.split(r"[,\s]+", args.index.strip()) if x}
            picked = [c for c in idx if c["no"] in want]
        if not picked:
            sys.exit("编号没匹配上任何课程")
    else:
        picked = [{"no": 0, "title": "", "uuid": parse_course(args.course), "videos": 0}]

    tot_ok = tot_fail = 0
    for i, c in enumerate(picked, 1):
        uuid = c["uuid"]
        title = c.get("title") or uuid
        if args.course:
            out_dir = args.out
        else:
            safe_dir = re.sub(r'[\\/:*?"<>|]', "_", f"{c['no']:02d}_{title}")[:80]
            out_dir = os.path.join(args.out, safe_dir)
        if args.dry:
            print(f"{c['no']:02d}. {title}  ({c.get('videos')}节)")
            continue
        print(f"\n=== [{i}/{len(picked)}] {title} ===")
        ok, fail = run_course(uuid, title, out_dir, token, ffmpeg, args.start, args.end, args.list)
        tot_ok += ok
        tot_fail += fail

    for f in (KEY_FILE, TMP_M3U8):
        if os.path.exists(f):
            os.remove(f)
    if not args.list and not args.dry:
        print(f"\n全部完成：{tot_ok} 成功 / {tot_fail} 失败。重跑可自动续传。")


if __name__ == "__main__":
    main()

