import json


async def stream_queue(queue, task, on_event=None):
    while True:
        event = await queue.get()
        if event is None:
            yield "data: [DONE]\n\n"
            break
        if on_event:
            result = await on_event(event)
            if result is not None:
                yield result
                continue
        yield f"data: {json.dumps(event)}\n\n"
    await task
