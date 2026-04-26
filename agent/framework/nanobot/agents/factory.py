from pathlib import Path

import yaml

_TEMPLATES_DIR = Path(__file__).parent / "templates"

with (_TEMPLATES_DIR / "formats.yaml").open("r", encoding="utf-8") as f:
    _FORMATS = yaml.safe_load(f)


# def load_agents(filename: str) -> list[dict]:
#     path = _TEMPLATES_DIR / filename
#     with path.open("r", encoding="utf-8") as f:
#         data = yaml.safe_load(f)
#
#     agents = []
#     for entry in data.get("agents", []):
#         suffix = "".join("\n" + _FORMATS[k] for k in entry.get("formats", []))
#         agents.append({
#             "name": entry["name"],
#             "description": entry["description"],
#             "system_prompt": entry["prompt"] + suffix,
#             "allowed_tools": entry["allowed_tools"],
#         })
#     return agents


# def load_agents(filenames: list[str]) -> list[dict]:
#     agents = []
#     for filename in filenames:
#         path = _TEMPLATES_DIR / filename
#         with path.open("r", encoding="utf-8") as f:
#             data = yaml.safe_load(f)
#         for entry in data.get("agents", []):
#             suffix = "".join("\n" + _FORMATS[k] for k in entry.get("formats", []))
#             agents.append({
#                 "name": entry["name"],
#                 "description": entry["description"],
#                 "system_prompt": entry["prompt"] + suffix,
#                 "allowed_tools": entry["allowed_tools"],
#             })
#     return agents


def seed_from_yaml(filenames: list[str]) -> int:
    # lazy: apps.py imports this module at top-level, so importing models here would trigger AppRegistryNotReady
    from agent.models import AgentTemplate

    created = 0
    for filename in filenames:
        path = _TEMPLATES_DIR / filename
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for entry in data.get("agents", []):
            suffix = "".join("\n" + _FORMATS[k] for k in entry.get("formats", []))
            _, was_created = AgentTemplate.objects.get_or_create(
                name=entry["name"],
                defaults={
                    "type": "transaction",
                    "description": entry["description"],
                    "instructions": entry["prompt"] + suffix,
                    "allowed_tools": entry["allowed_tools"],
                    "tool_config": entry.get("tool_config", {}),
                    "requires_write_access": entry.get("requires_write_access", False),
                    "is_active": True,
                    "is_default": True,
                },
            )
            if was_created:
                created += 1
    return created
