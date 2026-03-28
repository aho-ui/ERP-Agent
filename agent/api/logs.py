import csv
import io

from django.http import HttpResponse, JsonResponse

from agent.api.auth import require_auth
from agent.models import AgentAction


async def export_logs(request):
    _, _, err = await require_auth(request, admin_only=True)
    if err:
        return err
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "timestamp", "agent_name", "intent", "tool_called", "status"])
    async for r in AgentAction.objects.order_by("-timestamp").values("id", "timestamp", "agent_name", "intent", "tool_called", "status"):
        writer.writerow([r["id"], r["timestamp"].isoformat(), r["agent_name"], r["intent"], r["tool_called"], r["status"]])
    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
    return response


async def agent_logs(request):
    _, _, err = await require_auth(request, admin_only=True)
    if err:
        return err
    rows = AgentAction.objects.order_by("-timestamp").values(
        "id", "intent", "agent_name", "tool_called", "status", "timestamp", "output", "artifacts"
    )
    results = [
        {
            "id": str(r["id"]),
            "intent": r["intent"],
            "agent_name": r["agent_name"],
            "tool_called": r["tool_called"],
            "status": r["status"],
            "timestamp": r["timestamp"].isoformat(),
            "output": r["output"],
            "artifacts": r["artifacts"],
        }
        async for r in rows
    ]
    return JsonResponse(results, safe=False)
