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
_TOKENS_RE = re.compile(
    r"^Tokens: (\d+) prompt / (\d+) completion / \d+ total(?: \| model: (\S+))?\s*$"
)

_MODEL_PRICING = {
    # (input $/Mtok, output $/Mtok) — public list prices as of 2026-06
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-4-turbo": (10.00, 30.00),
    "anthropic/claude-3-5-sonnet-20241022": (3.00, 15.00),
    "anthropic/claude-3-haiku-20240307": (0.25, 1.25),
    "groq/llama-3.1-70b-versatile": (0.59, 0.79),
    "groq/qwen/qwen3-32b": (0.29, 0.39),
    "deepseek/deepseek-chat": (0.27, 1.10),
}

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

_KNOWN_MCPS = ["odoo", "sqlite"]
_DISABLED_MCPS_PARAM = "erp_agent.disabled_mcps"


def _safe_int(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


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


def _mask(p):
    if not p:
        return None
    return {
        "id": p["id"],
        "name": p["name"],
        "model": p["model"],
        "api_key_set": bool(p.get("api_key")),
    }


def _compute_cost(prompt, completion, model):
    rates = _MODEL_PRICING.get(model)
    if not rates:
        return 0.0
    in_rate, out_rate = rates
    return round((prompt * in_rate + completion * out_rate) / 1_000_000, 6)


def _parse_tokens_from_steps(steps_raw):
    try:
        steps = json.loads(steps_raw or "[]")
    except Exception:
        return 0, 0, "", 0.0
    for s in steps:
        if not isinstance(s, str):
            continue
        m = _TOKENS_RE.match(s.strip())
        if m:
            prompt = int(m.group(1))
            completion = int(m.group(2))
            model = m.group(3) or ""
            return prompt, completion, model, _compute_cost(prompt, completion, model)
    return 0, 0, "", 0.0


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
    raw = env.user.erp_agent_disabled_defaults or "[]"
    try:
        data = json.loads(raw)
    except Exception:
        data = []
    return data if isinstance(data, list) else []


def _save_disabled_defaults(env, names):
    env.user.sudo().write({
        "erp_agent_disabled_defaults": json.dumps(sorted(set(names))),
    })


def _disabled_mcps(env):
    raw = env["ir.config_parameter"].sudo().get_param(_DISABLED_MCPS_PARAM, "[]")
    try:
        data = json.loads(raw or "[]")
    except Exception:
        data = []
    return data if isinstance(data, list) else []


def _save_disabled_mcps(env, names):
    env["ir.config_parameter"].sudo().set_param(
        _DISABLED_MCPS_PARAM, json.dumps(sorted(set(names)))
    )


def _enabled_mcps(env):
    disabled = set(_disabled_mcps(env))
    return [m for m in _KNOWN_MCPS if m not in disabled]


def _available_tool_names():
    from backend import agent_loop as AL
    loop = AL._agent_loop
    if loop is None:
        return []
    return sorted(n for n in loop.tools.tool_names if n.startswith("mcp_"))
