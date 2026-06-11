import json
import re
import socket
import sys
from pathlib import Path

_ADDON_DIR = Path(__file__).resolve().parents[1]   # erp_agent/

# regexes used to parse the daemon's progress lines stored on each message
_TOOL_RE = re.compile(r"-> (mcp_\w+)\(")
_AGENT_RE = re.compile(r"^dispatch\(['\"]([^'\"]+)['\"]\)$")
_CALL_LINE_RE = re.compile(r"^\[([^\]]+)\] -> (mcp_\w+)\((.*)\)\s*$")
_RESULT_LINE_RE = re.compile(r"^\[([^\]]+)\] <- (mcp_\w+):\s*(.*)$")

MODEL_PRESETS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "openai/gpt-4-turbo",
    "anthropic/claude-3-5-sonnet-20241022",
    "anthropic/claude-3-haiku-20240307",
    "groq/llama-3.1-70b-versatile",
    "groq/qwen/qwen3-32b",
    "deepseek/deepseek-chat",
]

_DISABLED_PARAM = "erp_agent.disabled_default_agents"


def _ensure_path():
    # so the bundled `backend.*` modules import from this addon
    if str(_ADDON_DIR) not in sys.path:
        sys.path.insert(0, str(_ADDON_DIR))


def _is_running():
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=1):
            return True
    except OSError:
        return False


def _apply_runtime_config(profile_id):
    try:
        from backend.agent_loop import apply_runtime_config
        apply_runtime_config(profile_id)
    except Exception:
        pass


def _mask(p):
    if not p:
        return None
    return {
        "id": p["id"],
        "name": p["name"],
        "model": p["model"],
        "api_key_set": bool(p.get("api_key")),
    }


def _parse_steps(steps_raw):
    try:
        steps = json.loads(steps_raw or "[]")
    except Exception:
        return [], ""
    tools, agent = [], ""
    for s in steps:
        if not isinstance(s, str):
            continue
        mt = _TOOL_RE.search(s)
        if mt:
            tools.append(mt.group(1))
        if not agent:
            ma = _AGENT_RE.match(s.strip())
            if ma:
                agent = ma.group(1)
    return tools, agent


def _agent_dict(r):
    try:
        tools = json.loads(r.allowed_tools or "[]")
    except Exception:
        tools = []
    return {
        "id": r.id,
        "name": r.name or "",
        "description": r.description or "",
        "system_prompt": r.system_prompt or "",
        "allowed_tools": tools,
    }


def _disabled_defaults(env):
    raw = env["ir.config_parameter"].sudo().get_param(_DISABLED_PARAM, "[]")
    try:
        data = json.loads(raw or "[]")
    except Exception:
        data = []
    return data if isinstance(data, list) else []


def _save_disabled_defaults(env, names):
    env["ir.config_parameter"].sudo().set_param(_DISABLED_PARAM, json.dumps(sorted(set(names))))


def _warm_agents(env):
    from backend.agents.registry import AgentRegistry
    # NO sudo: record rule scopes this to the requesting user's agents.
    # active customs only (default search hides inactive)
    recs = env["erp_agent.agent"].search([])
    AgentRegistry.set_state(
        custom=[
            {
                "name": d["name"],
                "description": d["description"],
                "system_prompt": d["system_prompt"],
                "allowed_tools": d["allowed_tools"],
            }
            for d in (_agent_dict(r) for r in recs)
        ],
        disabled_defaults=_disabled_defaults(env),
    )
    return recs


def _available_tool_names():
    from backend import agent_loop as AL
    loop = AL._agent_loop
    if loop is None:
        return []
    return sorted(n for n in loop.tools.tool_names if n.startswith("mcp_"))
