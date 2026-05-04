import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from agent.api.auth import require_auth
from agent.models import AgentTemplate
from agent.framework.nanobot.agents.registry import AgentRegistry
from agent.framework.nanobot.agents.dispatch import DispatchTool


@csrf_exempt
async def agent_templates(request):
    if request.method == "GET":
        _, _, err = await require_auth(request)
        if err:
            return err
        results = []
        async for r in AgentTemplate.objects.order_by("created_at").values(
            "id", "name", "type", "description", "instructions",
            "allowed_tools", "is_active", "is_default", "created_at",
        ):
            results.append({
                "id": str(r["id"]),
                "name": r["name"],
                "type": r["type"],
                "description": r["description"],
                "instructions": r["instructions"],
                "system_prompt": r["instructions"],
                "allowed_tools": r["allowed_tools"],
                "is_active": r["is_active"],
                "is_default": r["is_default"],
                "builtin": r["is_default"],
                "created_at": r["created_at"].isoformat(),
            })
        return JsonResponse(results, safe=False)

    if request.method == "POST":
        user_id, _, err = await require_auth(request, admin_only=True)
        if err:
            return err
        body = json.loads(request.body)
        template = await AgentTemplate.objects.acreate(
            name=body["name"],
            type=body["type"],
            description=body.get("description", ""),
            instructions=body["instructions"],
            allowed_tools=body.get("allowed_tools", []),
            created_by_id=user_id,
        )
        AgentRegistry.invalidate()
        await DispatchTool.refresh()
        return JsonResponse({"id": str(template.id), "name": template.name}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def agent_template_detail(request, template_id):
    if request.method == "GET":
        _, _, err = await require_auth(request)
        if err:
            return err
    else:
        _, _, err = await require_auth(request, admin_only=True)
        if err:
            return err

    try:
        template = await AgentTemplate.objects.aget(id=template_id)
    except AgentTemplate.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "GET":
        return JsonResponse({
            "id": str(template.id),
            "name": template.name,
            "type": template.type,
            "description": template.description,
            "instructions": template.instructions,
            "system_prompt": template.instructions,
            "allowed_tools": template.allowed_tools,
            "is_active": template.is_active,
            "is_default": template.is_default,
            "builtin": template.is_default,
            "created_at": template.created_at.isoformat(),
        })

    if request.method == "PUT":
        body = json.loads(request.body)
        template.name = body.get("name", template.name)
        template.type = body.get("type", template.type)
        template.description = body.get("description", template.description)
        template.instructions = body.get("instructions", template.instructions)
        template.allowed_tools = body.get("allowed_tools", template.allowed_tools)
        await template.asave()
        AgentRegistry.invalidate()
        await DispatchTool.refresh()
        return JsonResponse({"id": str(template.id), "name": template.name})

    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        for field in ("name", "type", "description", "instructions", "allowed_tools", "is_active"):
            if field in body:
                setattr(template, field, body[field])
        await template.asave()
        AgentRegistry.invalidate()
        await DispatchTool.refresh()
        return JsonResponse({"id": str(template.id), "name": template.name, "is_active": template.is_active})

    if request.method == "DELETE":
        await template.adelete()
        AgentRegistry.invalidate()
        await DispatchTool.refresh()
        return JsonResponse({"status": "deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


async def available_tools(request):
    _, _, err = await require_auth(request)
    if err:
        return err
    tools: set[str] = set()
    for a in await AgentRegistry.aall():
        tools.update(a["allowed_tools"])
    return JsonResponse(sorted(tools), safe=False)
