import asyncio
import json
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from agent.framework.nanobot import get_agent_loop


@csrf_exempt
@require_POST
async def chat(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = body.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)

    session_key = body.get("session_key", "api:default")
    queue = asyncio.Queue()

    async def on_progress(content):
        await queue.put({"type": "progress", "content": content})

    async def run_agent():
        agent_loop = get_agent_loop()
        response = await agent_loop.process_direct(
            content=message,
            session_key=session_key,
            on_progress=on_progress,
        )
        await queue.put({"type": "response", "content": response})
        await queue.put(None)

    async def event_stream():
        task = asyncio.create_task(run_agent())
        while True:
            event = await queue.get()
            if event is None:
                yield "data: [DONE]\n\n"
                break
            yield f"data: {json.dumps(event)}\n\n"
        await task

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
