# MiniMax-M3 vision API — measured facts (2026-08)

Used as Hermes' auxiliary vision model. All values below were measured
live on 2026-08-04 against the CN endpoint during a 60-image batch job.

## Endpoints & keys
- CN: `https://api.minimaxi.com/v1` — key `MINIMAX_CN_API_KEY` in
  `~/.hermes/.env` (never config.yaml, never printed in chat)
- International: `https://api.minimax.io/v1` — key `MINIMAX_API_KEY`
- Config block (survives `hermes setup`):
  `auxiliary.vision.provider=custom`, `.model=MiniMax-M3`,
  `.base_url=https://api.minimaxi.com/v1`,
  `.api_key_env=MINIMAX_CN_API_KEY`

## Model list (GET {base_url}/v1/models)
Returns: MiniMax-M3, MiniMax-M2.7, MiniMax-M2.7-highspeed, MiniMax-M2.5,
MiniMax-M2.5-highspeed, MiniMax-M2.1, MiniMax-M2.1-highspeed, MiniMax-M2.
**Vision works ONLY on MiniMax-M3** — the M2.x family are text-only and
reply "I don't see an image".

## Chat completions (vision)
POST `{base_url}/chat/completions`, OpenAI-compatible. Image via content
block:
```json
{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
```
MIME map: jpg→jpeg, png→png, webp→webp. Full base64 inline is fine for
screenshots (<2MB); for very large images downscale first.

## Reasoning-model behavior (critical)
MiniMax-M3 is a REASONING model: every response starts with a
`<think>...</think>` block that counts toward completion tokens. For
machine-consumed output:
- strip `<think>...</think>` (regex `re.S`), then any stray XML tags
- parse JSON tolerantly: `json.loads` fails → slice `content[first { : last }]`
- a `max_tokens: 100` probe returned ~50 tokens of think text + ~50 of
  answer — budget accordingly (use ~900 for structured 11-field JSON)

## Measured token costs
- 375×491 PNG (≈0.18MP) + short prompt → 439 input tokens (≈400 for the
  image itself), 100 completion
- ~1.1MP average screenshot → ≈300–600 input tokens
- 60 images @ 5 concurrent workers: 148s wall clock, 0 failures, all
  responses parsed cleanly (temperature 0.2, max_tokens 900)

## Practical tuning
- temperature 0.2 → stable, parseable JSON (default 1.0 drifts format)
- 3-attempt retry with 3s/6s/9s backoff absorbs transient 5xx
- checkpoint the results JSON every ~10 items; resume skips done keys —
  a timeout then costs nothing

## Verify without leaking the key
Read the key inside the shell from .env and pass via env var to the
script (`K="$KEY" python3 ...`); never echo it. Model availability:
`curl -s {base_url}/models -H "Authorization: Bearer $KEY"` and grep the
returned IDs.
