import csv
import io

from django.http import HttpResponse, JsonResponse

from agent.api.auth import require_auth
from agent.models import AgentAction


async def actions(request):
    user_id, role, err = await require_auth(request)
    if err:
        return err

    status = request.GET.get("status", "")
    mcp_name = request.GET.get("mcp", "")
    source = request.GET.get("source", "")
    date_from = request.GET.get("date_from", "")
    fmt = request.GET.get("format", "json")

    qs = AgentAction.objects.order_by("-timestamp")
    if role != "admin":
        qs = qs.filter(user_id=user_id)
    if status:
        qs = qs.filter(status=status)
    if source:
        qs = qs.filter(source=source)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "timestamp", "agent_name", "intent", "tool_called", "status"])
        async for r in qs.values("id", "timestamp", "agent_name", "intent", "tool_called", "status"):
            writer.writerow([r["id"], r["timestamp"].isoformat(), r["agent_name"], r["intent"], r["tool_called"], r["status"]])
        response = HttpResponse(buf.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="actions.csv"'
        return response

    results = []
    async for r in qs.values(
        "id", "run_id", "source", "intent", "agent_name", "tool_called",
        "input_params", "output", "status", "timestamp", "artifacts"
    ):
        if mcp_name:
            tools = [t.strip() for t in r["tool_called"].split(",") if t.strip()]
            if mcp_name == "other":
                if any(t.startswith("mcp_") for t in tools):
                    continue
            else:
                if not any(t.startswith(f"mcp_{mcp_name}_") for t in tools):
                    continue
        results.append({
            "id": str(r["id"]),
            "run_id": str(r["run_id"]) if r["run_id"] else None,
            "source": r["source"],
            "intent": r["intent"],
            "agent_name": r["agent_name"],
            "tool_called": r["tool_called"],
            "input_params": r["input_params"],
            "output": r["output"],
            "status": r["status"],
            "timestamp": r["timestamp"].isoformat(),
            "artifacts": r["artifacts"],
        })
    return JsonResponse(results, safe=False)


async def action_detail(request, action_id):
    _, _, err = await require_auth(request)
    if err:
        return err
    try:
        action = await AgentAction.objects.aget(id=action_id)
    except AgentAction.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({
        "status": action.status,
        "output": action.output,
        "artifacts": action.artifacts,
    })


async def dashboard(request):
    user_id, role, err = await require_auth(request)
    if err:
        return err

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

    return JsonResponse({"agent_calls": agent_calls})


