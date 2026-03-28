import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from agent.api.auth import require_auth
from agent.models import AgentTemplate


def _get_agents():
    from agent.framework.nanobot.agents.sub_agents_odoo import AGENTS as _ODOO
    from agent.framework.nanobot.agents.sub_agents_demo import AGENTS as _DEMO
    return _ODOO + _DEMO


@csrf_exempt
async def agent_templates(request):
    AGENTS = _get_agents()

    if request.method == "GET":
        _, _, err = await require_auth(request)
        if err:
            return err
        db_templates = {}
        async for r in AgentTemplate.objects.order_by("created_at").values("id", "name", "type", "instructions", "allowed_tools", "is_active", "created_at"):
            db_templates[r["name"]] = r
        results = []
        for name, r in db_templates.items():
            if r["type"] != "builtin_stub":
                results.append({"id": str(r["id"]), "name": r["name"], "type": r["type"], "instructions": r["instructions"], "allowed_tools": r["allowed_tools"], "is_active": r["is_active"], "created_at": r["created_at"].isoformat(), "builtin": False})
        for a in AGENTS:
            if a["name"] not in db_templates:
                results.append({"id": None, "name": a["name"], "type": "builtin", "description": a.get("description", ""), "system_prompt": a.get("system_prompt", ""), "allowed_tools": a["allowed_tools"], "builtin": True, "is_active": True})
            elif db_templates[a["name"]]["type"] == "builtin_stub":
                results.append({"id": str(db_templates[a["name"]]["id"]), "name": a["name"], "type": "builtin", "description": a.get("description", ""), "system_prompt": a.get("system_prompt", ""), "allowed_tools": a["allowed_tools"], "builtin": True, "is_active": False})
        return JsonResponse(results, safe=False)

    if request.method == "POST":
        user_id, _, err = await require_auth(request, admin_only=True)
        if err:
            return err
        body = json.loads(request.body)
        template = await AgentTemplate.objects.acreate(
            name=body["name"],
            type=body["type"],
            instructions=body["instructions"],
            allowed_tools=body.get("allowed_tools", []),
            created_by_id=user_id,
        )
        return JsonResponse({"id": str(template.id), "name": template.name}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def agent_template_detail(request, template_id):
    _, _, err = await require_auth(request, admin_only=True)
    if err:
        return err

    try:
        template = await AgentTemplate.objects.aget(id=template_id)
    except AgentTemplate.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "PUT":
        body = json.loads(request.body)
        template.name = body.get("name", template.name)
        template.type = body.get("type", template.type)
        template.instructions = body.get("instructions", template.instructions)
        template.allowed_tools = body.get("allowed_tools", template.allowed_tools)
        await template.asave()
        return JsonResponse({"id": str(template.id), "name": template.name})

    if request.method == "DELETE":
        await template.adelete()
        return JsonResponse({"status": "deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def toggle_agent(request):
    _, _, err = await require_auth(request, admin_only=True)
    if err:
        return err
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = body.get("name", "").strip()
    enabled = body.get("enabled", True)
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    AGENTS = _get_agents()
    is_builtin = any(a["name"] == name for a in AGENTS)

    if is_builtin:
        if not enabled:
            await AgentTemplate.objects.aupdate_or_create(
                name=name,
                defaults={"type": "builtin_stub", "instructions": "", "allowed_tools": [], "is_active": False},
            )
        else:
            await AgentTemplate.objects.filter(name=name, type="builtin_stub").adelete()
    else:
        await AgentTemplate.objects.filter(name=name).aupdate(is_active=enabled)

    return JsonResponse({"name": name, "is_active": enabled})


async def available_tools(request):
    _, _, err = await require_auth(request)
    if err:
        return err
    AGENTS = _get_agents()
    tools: set[str] = set()
    for a in AGENTS:
        tools.update(a["allowed_tools"])
    return JsonResponse(sorted(tools), safe=False)
