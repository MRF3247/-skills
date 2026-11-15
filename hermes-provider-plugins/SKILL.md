---
name: hermes-provider-plugins
description: "Add image/video/TTS backends to Hermes via user plugins."
version: 1.0.0
author: Hermes Agent (curated)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, plugins, image-gen, providers, extension, minimax]
---

# Hermes Provider Plugins

## When to use
The user wants a generation backend Hermes doesn't ship — e.g. MiniMax for images. The `hermes tools` picker only lists built-in providers (fal, deepinfra, krea, openai, openai-codex, openrouter, xai for image_gen). Adding a new one = writing a plugin; no core edits needed.

## Architecture
- Providers self-register via `PluginContext.register_image_gen_provider()` (alias `register_provider`) at import time. Active backend is chosen by `image_gen.provider` in config.yaml; model by `image_gen.model`.
- Two homes (see `agent/image_gen_provider.py` docstring):
  - Bundled: `<hermes-agent repo>/plugins/image_gen/<name>/` — auto-load, `kind: backend`
  - User: `~/.hermes/plugins/image_gen/<name>/` — opt-in via `plugins.enabled`
- The `plugins.enabled` key is path-derived: `image_gen/<name>` (e.g. `image_gen/minimax`).
- A plugin = `plugin.yaml` (manifest) + `__init__.py` exposing `register(ctx)`.

## Steps
1. Scaffold: `mkdir -p ~/.hermes/plugins/image_gen/<name>/`, write `plugin.yaml` and `__init__.py` (use `templates/minimax_image_gen_provider.py` as a known-good starting point).
2. Implement the `ImageGenProvider` ABC from `agent.image_gen_provider`: `name`, `display_name`, `is_available`, `list_models`, `default_model`, `get_setup_schema`, `capabilities`, `generate`. Use the provided helpers: `success_response`, `error_response`, `save_b64_image`, `save_url_image`, `resolve_aspect_ratio`, `normalize_reference_images`, `DEFAULT_ASPECT_RATIO`.
3. Read credentials with `get_secret("NAME")` from `agent.secret_scope` (reads ~/.hermes/.env). Never hardcode keys.
4. Enable:
   ```
   hermes config set plugins.enabled '["image_gen/<name>"]'
   hermes config set image_gen.provider <name>
   hermes config set image_gen.model <model-id>
   ```
   These print `⚠ '...' is not a recognized config key` warnings — benign, they are saved and the plugin loader reads them.
5. Verify offline (no key needed): load `__init__.py` with a fake ctx object that records `register_image_gen_provider` calls, then assert `provider.name`, `list_models()`, and that `is_available()` returns False without a key (that is correct behavior, not a bug).
6. End-to-end test needs the real key in ~/.hermes/.env. Fill it, then call `image_generate` or invoke `generate()` directly.

## Pitfalls
- User plugins are opt-in: without a `plugins.enabled` entry the plugin silently never loads. Built-in bundled ones auto-load; user ones do not.
- Provider APIs often return ephemeral/temporary URLs — always `save_url_image()` to `$HERMES_HOME/cache/images/` first; fall back to the bare URL only if caching fails (xAI/OpenAI providers set this precedent).
- Aspect ratios: Hermes passes the unified set `landscape|square|portrait`. Map to provider-specific values (MiniMax: `16:9 / 1:1 / 9:16`); `resolve_aspect_ratio` clamps invalid input to landscape.
- `generate()` must return the uniform response dict (success, image, model, prompt, aspect_ratio, modality, provider, error/error_type on failure) — build via `success_response`/`error_response`.
- Check provider-specific error envelopes in the response body (MiniMax: `base_resp.status_code != 0` = failure) before trusting `data`.
- i2i/edit support is separate: MiniMax's image-to-image endpoint has a different payload (image/reference input). Declare `capabilities() = {"modalities": ["text"], ...}` truthfully and return a clear `unsupported` error_response rather than guessing.

## Support files
- `templates/minimax_image_gen_provider.py` — known-good MiniMax image-01 provider plugin (`__init__.py` body); copy and adapt for other backends.
- `references/minimax-image-api.md` — MiniMax `/v1/image_generation` API: endpoints, auth, payload, response shape, aspect ratios, key env vars.
