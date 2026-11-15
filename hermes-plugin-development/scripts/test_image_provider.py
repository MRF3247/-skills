#!/usr/bin/env python3
"""Test a custom Hermes image_gen provider end-to-end.

Usage (run from ~/.hermes/hermes-agent with the VENV python):

    ./venv/bin/python /path/to/test_image_provider.py \
        /Users/<you>/.hermes/plugins/image_gen/<name>/__init__.py \
        "a red apple on white background"

Loads the Hermes .env into os.environ (get_secret reads process env),
instantiates the provider via its register() entry point, then checks
is_available() and runs one real generate() call.
"""

import importlib.util
import os
import sys
from pathlib import Path


def load_env(env_path: Path) -> None:
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    provider_path = Path(sys.argv[1]).resolve()
    prompt = sys.argv[2] if len(sys.argv) > 2 else "a red apple on white background"
    aspect = sys.argv[3] if len(sys.argv) > 3 else "square"

    home = Path(os.path.expanduser("~/.hermes"))
    load_env(home / ".env")

    spec = importlib.util.spec_from_file_location("provider_under_test", provider_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    providers = []
    class FakeCtx:
        def register_image_gen_provider(self, p): providers.append(p)
    mod.register(FakeCtx())

    if not providers:
        print("ERROR: register() registered no provider")
        sys.exit(1)

    p = providers[0]
    print(f"provider: {p.name} | display: {p.display_name}")
    print(f"available: {p.is_available()}")
    print(f"default model: {p.default_model()}")
    if not p.is_available():
        print("SKIP generate(): provider unavailable (key/deps missing?)")
        sys.exit(2)

    r = p.generate(prompt, aspect_ratio=aspect)
    print(f"success: {r.get('success')}")
    print(f"error_type: {r.get('error_type')}")
    print(f"error: {(r.get('error') or '')[:200]}")
    print(f"image: {r.get('image')}")
    sys.exit(0 if r.get("success") else 3)


if __name__ == "__main__":
    main()
