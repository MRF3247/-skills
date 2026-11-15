---
name: hermes-plugin-development
description: "Build Hermes provider plugins; install ClawHub skills."
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, plugins, providers, image-gen, clawhub, skills, development]
---

# Hermes Plugin & Provider Development

Extending Hermes with a new tool backend (image generation, video, TTS, model
providers) is done via **plugins**, not by editing core. This skill covers the
provider plugin architecture, the ClawHub skill-install quirks, and the
secrets/testing workflow. The bundled `hermes-agent` skill covers general
configuration; this one is for writing actual plugin code.

## When to use

- User wants a third-party API (MiniMax, new image/video model, custom TTS) wired into a Hermes tool
- `hermes skills install <name>` fails to resolve a ClawHub/community skill
- Any task touching `~/.hermes/plugins/` or the `plugins.enabled` config

## Architecture quick map

- Provider plugins live in `<repo>/plugins/<category>/<name>/` (bundled,
  auto-loaded) or `~/.hermes/plugins/<category>/<name>/` (user, **opt-in**).
- `kind: backend` in plugin.yaml = pluggable backend for an existing core tool
  (image_gen, video_gen, tts). Registry keys are path-derived:
  `image_gen/minimax`, `video_gen/...`, `tts/...`.
- The active image provider is chosen by `image_gen.provider` in config.yaml;
  the model by `image_gen.model`. Same pattern for other categories.
- Plugin entry point is `def register(ctx)` calling
  `ctx.register_image_gen_provider(Provider())` (or the category's equivalent).

## Adding a custom image_gen provider (worked example: MiniMax image-01)

1. Create `~/.hermes/plugins/image_gen/<name>/plugin.yaml`:

   ```yaml
   name: minimax
   version: 1.0.0
   description: "MiniMax image generation backend (image-01)."
   author: user
   kind: backend
   requires_env:
     - MINIMAX_API_KEY
   ```

2. Create `__init__.py` in the same dir implementing the ABC from
   `agent.image_gen_provider` — subclass `ImageGenProvider`, implement
   `name`, `display_name`, `is_available`, `list_models`, `default_model`,
   `get_setup_schema`, `capabilities`, and `generate(prompt, aspect_ratio=...,
   *, image_url=None, reference_image_urls=None, **kwargs) -> dict`.
   End with `def register(ctx): ctx.register_image_gen_provider(Provider())`.
   Use the helper builders: `success_response(image=, model=, prompt=,
   aspect_ratio=, provider=, modality=, extra=)` and `error_response(error=,
   error_type=, provider=, model=, prompt=, aspect_ratio=)`. For APIs that
   return ephemeral URLs, cache bytes locally with `save_url_image(url,
   prefix=...)` (falls back to the bare URL on failure); for base64 use
   `save_b64_image`. See `templates/image_gen_provider.py`.

3. Enable and configure (the "not a recognized config key" warning on
   `hermes config set` for these keys is cosmetic — the code reads them):

   ```bash
   hermes config set plugins.enabled '["image_gen/minimax"]'
   hermes config set image_gen.provider minimax
   hermes config set image_gen.model image-01
   ```

4. Test **with the Hermes venv python**, never system python3:

   ```bash
   ~/.hermes/hermes-agent/venv/bin/python -c "..."
   ```

   System python3 lacks `requests` and other deps. Also: `get_secret` reads
   `os.environ` (loaded from the Hermes .env at startup) — a standalone test
   process must load the .env into `os.environ` itself before calling
   `is_available()`/`generate()`. `scripts/test_image_provider.py` does this.

## Installing skills from ClawHub

- Search with JSON output to get exact identifiers:
  `hermes skills search --source clawhub --json <query>`
- **Install with the source prefix**: `hermes skills install clawhub/<identifier>`.
  A bare identifier often fails with `No exact match ... Did you mean one of these?`
  even though search found it — the resolver requires the qualified form.
- Community skills are security-scanned on install (verdict SAFE/ALLOWED);
  `hermes skills inspect <id>` previews content first. Use `-y` to skip the prompt.
- Some search hits are phantom entries that fail to fetch
  (`Could not fetch 'clawhub/<id>' from any source`) — skip them and use a sibling.
- `hermes skills list` shows installed skills and their source.

## Secrets & endpoint discovery

- Keys live in the Hermes .env (one line per var, `#` prefix = commented).
- Multi-endpoint providers: probe each endpoint with a real minimal call to
  discover which accepts the key. MiniMax example: intl key on the CN endpoint
  returns `invalid api key`; a valid CN key with no credit returns
  `insufficient balance` (key valid, account needs top-up).
- Never print API keys in terminal output or chat — mask them
  (`key[:4] + '***' + key[-4:]`) and use sed on output for verification.
- Extract keys from RTF files by stripping RTF control words
  (`\\[a-z]+[-0-9]* ?`, `{}`, hex escapes) before regex-searching for the token.

## Pitfalls

- **Editing the .env**: match lines with AND without the `#` comment prefix,
  and prefer a simple exact-string replace over complex per-line logic. A
  placeholder round-trip (write placeholder, then try to replace it) is a
  failure mode — write the real value once, verify with a masked grep.
- **Image provider quirks**: MiniMax `image-01` is text-to-image only; image
  editing (i2i) is a different endpoint and needs separate wiring. Report
  `unsupported` cleanly instead of guessing payloads.
- **Long shell one-liners** (sed+grep pipes, big heredocs) can trip the
  command parser blocklist; prefer `read_file`/`search_files` or a short
  `python3 -c` / small script file.
- macOS Finder hides file extensions by default — a file like `minimaxAPI.rtf`
  may "appear" extension-less. Cmd+I (简介) → uncheck "隐藏扩展名", or Finder
  Settings → Advanced → show all extensions. Renaming alone does not convert
  RTF to plain text.

## Support files

- `references/minimax-image-api.md` — MiniMax image-01 API: endpoints, payload,
  response shape, error codes, intl-vs-CN key probing.
- `templates/image_gen_provider.py` — skeleton ImageGenProvider (copy & adapt).
- `scripts/test_image_provider.py` — loads .env, instantiates a provider by
  module path, runs is_available + a real generate() call.
