"""Custom image_gen provider scaffold — copy and adapt per API.

Place at ~/.hermes/plugins/image_gen/<name>/__init__.py alongside a
plugin.yaml with: name, kind: backend, requires_env: [YOUR_KEY].

Enable with:  hermes plugins enable image_gen/<name>
Configure:    hermes config set image_gen.provider <name>
              hermes config set image_gen.model <model>
Key in:       ~/.hermes/.env  (e.g. YOUR_API_KEY=sk-...)

Changes take effect on a NEW session. Test standalone with the Hermes venv
python (see launcher shebang) and load .env into os.environ first.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent.secret_scope import get_secret
from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    save_url_image,
    success_response,
)

logger = logging.getLogger(__name__)

API_MODEL = "your-model-id"
DEFAULT_MODEL = API_MODEL

# Hermes unified aspect -> provider's aspect values.
_ASPECT_MAP = {"landscape": "16:9", "square": "1:1", "portrait": "9:16"}

_ENDPOINT = "https://api.example.com/v1/image_generation"


class ExampleImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "example"

    @property
    def display_name(self) -> str:
        return "Example"

    def is_available(self) -> bool:
        return bool(get_secret("YOUR_API_KEY"))

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": API_MODEL, "display": API_MODEL, "price": "varies"}]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Example",
            "badge": "paid",
            "tag": "text-to-image",
            "env_vars": [
                {
                    "key": "YOUR_API_KEY",
                    "prompt": "API key",
                    "url": "https://api.example.com/keys",
                },
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {"modalities": ["text"], "max_reference_images": 0}

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)
        if not prompt:
            return error_response(
                error="Prompt is required",
                error_type="invalid_argument",
                provider="example",
                aspect_ratio=aspect,
            )

        api_key = get_secret("YOUR_API_KEY")
        if not api_key:
            return error_response(
                error="YOUR_API_KEY not set (see hermes tools → Image Generation)",
                error_type="auth_required",
                provider="example",
                aspect_ratio=aspect,
            )

        import requests

        payload: Dict[str, Any] = {
            "model": API_MODEL,
            "prompt": prompt,
            "aspect_ratio": _ASPECT_MAP.get(aspect, "16:9"),
            "response_format": "url",
            "n": 1,
        }
        try:
            resp = requests.post(
                _ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as exc:
            logger.debug("generation failed", exc_info=True)
            return error_response(
                error=f"generation failed: {exc}",
                error_type="api_error",
                provider="example",
                model=DEFAULT_MODEL,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        # ADAPT: extract the image URL per provider response shape.
        url = (body.get("data") or {}).get("image_urls", [None])[0]
        if not url:
            return error_response(
                error="no image in response",
                error_type="empty_response",
                provider="example",
                model=DEFAULT_MODEL,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        try:
            saved = save_url_image(url, prefix="example")
            image_ref = str(saved)
        except Exception as exc:
            logger.warning("could not cache URL (%s); using bare URL", exc)
            image_ref = url

        return success_response(
            image=image_ref,
            model=DEFAULT_MODEL,
            prompt=prompt,
            aspect_ratio=aspect,
            provider="example",
            modality="text",
        )


def register(ctx) -> None:
    ctx.register_image_gen_provider(ExampleImageGenProvider())
