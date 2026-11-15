#!/usr/bin/env python3
"""Verify a mirrored tree against its HTTP source.

Usage: python3 verify.py BASE_URL LOCAL_DIR [SAMPLE_N]
Re-crawls the server's listings for the full expected file set, diffs it
against the local tree (missing AND extra), then HEAD-samples file sizes
(default 150, seeded so reruns pick the same files).
Prints RESULT: OK or PROBLEMS FOUND; exits non-zero on problems.
"""
import concurrent.futures as cf
import os
import random
import re
import sys
import urllib.parse
import urllib.request

LI_RE = re.compile(r'<a href="(.+?)">')


def crawl_expected(base):
    expected = []  # (relpath, url)
    dirs, seen = [base], set()
    while dirs:
        d = dirs.pop()
        if d in seen:
            continue
        seen.add(d)
        with urllib.request.urlopen(d, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
        for href in LI_RE.findall(text):
            full = urllib.parse.urljoin(d, href)
            if full.rstrip("/") == base.rstrip("/"):
                continue
            if full.endswith("/"):
                dirs.append(full)
            else:
                rel = urllib.parse.unquote(urllib.parse.urlparse(full).path).lstrip("/")
                expected.append((rel, full))
    return expected, seen


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    base = sys.argv[1]
    if not base.endswith("/"):
        base += "/"
    out = os.path.expanduser(sys.argv[2])
    n_sample = int(sys.argv[3]) if len(sys.argv) > 3 else 150

    expected, seen_dirs = crawl_expected(base)
    print(f"server reports {len(expected)} files in {len(seen_dirs)} dirs")

    local = set()
    for root, _, files in os.walk(out):
        for f in files:
            local.add(os.path.relpath(os.path.join(root, f), out))
    print(f"local has {len(local)} files")

    expected_set = {rel for rel, _ in expected}
    missing = [rel for rel in expected_set if rel not in local]
    extra = sorted(local - expected_set)
    print(f"missing on local: {len(missing)}")
    for m in missing[:20]:
        print("  MISSING:", m)
    print(f"extra on local (not on server): {len(extra)}")
    for e in extra[:10]:
        print("  EXTRA:", e)

    sample = random.Random(42).sample(expected, min(n_sample, len(expected)))

    def check(item):
        rel, url = item
        lp = os.path.join(out, rel)
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=20) as r:
                remote = int(r.headers["Content-Length"])
            return rel, remote == os.path.getsize(lp), remote, os.path.getsize(lp)
        except Exception as e:  # noqa: BLE001
            return rel, False, str(e), None

    bad = 0
    with cf.ThreadPoolExecutor(16) as ex:
        for rel, ok, a, b in ex.map(check, sample):
            if not ok:
                bad += 1
                print(f"  SIZE/HEAD MISMATCH: {rel}: server={a} local={b}")
    print(f"size sample: {len(sample)} checked, {bad} mismatches")

    ok = not missing and bad == 0
    print("RESULT:", "OK" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
