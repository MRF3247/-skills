# MiniMax-M3 Batch Analysis — Script Patterns

Concrete, battle-tested patterns for driving MiniMax-M3 (vision, CN endpoint `https://api.minimaxi.com/v1`, key env `MINIMAX_CN_API_KEY` from `~/.hermes/.env` or config.yaml).

## Key facts about the model

- **Reasoning model**: `enable_thinking: false` is silently ignored. Every response contains `<think>...</think>`.
- **Thinking eats the token budget**: with `max_tokens: 400`, long prompts produce only the think block — the real answer is truncated to empty after stripping tags. **Always use `max_tokens: 1500+` for any generation task.**
- **Fixed-line format > strict JSON**: the model frequently answers JSON requests with prose/self-talk ("The user wants me to... Let me break down..."). A rigid 4-line format (`前缀：值`) parses reliably.
- **Occasional `socket.timeout`** on reads — `socket.timeout` is NOT a subclass of `urllib.error.URLError`, so an except clause on URLError alone crashes the run. Catch it explicitly.

## Shared API call skeleton

```python
payload = {
    "model": "MiniMax-M3",
    "messages": [{"role": "user", "content": PROMPT}],  # text-only: no image_url part
    "max_tokens": 1500,
    "temperature": 0.2,
    "enable_thinking": False,  # ineffective, keep anyway (harmless)
}
req = urllib.request.Request("https://api.minimaxi.com/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
r = json.loads(urllib.request.urlopen(req, timeout=90).read())
content = r["choices"][0]["message"]["content"]
```

Vision variant: replace `content` with a list:
```python
"content": [
    {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
    {"type": "text", "text": PROMPT},
]
```
mime map: jpg→jpeg, png→png, webp→webp. Small images (~1MP) cost ~400 input tokens.

## Sanitize + validate + retry loop

```python
def clean(content):
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)  # DOTALL!
    content = re.sub(r"<[^>]+>", "", content).strip()
    return content

def valid_zh(content):
    cn = len(re.findall(r"[\u4e00-\u9fff]", content))
    return cn > 40 and "The user" not in content and "Let me" not in content

for attempt in range(4):  # re-request until valid, never reuse bad content
    content = clean(api_call())
    if valid_zh(content):
        break
    time.sleep(2 * (attempt + 1))
```

## Fixed-line parsing (preferred over JSON)

Prompt asks for exactly:
```
风格_中：...
风格_英：...
元素_中：...
元素_英：...
```
Parse: for each line, `startswith(key + "：")` (also try ASCII `:`), take the part after the separator. Require ALL fields non-empty or retry.

## Template string gotcha

Never `.format()` a prompt that contains literal JSON braces — `KeyError` on `{"风格_中"`. Either escape braces as `{{ }}` or use `PROMPT.replace("__ZH__", zh).replace("__EN__", en)` placeholders. Placeholder-replace is simpler and safer.

## Fallback when the model refuses repeatedly

Stitch the already-collected Chinese 7-dimension fields into a usable style prompt:
```python
style_zh = "，".join([v[构图], v[配色], v[风格媒介], v[光影质感], v[字体特征], v[时代标签]])  # drop 主体
elements = v["主体"]  # the 主体 field IS the element list
```

## Batch script hygiene

- `ThreadPoolExecutor(max_workers=5)` for vision calls, 4 for text-only.
- Resume: load existing result JSON at start, skip files already present; dump every 10-15 completions.
- Print progress `[done/total]` with flush=True so background runs show liveness.
- Full-path bug: `os.path.isfile(f)` on a bare filename returns False when cwd differs — always `os.path.join(IMG_DIR, f)`.
