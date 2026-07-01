import os
import tempfile
from pathlib import Path

from nanobot.config.loader import load_config as _load_config
from nanobot.providers.litellm_provider import LiteLLMProvider

_CONFIG_PATH = Path(__file__).resolve().parent / "nanobot.config"


def _resolve_workspace() -> Path:
    candidate = _CONFIG_PATH.parent / "workspace"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "erp_agent_workspace"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


_PROVIDER_ENV_VARS = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def load():
    config = _load_config(_CONFIG_PATH)
    config.agents.defaults.workspace = str(_resolve_workspace())

    provider_name = config.get_provider_name()
    api_key = os.getenv(_PROVIDER_ENV_VARS[provider_name], "") if provider_name in _PROVIDER_ENV_VARS else ""
    if provider_name and provider_name in _PROVIDER_ENV_VARS:
        provider_cfg = getattr(config.providers, provider_name, None)
        if provider_cfg is not None:
            provider_cfg.api_key = api_key

    provider_cfg = config.get_provider()
    provider = LiteLLMProvider(
        api_key=provider_cfg.api_key if provider_cfg else api_key,
        api_base=provider_cfg.api_base if provider_cfg else None,
        default_model=config.agents.defaults.model,
    )
    return config, provider
