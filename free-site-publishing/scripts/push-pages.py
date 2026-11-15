#!/usr/bin/env python3
"""把快照目录分批 commit + push 到远端分支，单批失败自动重试。

为什么分批：这台机器到 GitHub 的链路对「一次推上百 MB」不稳定，会报
`send-pack: unexpected disconnect while reading sideband packet`；小批次（~20MB）
几乎不会失败，而且单批失败只重试那一批，整次同步不会全废。

用法:
  python3 push-pages.py --dir .publish/pages --remote git@github.com:USER/REPO.git \
      --branch gh-pages --message "snapshot 2026-10-10 15:40 · 2907 页"

行为:
  - 目录里没有 .git 就 init；远端地址不对就 set-url
  - 文件按体积切批（默认 ~20MB/批、最多 400 个/批），资源先推、HTML 页最后推
  - 每批：git add -A -- <批内文件> → commit → push -f（失败按 15/30/45… 秒退避重试）
  - 跑完打印批次统计；只要有一批彻底失败就以 1 退出（下次定时任务会再试）
"""
from __future__ import annotations
import argparse, os, subprocess, sys, time

def git(args, cwd, check=True):
    p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}\n{p.stdout}\n{p.stderr}")
    return p

def collect(root: str):
    """返回 [(相对路径, 字节数)]，资源在前、HTML 在后（最后一批推完站点就是完整一致的）。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for f in filenames:
            p = os.path.join(dirpath, f)
            try:
                out.append((os.path.relpath(p, root), os.path.getsize(p)))
            except OSError:
                pass
    out.sort(key=lambda t: (t[0].endswith(".html"), t[0]))
    return out

def batches(files, max_bytes, max_count):
    cur, size = [], 0
    for rel, n in files:
        if cur and (size + n > max_bytes or len(cur) >= max_count):
            yield cur
            cur, size = [], 0
        cur.append(rel); size += n
    if cur:
        yield cur

def push_with_retry(cwd, branch, retries, log):
    for attempt in range(1, retries + 1):
        p = git(["push", "-q", "-f", "origin", branch], cwd, check=False)
        if p.returncode == 0:
            return True
        tail = (p.stderr or p.stdout).strip().splitlines()[-1:] or [""]
        log(f"    第 {attempt}/{retries} 次推送失败：{tail[0][:150]}")
        if attempt < retries:
            time.sleep(15 * attempt)
    return False

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--remote", required=True)
    ap.add_argument("--branch", default="gh-pages")
    ap.add_argument("--message", default="snapshot")
    ap.add_argument("--max-batch-mb", type=float, default=20.0)
    ap.add_argument("--max-batch-files", type=int, default=400)
    ap.add_argument("--retries", type=int, default=5)
    a = ap.parse_args()

    root = os.path.abspath(a.dir)
    if not os.path.isdir(root):
        print(f"✗ 目录不存在：{root}"); return 1
    def log(m): print(m, flush=True)

    if not os.path.isdir(os.path.join(root, ".git")):
        git(["init", "-q"], root)
    git(["config", "user.name", "site-snapshot"], root)
    git(["config", "user.email", "snapshot@local"], root)
    if git(["remote", "get-url", "origin"], root, check=False).returncode != 0:
        git(["remote", "add", "origin", a.remote], root)
    else:
        git(["remote", "set-url", "origin", a.remote], root)
    git(["checkout", "-q", "-B", a.branch], root, check=False)

    files = collect(root)
    if not files:
        print("✗ 目录是空的"); return 1
    total_mb = sum(n for _, n in files) / 1048576
    groups = list(batches(files, int(a.max_batch_mb * 1048576), a.max_batch_files))
    log(f"  {len(files)} 个文件 / {total_mb:.0f}MB → 分 {len(groups)} 批推送（每批 ≤{a.max_batch_mb:.0f}MB）")

    t0 = time.time()
    pushed = failed = 0
    for i, grp in enumerate(groups, 1):
        git(["add", "-A", "--"] + grp, root)
        if git(["diff", "--cached", "--quiet"], root, check=False).returncode == 0:
            continue                                  # 这批没有任何变化
        mb = sum(n for rel, n in files if rel in set(grp)) / 1048576
        git(["commit", "-q", "-m", f"{a.message} · 批次 {i}/{len(groups)}"], root)
        if push_with_retry(root, a.branch, a.retries, log):
            pushed += 1
            log(f"  批次 {i}/{len(groups)} 推送成功（{mb:.0f}MB，累计 {time.time()-t0:.0f}s）")
        else:
            failed += 1
            log(f"  ✗ 批次 {i}/{len(groups)} 重试 {a.retries} 次仍失败")

    # 收尾：把批外残留（含删除）也提交推掉
    git(["add", "-A"], root)
    if git(["diff", "--cached", "--quiet"], root, check=False).returncode != 0:
        git(["commit", "-q", "-m", f"{a.message} · 收尾"], root)
        if push_with_retry(root, a.branch, a.retries, log):
            pushed += 1
            log("  收尾批次推送成功")
        else:
            failed += 1
    log(f"  推送批次：成功 {pushed} / 失败 {failed}（总用时 {time.time()-t0:.0f}s）")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
