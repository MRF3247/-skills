"""MiniMax image generation backend (image-01).

Known-good example of a Hermes image_gen provider plugin. Deployed as
~/.hermes/plugins/image_gen/minimax/__init__.py (with plugin.yaml below).
Copy this file and adapt for other providers.

plugin.yaml for this plugin:

    name: minimax
    version: 1.0.0
    description: "MiniMax image generation backend (image-01)."
    author: user
    kind: backend
    requires_env:
      - MINIMAX_API_KEY

Enable via:
    hermes config set plugins.enabled '["image_gen/minimax"]'
    hermes config set image_gen.provider minimax
    hermes config set image_gen.model image-01
The "not a recognized config key" warnings from `hermes config set` are benign.
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

API_MODEL = "image-01"
DEFAULT_MODEL = "image-01"

# Hermes unified aspect -> provider-specific aspect_ratio values.
_ASPECT_MAP = {
    "landscape": "16:9",
    "square": "1:1",
    "portrait": "9:16",
}

_ENDPOINTS = {
    "intl": "https://api.minimax.io/v1/image_generation",
    "cn": "https://api.minimaxi.com/v1/image_generation",
}

_MODELS: Dict[str, Dict[str, Any]] = {
    "image-01": {
        "display": "MiniMax Image-01",
        "speed": "~10-20s",
        "strengths": "Text-to-image, character reference support, batch up to 9",
        "price": "pay-per-image",
    },
}


def _load_minimax_config() -> Dict[str, Any]:
    """Read ``image_gen.minimax`` from config.yaml (returns {} on failure)."""
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else None
        if isinstance(section, dict):
            mm = section.get("minimax")
            if isinstance(mm, dict):
                return mm
        return {}
    except Exception as exc:
        logger.debug("Could not load image_gen.minimax config: %s", exc)
        return {}


def _pick_credentials() -> tuple[str, str]:
    """Return ``(api_key, endpoint_url)``.

    China endpoint wins when a CN key is present; otherwise the
    international key/endpoint. A config-level ``base_url`` overrides the
    default endpoint.
    """
    cfg = _load_minimax_config()
    base_url = cfg.get("base_url")

    cn_key = get_secret("MINIMAX_CN_API_KEY")
    if cn_key:
        return cn_key, base_url or _ENDPOINTS["cn"]

    intl_key = get_secret("MINIMAX_API_KEY")
    if intl_key:
        return intl_key, base_url or _ENDPOINTS["intl"]

    return "", ""


class MiniMaxImageGenProvider(ImageGenProvider):
    """MiniMax ``/v1/image_generation`` backend — image-01."""

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def display_name(self) -> str:
        return "MiniMax"

    def is_available(self) -> bool:
        key, _ = _pick_credentials()
        if not key:
            return False
        try:
            import requests  # noqa: F401
        except ImportError:
            return False
        return True

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": model_id,
                "display": meta["display"],
                "speed": meta["speed"],
                "strengths": meta["strengths"],
                "price": meta["price"],
            }
            for model_id, meta in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "MiniMax",
            "badge": "paid",
            "tag": "image-01 text-to-image — international & China endpoints",
            "env_vars": [
                {
                    "key": "MINIMAX_API_KEY",
                    "prompt": "MiniMax API key (international, https://www.minimax.io)",
                    "url": "https://platform.minimax.io/user-center/basic-information/interface-key",
                },
                {
                    "key": "MINIMAX_CN_API_KEY",
                    "prompt": "MiniMax API key (mainland China, https://platform.minimaxi.com)",
                    "url": "https://platform.minimaxi.com/user-center/basic-information/interface-key",
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
                error="Prompt is required and must be a non-empty string",
                error_type="invalid_argument",
                provider="minimax",
                aspect_ratio=aspect,
            )

        if image_url or reference_image_urls:
            return error_response(
                error=(
                    "MiniMax image-01 backend currently supports "
                    "text-to-image only; image editing is not wired up yet."
                ),
                error_type="unsupported",
                provider="minimax",
                model=DEFAULT_MODEL,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        api_key, endpoint = _pick_credentials()
        if not api_key:
            return error_response(
                error=(
                    "MiniMax API key not set. Run `hermes tools` → Image "
                    "Generation → MiniMax to configure, or set "
                    "MINIMAX_API_KEY / MINIMAX_CN_API_KEY in ~/.hermes/.env"
                ),
                error_type="auth_required",
                provider="minimax",
                aspect_ratio=aspect,
            )

        try:
            import requests
        except ImportError:
            return error_response(
                error="requests package not installed (pip install requests)",
                error_type="missing_dependency",
                provider="minimax",
                aspect_ratio=aspect,
            )

        mm_aspect = _ASPECT_MAP.get(aspect, "16:9")
        payload: Dict[str, Any] = {
            "model": API_MODEL,
            "prompt": prompt,
            "aspect_ratio": mm_aspect,
            "response_format": "url",
            "n": 1,
            "prompt_optimizer": True,
        }

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as exc:
            logger.debug("MiniMax image generation failed", exc_info=True)
            return error_response(
                error=f"MiniMax image generation failed: {exc}",
                error_type="api_error",
                provider="minimax",
                model=DEFAULT_MODEL,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        base_resp = body.get("base_resp") or {}
        status_code = base_resp.get("status_code")
        if status_code not in (0, "0", None):
            return error_response(
                error=(
                    "MiniMax API error: "
                    f"{base_resp.get('status_msg') or base_resp.get('status_code')}"
                ),
                error_type="api_error",
                provider="minimax",
                model=DEFAULT_MODEL,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        data = body.get("data") or {}
        image_urls = data.get("image_urls") or []
        if not image_urls:
            return error_response(
                error="MiniMax returned no image URLs",
                error_type="empty_response",
                provider="minimax",
                model=DEFAULT_MODEL,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        url = image_urls[0]
        try:
            saved_path = save_url_image(url, prefix="minimax_image01")
        except Exception as exc:
            logger.warning(
                "MiniMax image URL %s could not be cached (%s); falling back to bare URL.",
                url,
                exc,
            )
            image_ref = url
        else:
            image_ref = str(saved_path)

        return success_response(
            image=image_ref,
            model=DEFAULT_MODEL,
            prompt=prompt,
            aspect_ratio=aspect,
            provider="minimax",
            modality="text",
            extra={"endpoint": endpoint, "n": 1},
        )


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    """Plugin entry point — wire ``MiniMaxImageGenProvider`` into the registry."""
    ctx.register_image_gen_provider(MiniMaxImageGenProvider())
