import os
from pathlib import Path

from nanobot.config.loader import load_config as _load_config
from nanobot.providers.litellm_provider import LiteLLMProvider

_CONFIG_PATH = Path(__file__).resolve().parent / "nanobot.config"


_ENV_KEY_MAP = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def load():
    config = _load_config(_CONFIG_PATH)
    config.agents.defaults.workspace = str(_CONFIG_PATH.parent / "workspace")
    provider_name = config.get_provider_name()
    if provider_name and (env_var := _ENV_KEY_MAP.get(provider_name)):
        getattr(config.providers, provider_name).api_key = os.getenv(env_var, "")
    provider_cfg = config.get_provider()
    provider = LiteLLMProvider(
        api_key=provider_cfg.api_key if provider_cfg else None,
        api_base=provider_cfg.api_base if provider_cfg else None,
        default_model=config.agents.defaults.model,
    )
    return config, provider
