#!/usr/bin/env python3
"""Tavily search/extract helpers — reads key from the user's API rtf, never prints it.

Usage (import as module or copy the two functions):
    from tavily_helpers import tavily_search, tavily_extract
    r = tavily_search("INTerpath-001 phase 3", topic="news", days=14)
    for hit in r["results"]: print(hit["title"], hit["url"])

Notes:
- Key source: ~/Documents/Hermes/APIs/Tavily API.rtf (regex tvly-[A-Za-z0-9_-]{8,})
- Free tier ~1000 calls/month; sleep ~1.5s between calls to be safe.
- topic="news" + days=N filters by publication recency (use to check "any new
  official announcements since X" — absence of results IS the finding).
- extract accepts up to 5 urls per call; returns raw_content per page.
- Never echo the key into chat/terminal output.
"""
import json
import os
import re
import time
import urllib.request

KEY_RTF = os.path.expanduser("~/Documents/Hermes/APIs/Tavily API.rtf")


def _load_key() -> str:
    raw = open(KEY_RTF, "rb").read().decode("utf-8", errors="ignore")
    m = re.search(r"tvly-[A-Za-z0-9_-]{8,}", raw)
    assert m, "Tavily key not found in " + KEY_RTF
    return m.group(0)


def _post(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + _load_key()},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def tavily_search(query: str, n: int = 8, topic: str = "general",
                  days: int | None = None, depth: str = "advanced") -> dict:
    """topic: 'general' or 'news'. days filters news recency (e.g. 7/14/30)."""
    payload = {"query": query, "search_depth": depth, "max_results": n, "topic": topic}
    if days:
        payload["days"] = days
    return _post("https://api.tavily.com/search", payload)


def tavily_extract(urls: list[str]) -> list[dict]:
    """Full-text extraction, up to 5 urls per call."""
    if len(urls) > 5:
        urls = urls[:5]
    r = _post("https://api.tavily.com/extract", {"urls": urls})
    return r.get("results", [])


def html_to_text(html: str) -> str:
    """Minimal HTML→text for curl-fetched pages when web_extract is blocked."""
    import html as h
    html = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html,
                  flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", "\n", html)
    lines = [re.sub(r"\s+", " ", h.unescape(l)).strip() for l in html.split("\n")]
    return "\n".join(l for l in lines if l)


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "test"
    out = tavily_search(q)
    print(f"{len(out.get('results', []))} results for: {q}")
    for r in out.get("results", [])[:8]:
        print("-", r.get("title"), "|", r.get("url"))
    time.sleep(1.5)
