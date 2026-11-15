---
name: hermes-tool-verification
description: "Verify Hermes tools after restart/setup; keys never printed."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [hermes, verification, health-check, plugins, providers, api-keys, troubleshooting]
---

# Hermes Tool/Provider Verification

Use when the user restarts Hermes, runs setup, or asks "检查下配置的工具是不是都正常运行了 / is everything still working". Also applies after installing/updating a provider plugin. Goal: confirm the whole chain (config → plugin → credential → endpoint → real call) works, WITHOUT ever printing API keys to chat or terminal.

## Verification ladder (fast → thorough)

1. **Doctor + config** — `hermes doctor` (every toolset should show ✓; note the ⚠ lines: missing tokens like DISCORD_BOT_TOKEN are expected/benign, but a tool the user actually configured must NOT be ⚠). Confirm the relevant section: `hermes config get <tool>` (e.g. `image_gen` → provider+model).
2. **Plugin/backend files** — plugin dir exists and has its loader: `ls ~/.hermes/plugins/<tool>/<name>/` (expect `__init__.py` + `plugin.yaml`).
3. **Credential presence, masked** — list only the variable NAMES, never values:
   ```bash
   grep -oE "PREFIX_[A-Z_]*=" ~/.hermes/.env | sort -u
   ```
   To confirm a value exists without revealing it: `KEY=$(grep -E "^VAR=" ~/.hermes/.env | cut -d= -f2- | tr -d '"' | tr -d "'"); echo "len=${#KEY}"`.
4. **Endpoint reachability** — `curl -s -o /dev/null -w "%{http_code}" --connect-timeout 8 https://<api-host>` — ANY HTTP code (404 on the root path is normal) proves TLS+route are fine; only a timeout/connection failure means the network path is down. Cheap way to rule out network issues before spending money on a real call.
5. **Real end-to-end probe** — one actual API call with the key read from .env (never echoed): POST to the provider's real endpoint, expect success status + a result (URL/file). If the tool wrapper (`image_generate`, `text_to_speech`) failed, probe the raw API with curl first to isolate wrapper vs API vs network.

## Pitfalls

- **Tool wrapper read-timeout ≠ broken plugin.** A 120s `Read timed out` from the tool call is often transient network jitter. Do NOT report the plugin as broken; re-verify with the direct curl probe (it usually succeeds immediately after). The lesson is the retry-via-curl pattern.
- **Never echo the key.** Read it into a shell var from .env and reuse; print only length/name. The user (key-security preference) wants keys written to config files, not displayed.
- **Check cache/temp for artifacts after testing.** Generated test images may be cached (e.g. `~/.hermes/cache/images/`), TTS probes may leave mp3s in /tmp. Clean them up.

## Artifact hygiene (user preference — hard rule)

ALL artifacts this user's sessions create — test images, audio, scripts, temp files, research docs — go in the working folder `/Users/Jin/Documents/Hermes`. Never /tmp, ~/Downloads, or anywhere else (unless objectively impossible). The same rule applies to verification test artifacts: generate them in the working folder and delete them (or leave them there) — never scatter them.

## Scripts

- `scripts/verify_minimax.sh` — end-to-end probe for the MiniMax image_gen plugin (config → plugin dir → masked key → endpoint → real image generation, artifact into a chosen output dir). Pattern transfers to any provider: swap endpoint/headers/body.
