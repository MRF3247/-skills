# MiniMax Image Generation API (image-01)

Reference for wiring MiniMax's text-to-image API into Hermes or scripts.
Verified against platform.minimax.io docs (2026-08).

## Endpoints (two separate platforms — keys are NOT interchangeable)

| Platform | Base URL | Key env var |
|---|---|---|
| International | `https://api.minimax.io/v1/image_generation` | MINIMAX_API_KEY |
| China | `https://api.minimaxi.com/v1/image_generation` | MINIMAX_CN_API_KEY |

A key issued on one platform is rejected by the other (`invalid api key`).
Probe BOTH endpoints with a minimal real call to discover which accepts the key.

## Request (POST, JSON)

Headers: `Authorization: Bearer <key>`, `Content-Type: application/json`

```json
{
  "model": "image-01",
  "prompt": "A man in a white t-shirt, ... photorealistic.",
  "aspect_ratio": "16:9",
  "response_format": "url",
  "n": 1,
  "prompt_optimizer": true
}
```

- `aspect_ratio`: `16:9`, `1:1`, `4:3`, `3:4`, `9:16` (map Hermes
  landscape/square/portrait → 16:9 / 1:1 / 9:16)
- `response_format`: `url` (default) or `base64`
- `n`: up to 9 images per request (batch)
- `prompt_optimizer`: bool, auto-improves the prompt

## Response (200)

```json
{
  "id": "...",
  "data": { "image_urls": ["https://..." ] },
  "metadata": { "failed_count": "0", "success_count": "1" },
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

Success check: `base_resp.status_code == 0`. URLs are TEMPORARY (download
within ~24h) — cache bytes locally before returning (use `save_url_image`).

## Error signals (base_resp.status_msg)

| Message | Meaning |
|---|---|
| `invalid api key` | Wrong endpoint for this key (intl vs CN mismatch) |
| `insufficient balance` | Key valid, account has no credit — needs top-up |
| non-zero `status_code` | API-side failure — surface status_msg to the user |

## Models

- `image-01` — text-to-image (and image-to-image via a separate i2i endpoint)
- `image-01-live` — live/video-capable variant
- Batch up to 9 images/request; character-reference support for consistent characters

## Testing pattern

Probe with a minimal call (cheap): `n=1`, `aspect_ratio="1:1"`, tiny prompt.
Never print the key — mask as `key[:4] + '...' + key[-4:]`.
