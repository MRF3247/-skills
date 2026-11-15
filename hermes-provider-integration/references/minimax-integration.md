# MiniMax Integration Reference

Verified against MiniMax official docs and live API probes (2026-08).

## Credentials & endpoints

| Region | Env var | Base URL | Notes |
|--------|---------|----------|-------|
| global | `MINIMAX_API_KEY` | https://api.minimax.io/v1 | platform.minimax.io |
| cn | `MINIMAX_CN_API_KEY` | https://api.minimaxi.com/v1 | platform.minimaxi.com (mainland China) |

- Keys look like `sk-...` (observed length 126). A key issued on one platform is
  NOT valid on the other — probe both before committing:
  - "invalid api key" → wrong endpoint for this key
  - "insufficient balance" → key valid, account needs funds
- OpenAI-compatible: `export OPENAI_BASE_URL=https://api.minimaxi.com/v1` +
  standard `chat.completions` calls. Model list via `GET /v1/models`
  (OpenAI-wire). M2.x models force/adaptive thinking; M3 supports
  `reasoning_split` via `extra_body`.

## Image generation (text-to-image, model `image-01`)

- `POST {base}/v1/image_generation`
- Headers: `Authorization: Bearer <key>`, `Content-Type: application/json`
- Body:
  ```json
  {"model": "image-01", "prompt": "...", "aspect_ratio": "16:9",
   "response_format": "url", "n": 1, "prompt_optimizer": true}
  ```
  - `aspect_ratio` values: `16:9`, `1:1`, `4:3`, `3:4`, `9:16`
  - `n` up to 9 per request (batch); `response_format`: `url` | `base64`
- Response:
  ```json
  {"id": "...", "data": {"image_urls": ["..."]},
   "metadata": {"failed_count": "0", "success_count": "3"},
   "base_resp": {"status_code": 0, "status_msg": "success"}}
  ```
  - Success = `base_resp.status_code` is 0 (int or str). image_urls are
    TEMPORARY — download/cache them immediately (save_url_image pattern).
- Image-01 also supports `subject_reference` (character consistency) and
  image-to-image via the i2i endpoint — not yet wired in the Hermes plugin.

## TTS (speech synthesis, t2a_v2)

- Built into Hermes `tools/tts_tool.py` — no plugin needed.
- `hermes config set tts.provider minimax`
- `hermes config set tts.minimax.region cn`  (or `global`)
- Endpoints: `https://api.minimax.io/v1/t2a_v2` (global) /
  `https://api.minimaxi.com/v1/t2a_v2` (cn)
- Region resolution: explicit `tts.minimax.region` wins; else global key if set;
  else cn key if it is the only one. A configured `base_url` must match the
  region host or Hermes raises.
- Sync char cap: 10000 (minimax) per `tts_tool.py`.
- **Response quirk — `data.audio` is HEX, not base64.** The t2a_v2 response's
  `data.audio` field is a hex-encoded string (first bytes `4944330400000000...`
  = "ID3" in hex), NOT base64. Decode with `binascii.unhexlify(data["audio"])`
  and write the bytes straight to the file. Base64-decoding it produces a
  corrupt file that `file` reports as "data" (no ID3 magic) and that
  PyAV/whisper reject with "Invalid data" or transcribe as empty — a confusing
  silent failure. Verified live with `speech-02-hd`, `format: mp3` (2026-08).

## Vision (image understanding)

- **Only `MiniMax-M3` accepts image input** via OpenAI-wire
  `chat.completions` with `image_url` content parts. M2.7 / M2.5 / M2.1 / M2
  are TEXT-ONLY — they reply "I don't see an image" and never error, so a
  wrong model looks like a silent failure. Verified by live probe (2026-08).
- `/v1/vl/chat/completions` (VL endpoint) does NOT exist on
  platform.minimaxi.com (404). `MiniMax-VL-01` as a model name also 404s on
  the CN platform. Use plain `/v1/chat/completions` + `MiniMax-M3`.
- Hermes wiring (NOT in the interactive menus):
  `auxiliary.vision.provider=custom`,
  `auxiliary.vision.base_url=https://api.minimaxi.com/v1`,
  `auxiliary.vision.model=MiniMax-M3`,
  `auxiliary.vision.api_key_env=MINIMAX_CN_API_KEY`.
  Prefer `api_key_env=<ENV_VAR>` (reads the key from .env at runtime) over
  `api_key=<plaintext>` — never write the key into config.yaml. Use `--force`
  on `hermes config set` and verify the values actually landed in config.yaml
  (a first attempt without --force appeared to succeed but did not persist).
- Config defaults live in `hermes_cli/config_defaults.py` under
  `auxiliary.vision`; provider enum: `auto | openrouter | nous | codex | custom`.
- `auto` uses the main chat model when it supports vision; deepseek main model
  is text-only, so a custom endpoint is the way to go.
- Verify resolution offline with
  `resolve_vision_provider_client()` from `agent.auxiliary_client` — it
  returns (provider, client, model) and confirms base_url + api_key picked up.

## Hermes plugin files (image gen, as installed)

- `~/.hermes/plugins/image_gen/minimax/plugin.yaml`:
  ```yaml
  name: minimax
  version: 1.0.0
  description: "MiniMax image generation backend (image-01)..."
  author: user
  kind: backend
  requires_env:
    - MINIMAX_API_KEY
  ```
- `~/.hermes/plugins/image_gen/minimax/__init__.py`: `MiniMaxImageGenProvider`
  subclasses `ImageGenProvider`; `register(ctx)` calls
  `ctx.register_image_gen_provider(...)`. CN credential wins when present
  (`MINIMAX_CN_API_KEY` → minimaxi.com), else global.
- Config: `plugins.enabled: [image_gen/minimax]` (via `hermes plugins enable`),
  `image_gen.provider: minimax`, `image_gen.model: image-01`.
- Key in `~/.hermes/.env` as `MINIMAX_CN_API_KEY=sk-...`.

## Local STT (faster-whisper) — the venv-pip trap

- MiniMax a2t (ASR) is NOT OpenAI-compatible and Hermes has no custom STT
  endpoint, so STT means local Whisper or Groq. Local is free and offline.
- The Hermes venv has NO `pip` module (`python -m pip` → "No module named
  pip"). Install with uv:
  `uv pip install --python ~/.hermes/hermes-agent/venv/bin/python faster-whisper`
  (uv lives at `~/.hermes/bin/uv`).
- No system ffmpeg needed: faster-whisper decodes MP3 via its bundled PyAV
  (av 18.x). A missing ffmpeg binary is a red herring if PyAV opens the file.
- Config: `stt.provider: local` (default), `stt.local.model: base`. The base
  model is usable on zh but imperfect (e.g. 识别→实别); small/medium are more
  accurate at a speed cost.
- Closed-loop verification: generate audio with MiniMax TTS (hex-decode!),
  then `WhisperModel("base", device="cpu", compute_type="int8").transcribe(...)`
  with `language="zh"`. Expect ~90% accuracy; don't require exact match.
