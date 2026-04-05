import asyncio

from django.http import JsonResponse

from agent.api.auth import require_auth
from agent.models import AgentAction
from MCP.utils.health import check_all
from MCP.servers.odoo import dashboard_stats as odoo_stats
from MCP.servers.sqlite import dashboard_stats as sqlite_stats

_MCP_STATS = {
    "odoo": odoo_stats,
    "sqlite": sqlite_stats,
}


async def dashboard(request):
    user_id, role, err = await require_auth(request)
    if err:
        return err

    loop = asyncio.get_event_loop()
    health = await loop.run_in_executor(None, check_all)

    mcps = []
    for name, healthy in health.items():
        stats = None
        if healthy and name in _MCP_STATS:
            try:
                stats = await loop.run_in_executor(None, _MCP_STATS[name])
            except Exception:
                stats = None
        mcps.append({"name": name, "healthy": healthy, "stats": stats})

    source = request.GET.get("source", "")
    date_from = request.GET.get("date_from", "")

    qs = AgentAction.objects.exclude(tool_called="")
    if role != "admin":
        qs = qs.filter(user_id=user_id)
    if source:
        qs = qs.filter(source=source)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)

    agent_calls: dict = {}
    async for action in qs.values("agent_name", "tool_called", "status"):
        tools = [t.strip() for t in action["tool_called"].split(",") if t.strip()]
        mcp_names: set[str] = set()
        for tool in tools:
            if tool.startswith("mcp_"):
                parts = tool.split("_")
                if len(parts) >= 2:
                    mcp_names.add(parts[1])
        if not mcp_names:
            mcp_names.add("other")
        for mcp_name in mcp_names:
            if mcp_name not in agent_calls:
                agent_calls[mcp_name] = {"total": 0, "agents": {}, "statuses": {}}
            agent_calls[mcp_name]["total"] += 1
            an = action["agent_name"] or "unknown"
            agent_calls[mcp_name]["agents"][an] = agent_calls[mcp_name]["agents"].get(an, 0) + 1
            st = action["status"] or "unknown"
            agent_calls[mcp_name]["statuses"][st] = agent_calls[mcp_name]["statuses"].get(st, 0) + 1

    for mcp_name in agent_calls:
        agents = [{"name": k, "count": v} for k, v in agent_calls[mcp_name]["agents"].items()]
        agents.sort(key=lambda x: -x["count"])
        agent_calls[mcp_name]["agents"] = agents
        agent_calls[mcp_name]["statuses"] = [
            {"name": k, "value": v} for k, v in agent_calls[mcp_name]["statuses"].items()
        ]

    return JsonResponse({"mcps": mcps, "agent_calls": agent_calls})


async def dashboard_calls(request):
    user_id, role, err = await require_auth(request)
    if err:
        return err

    mcp_name = request.GET.get("mcp", "")
    if not mcp_name:
        return JsonResponse({"error": "mcp param required"}, status=400)

    source = request.GET.get("source", "")
    date_from = request.GET.get("date_from", "")

    qs = AgentAction.objects.order_by("-timestamp")
    if role != "admin":
        qs = qs.filter(user_id=user_id)
    if source:
        qs = qs.filter(source=source)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)

    results = []
    async for r in qs.values(
        "id", "agent_name", "tool_called", "intent", "input_params", "output", "status", "timestamp"
    ):
        tools = [t.strip() for t in r["tool_called"].split(",") if t.strip()]
        if mcp_name == "other":
            match = not any(t.startswith("mcp_") for t in tools)
        else:
            match = any(t.startswith(f"mcp_{mcp_name}_") for t in tools)
        if match:
            results.append({
                "id": str(r["id"]),
                "agent_name": r["agent_name"],
                "tool_called": r["tool_called"],
                "intent": r["intent"],
                "input_params": r["input_params"],
                "output": r["output"],
                "status": r["status"],
                "timestamp": r["timestamp"].isoformat(),
            })

    return JsonResponse(results, safe=False)
