def get_agent(name: str):
    if name == "groq":
        from agent.framework import groq
        return groq
    elif name == "openai":
        from agent.framework import nanobot
        return nanobot
    raise ValueError(f"Unknown provider: {name}")
