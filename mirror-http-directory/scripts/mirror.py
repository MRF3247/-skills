#!/usr/bin/env python3
"""Mirror a directory tree served over plain HTTP (SimpleHTTP-style listings).

Usage: python3 mirror.py BASE_URL OUT_DIR
Example: python3 mirror.py http://192.168.31.25:8899/ ~/staging
Exits non-zero if any URL failed; rerun to retry (downloads are overwritten).
"""
import os
import re
import sys
import urllib.parse
import urllib.request


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    base = sys.argv[1]
    if not base.endswith("/"):
        base += "/"
    out = os.path.expanduser(sys.argv[2])
    li_re = re.compile(r'<a href="(.+?)">')

    visited = set()
    queue = [base]
    saved = 0
    total_bytes = 0
    errors = []

    while queue:
        url = queue.pop()
        if url in visited:
            continue
        visited.add(url)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
        except Exception as e:  # noqa: BLE001
            errors.append((url, str(e)))
            continue

        # Keep the URL percent-encoded on the wire; unquote only the path
        # for the local filename (handles spaces / CJK names).
        rel = urllib.parse.unquote(urllib.parse.urlparse(url).path).lstrip("/")
        lp = os.path.join(out, rel)

        if url.endswith("/"):  # directory listing
            os.makedirs(lp, exist_ok=True)
            for href in li_re.findall(data.decode("utf-8", "replace")):
                full = urllib.parse.urljoin(url, href)
                if full.rstrip("/") == base.rstrip("/"):
                    continue  # the listing links to itself
                if full not in visited:
                    queue.append(full)
        else:  # file
            os.makedirs(os.path.dirname(lp), exist_ok=True)
            with open(lp, "wb") as f:
                f.write(data)
            saved += 1
            total_bytes += len(data)
            if saved % 500 == 0:
                print(f"  ... {saved} files", flush=True)

    ndirs = sum(1 for u in visited if u.endswith("/"))
    print(f"done: {saved} files, {total_bytes / 1024 / 1024:.1f} MiB, {ndirs} dirs")
    if errors:
        print(f"errors ({len(errors)}):")
        for u, e in errors[:20]:
            print("  ", u, "->", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
