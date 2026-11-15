---
name: hermes-provider-integration
description: "Wire custom AI providers into Hermes (image, TTS, vision)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, providers, image-gen, tts, vision, plugins, minimax, configuration]
---

# Hermes Provider Integration

Use when the user wants Hermes to use a third-party API that is NOT listed in the
built-in `hermes tools` menus (image generation, TTS, vision) — e.g. MiniMax image
gen, a custom vision endpoint, or any OpenAI-compatible backend. Covers the two
real paths: (A) config-key wiring for features that already have built-in support,
and (B) writing a custom image_gen provider plugin.

## Core facts (learned the hard way)

1. **The `hermes tools` provider menus only list built-ins.** A provider missing
   from the menu is NOT absent from Hermes — it may be configurable via config.yaml
   keys (TTS, vision) or need a plugin (image_gen). Always check the code before
   telling the user "not supported": `tools/tts_tool.py`, `agent/auxiliary_client.py`,
   `hermes_cli/config_defaults.py`, `agent/image_gen_registry.py`.

2. **`hermes config set` writes list values as STRINGS.** `hermes config set
   plugins.enabled '["image_gen/minimax"]'` stores a literal string, and the plugin
   manager silently reads nothing (`_get_enabled_plugins()` requires a real YAML
   list → returns None → plugin reported "not enabled in config"). The correct
   command is `hermes plugins enable <path-key>` (e.g. `image_gen/minimax`), which
   writes a proper YAML list. It also answers "allow tool override?" — decline
   unless the plugin genuinely replaces built-in tools.

3. **`hermes skills install` on ClawHub needs the `clawhub/<name>` prefix.**
   Bare names fail with "No exact match... Did you mean" even though
   `hermes skills search --source clawhub` shows them. `clawhub/paper-writer`
   works; `clawhub:name` and `name@clawhub` do not. Use `--json` on search to get
   exact identifiers.

4. **Secrets live in process env, not the .env file directly.** `get_secret()`
   reads `os.environ`; Hermes loads `~/.hermes/.env` at startup. A standalone
   test script must load `.env` into `os.environ` manually (skip `#` comments and
   blanks). Test with the Hermes venv python (path is in the launcher shebang,
   e.g. `~/.hermes/hermes-agent/venv/bin/python`), because system python often
   lacks deps like `requests`.

5. **Verify plugin registration the official way** (not by guessing):
   ```python
   from hermes_cli.plugins import PluginManager
   pm = PluginManager(); pm.discover_and_load(force=True)
   from agent.image_gen_registry import list_providers
   [p.name for p in list_providers()]   # check your provider is in the list
   ```

## Path A — Config-key wiring (TTS, vision, custom endpoints)

- TTS: `hermes config set tts.provider <name>` (built-in support, see
  `tools/tts_tool.py` for per-provider keys, e.g. `tts.minimax.region`).
- Vision: `auxiliary.vision.{provider,model,base_url,api_key}` — provider is
  `auto | openrouter | nous | codex | custom`; `custom` = any OpenAI-compatible
  endpoint (`base_url` + `api_key` + `model`). `hermes config set` warns on
  unrecognized keys but saves them — the code reads them anyway.
- `hermes config set` warnings about unrecognized keys are schema notices, not
  failures.

## Path B — Custom image_gen provider plugin

Files under `~/.hermes/plugins/image_gen/<name>/` (user plugins, opt-in):

- `plugin.yaml` — `name`, `kind: backend`, `requires_env: [KEY]`.
- `__init__.py` — subclass `agent.image_gen_provider.ImageGenProvider`
  (implement `name` + `generate`; use helpers `success_response`,
  `error_response`, `save_url_image`, `save_b64_image`,
  `resolve_aspect_ratio`, `normalize_reference_images`) and expose
  `def register(ctx): ctx.register_image_gen_provider(Provider())`.

Then: `hermes plugins enable image_gen/<name>` (NOT `config set`), set
`image_gen.provider=<name>` and `image_gen.model=<model>`, put the API key in
`~/.hermes/.env`. Changes take effect on a NEW session.

See `templates/image_gen_plugin_scaffold.py` for a known-good provider skeleton.

## Secrets hygiene

- Never echo API keys into the terminal or chat. To move a key from a user
  document into `.env`, write a throwaway script that extracts → probes → writes
  and prints only masked diagnostics (`key[:4]...key[-4:]`). Probe both regional
  endpoints before committing: "invalid api key" vs "insufficient balance"
  distinguishes wrong-endpoint from valid-key-no-funds.
- Prefer config-set / .env writes over typing keys into interactive menus (keys
  flash on screen).

## MiniMax specifics

Endpoint map, model names, request/response formats, and the exact config values
for image gen (image-01), TTS (t2a_v2), and vision (M2.x) live in
`references/minimax-integration.md`.
