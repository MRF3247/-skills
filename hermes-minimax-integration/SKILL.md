---
name: hermes-minimax-integration
description: "Wire MiniMax image/TTS/vision into Hermes (resets on setup)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [hermes, minimax, image-gen, tts, vision, plugin, configuration]
---

# MiniMax API → Hermes Integration

Hook MiniMax (image-01 / M3 / T2A) into Hermes' image_gen, TTS, and vision
tools. Covers writing a custom image_gen provider plugin, config keys, the
China vs international endpoint split, and the `hermes setup` reset trap.

## Credentials & Endpoints

- International: `MINIMAX_API_KEY` → `https://api.minimax.io/v1`
- China: `MINIMAX_CN_API_KEY` → `https://api.minimaxi.com/v1`
- Keys live in `~/.hermes/.env` (never config.yaml). Existing template
  comments in .env show both.

## Capability map (important — models differ!)

| Capability | Works | Model / Endpoint |
|---|---|---|
| Image gen | ✅ | `image-01` via `POST /v1/image_generation` (auth: `Authorization: Bearer <key>`) |
| TTS | ✅ | `provider: minimax`, `region: cn\|global` → `POST /v1/t2a_v2` |
| Vision (image understanding) | ✅ | **Only `MiniMax-M3`** via standard `POST /v1/chat/completions` with `image_url` content blocks |
| Vision ❌ | ❌ | M2.7 / M2.5 / M2.1 / M2 are TEXT-ONLY — they reply "I don't see an image" |
| STT | ❌ | MiniMax a2t is NOT OpenAI-compatible; Hermes has no custom STT endpoint — use local Whisper or Groq |

Vision gotcha: `/v1/vl/chat/completions` (VL endpoint) does NOT exist on
platform.minimaxi.com (404). Use plain chat/completions + MiniMax-M3.
`MiniMax-VL-01` model name also 404s on the CN platform.

## Image gen: custom provider plugin

Hermes ships image_gen backends as plugins: `<repo>/plugins/image_gen/<name>/`
(bundled) or `~/.hermes/plugins/image_gen/<name>/` (user). User backends are
opt-in via `plugins.enabled`.

1. Create `~/.hermes/plugins/image_gen/minimax/plugin.yaml`:
   ```yaml
   name: minimax
   version: 1.0.0
   description: "MiniMax image generation backend (image-01)."
   author: user
   kind: backend
   requires_env:
     - MINIMAX_API_KEY
   ```
2. Create `__init__.py` implementing `ImageGenProvider` (from
   `agent.image_gen_provider`): `name`, `display_name`, `is_available`,
   `list_models`, `default_model`, `generate(prompt, aspect_ratio, ...)`.
   Use `get_secret("MINIMAX_CN_API_KEY")` (agent.secret_scope) for keys,
   `save_url_image(url, prefix=...)` / `success_response(...)` /
   `error_response(...)` helpers. `register(ctx)` calls
   `ctx.register_image_gen_provider(Provider())`.
3. Enable (IMPORTANT — bare `hermes config set plugins.enabled` writes a
   STRING, not a YAML list, and the plugin manager silently ignores it):
   ```
   hermes plugins enable image_gen/minimax
   ```
4. Select:
   ```
   hermes config set image_gen.provider minimax
   hermes config set image_gen.model image-01
   ```

## TTS

```
hermes config set tts.provider minimax
hermes config set tts.minimax.region cn   # or global
```
Resolver (`tools/tts_tool.py:_resolve_minimax_tts_runtime`) auto-picks CN
endpoint when only MINIMAX_CN_API_KEY exists; explicit region wins.

## Vision

```
hermes config set auxiliary.vision.provider custom
hermes config set auxiliary.vision.base_url https://api.minimaxi.com/v1
hermes config set auxiliary.vision.model MiniMax-M3
hermes config set auxiliary.vision.api_key_env MINIMAX_CN_API_KEY
```
`api_key_env` reads the key from .env — do NOT write the key into
config.yaml. Verify with `resolve_vision_provider_client()` from
`agent.auxiliary_client`.

## Testing (offline, no key printed)

Use the Hermes venv python: `~/.hermes/hermes-agent/venv/bin/python`
(system python3 lacks `requests` and is too old for `str | None` syntax).
Load .env manually before importing tools:
```python
for line in open(os.path.expanduser('~/.hermes/.env')):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
```

## Pitfalls

- **`hermes setup` WIPES parts of config.yaml**: plugins.enabled,
  image_gen.*, and tts.* sections get reset (auxiliary.vision survives).
  After any setup run, re-check and re-apply this skill's config commands.
- `hermes config set` warns "not a recognized config key" for nested plugin
  keys — harmless, value still saved. Use `--force` to silence.
- First `hermes config set auxiliary.vision.provider custom` appeared to
  succeed but didn't persist (no --force); re-run with `--force` and verify
  in config.yaml before testing.
- Plugins require a NEW session to take effect (discovery runs at startup).
- `hermes plugins enable` asks about tool-override privilege — answer no
  unless the plugin replaces a builtin.
