import asyncio

from django.http import JsonResponse


async def mcp_health(_request):
    from MCP.utils.health import check_all
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, check_all)
    return JsonResponse(
        [{"name": name, "status": "ok" if ok else "error"} for name, ok in results.items()],
        safe=False,
    )
