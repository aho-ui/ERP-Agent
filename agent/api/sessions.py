import json
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from agent.api.auth import require_auth
from agent.models import ChatSession, ChatMessage


@csrf_exempt
async def sessions(request):
    user_id, _, err = await require_auth(request)
    if err:
        return err

    if request.method == "GET":
        status = request.GET.get("status", "open")
        is_closed = status == "closed"
        order = "-updated_at" if is_closed else "created_at"
        rows = ChatSession.objects.filter(user_id=user_id, is_closed=is_closed).order_by(order).values(
            "id", "label"
        )
        results = [
            {"id": str(r["id"]), "label": r["label"]}
            async for r in rows
        ]
        return JsonResponse(results, safe=False)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        session_id = body.get("id") or str(uuid.uuid4())
        label = body.get("label", "New Chat")
        session, _ = await ChatSession.objects.aupdate_or_create(
            id=session_id,
            defaults={"user_id": user_id, "label": label, "is_closed": False},
        )
        return JsonResponse({"id": str(session.id), "label": session.label})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def update_session(request, session_id):
    user_id, _, err = await require_auth(request)
    if err:
        return err

    if request.method == "DELETE":
        await ChatSession.objects.filter(id=session_id, user_id=user_id).adelete()
        return JsonResponse({"status": "deleted"})

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    updated = {}
    if "label" in body:
        updated["label"] = body["label"]
    if "is_closed" in body:
        updated["is_closed"] = body["is_closed"]

    if updated:
        await ChatSession.objects.filter(id=session_id, user_id=user_id).aupdate(**updated)
    return JsonResponse({"status": "ok"})


async def session_messages(request, session_id):
    _, _, err = await require_auth(request)
    if err:
        return err
    rows = ChatMessage.objects.filter(session_id=session_id).order_by("timestamp").values(
        "id", "role", "content", "artifacts", "steps", "timestamp"
    )
    results = [
        {
            "id": str(r["id"]),
            "role": r["role"],
            "content": r["content"],
            "artifacts": r["artifacts"],
            "steps": r["steps"],
            "timestamp": r["timestamp"].isoformat(),
        }
        async for r in rows
    ]
    return JsonResponse(results, safe=False)
