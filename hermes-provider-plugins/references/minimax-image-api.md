# MiniMax Image Generation API (image-01)

Verified against the official docs at platform.minimax.io (2026-08). Used by the
`minimax` image_gen plugin (see `templates/minimax_image_gen_provider.py`).

## Endpoints

| Scope | URL | Key env var |
|-------|-----|-------------|
| International | `https://api.minimax.io/v1/image_generation` | `MINIMAX_API_KEY` |
| Mainland China | `https://api.minimaxi.com/v1/image_generation` | `MINIMAX_CN_API_KEY` |

Auth: `Authorization: Bearer <key>` + `Content-Type: application/json`.

## Request payload (text-to-image)

```json
{
  "model": "image-01",
  "prompt": "A man in a white t-shirt, full-body, standing front view...",
  "aspect_ratio": "16:9",
  "response_format": "url",
  "n": 3,
  "prompt_optimizer": true
}
```

- `aspect_ratio`: `16:9`, `1:1`, `4:3`, `3:4`, `9:16`
- `n`: batch size, up to 9 images per request
- `response_format`: `url` (default) or `base64`

## Response (HTTP 200)

```json
{
  "id": "...",
  "data": { "image_urls": ["XXX", "XXX", "XXX"] },
  "metadata": { "failed_count": "0", "success_count": "3" },
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

**Always check `base_resp.status_code == 0` before trusting `data`** — API-level
errors (bad key, rate limit, invalid prompt) come back as HTTP 200 with a nonzero
`base_resp.status_code`.

## Critical facts for a provider plugin

- Returned `image_urls` are TEMPORARY (docs: download within 24h). Cache bytes
  locally via `save_url_image()` at tool-completion time — never hand the bare
  URL to a downstream consumer that may fetch it later (Telegram, browser).
- Image-to-image (i2i) is a SEPARATE endpoint (`image-generation-i2i`) with a
  different payload (image/reference input). The `minimax` plugin declares
  text-only capabilities and returns `unsupported` rather than faking i2i.
- Model names: `image-01` (t2i), `image-01-live`. Cost at launch ~1/10 of
  comparable models; batch of 9 supported.

## Reading the docs

`web_extract` may block platform.minimax.io pages with a "private or internal
network address" verdict. Works reliably:
`curl -sL --max-time 25 "<docs-url>" -H "User-Agent: Mozilla/5.0 ..."` then
strip tags with python (regex `<[^>]+>` → text) and grep for the keywords
(`image_generation`, `aspect_ratio`, `base_resp`, `image_urls`).
