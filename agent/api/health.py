from django.http import JsonResponse

from agent.api.auth import require_auth
from agent.utils.mcp import health, dashboard_stats, _health_cache


async def mcp(request):
    _, _, err = await require_auth(request)
    if err:
        return err

    if request.method == "POST":
        # lazy: DispatchTool import here avoids circular import at module load
        from agent.framework.nanobot.agents.dispatch import DispatchTool
        statuses = await health()
        await DispatchTool.refresh()
        results = [{"name": n, "status": "ok" if ok else "error"} for n, ok in statuses.items()]
        return JsonResponse(results, safe=False)

    detail = request.GET.get("detail", "status")
    statuses = _health_cache

    results = []
    for name, ok in statuses.items():
        entry = {"name": name, "status": "ok" if ok else "error"}
        if detail == "full":
            entry["stats"] = await dashboard_stats(name) if ok else None
        results.append(entry)
    return JsonResponse(results, safe=False)
