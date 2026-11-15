"""Skeleton ImageGenProvider for a custom Hermes image_gen backend.

Copy to ~/.hermes/plugins/image_gen/<name>/__init__.py, adapt the class
body, and add a plugin.yaml alongside it (see SKILL.md step 1).
Run tests with the Hermes venv python, not system python3.
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

# Hermes unified aspect -> provider aspect values.
_ASPECT_MAP = {
    "landscape": "16:9",
    "square": "1:1",
    "portrait": "9:16",
}


class YourProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "yourname"  # matches image_gen.provider in config.yaml

    @property
    def display_name(self) -> str:
        return "Your Provider"

    def is_available(self) -> bool:
        if not get_secret("YOUR_API_KEY"):
            return False
        try:
            import requests  # noqa: F401
        except ImportError:
            return False
        return True

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": API_MODEL, "display": API_MODEL, "speed": "~10-20s",
                 "strengths": "...", "price": "..."}]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "paid",
            "tag": "one-line description",
            "env_vars": [
                {"key": "YOUR_API_KEY",
                 "prompt": "API key",
                 "url": "https://provider.example.com/keys"},
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
                error="Prompt is required and must be a non-empty string",
                error_type="invalid_argument",
                provider=self.name,
                aspect_ratio=aspect,
            )

        api_key = get_secret("YOUR_API_KEY")
        if not api_key:
            return error_response(
                error="API key not set — run `hermes tools` to configure.",
                error_type="auth_required",
                provider=self.name,
                aspect_ratio=aspect,
            )

        # TODO: call the provider API, then:
        #   saved = save_url_image(url, prefix="provider_model")   # ephemeral URLs
        #   return success_response(image=str(saved), model=DEFAULT_MODEL,
        #                           prompt=prompt, aspect_ratio=aspect,
        #                           provider=self.name, modality="text")
        return error_response(
            error="generate() not implemented yet",
            error_type="provider_error",
            provider=self.name,
            aspect_ratio=aspect,
        )


def register(ctx) -> None:
    """Plugin entry point — wire the provider into the registry."""
    ctx.register_image_gen_provider(YourProvider())
