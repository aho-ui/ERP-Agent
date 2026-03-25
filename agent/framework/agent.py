def get_agent(name: str):
    import importlib
    try:
        return importlib.import_module(f"agent.framework.{name}.main")
    except ModuleNotFoundError:
        raise ValueError(f"Unknown provider: {name}")
