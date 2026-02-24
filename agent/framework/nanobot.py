from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.config.loader import load_config

_agent_loop: AgentLoop | None = None


def get_agent_loop() -> AgentLoop:
    global _agent_loop
    if _agent_loop is None:
        config = load_config()
        provider_cfg = config.get_provider()
        provider = LiteLLMProvider(
            api_key=provider_cfg.api_key if provider_cfg else None,
            api_base=provider_cfg.api_base if provider_cfg else None,
            default_model=config.agents.defaults.model,
        )
        bus = MessageBus()
        workspace = config.workspace_path
        workspace.mkdir(parents=True, exist_ok=True)

        _agent_loop = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=workspace,
        )
    return _agent_loop
