from django.http import HttpResponse


def store(data: bytes, content_type: str) -> str:
    from agent.models import BotMedia
    obj = BotMedia.objects.create(data=data, content_type=content_type)
    return str(obj.key)


def serve(_request, key: str):
    from agent.models import BotMedia
    try:
        obj = BotMedia.objects.get(key=key)
    except BotMedia.DoesNotExist:
        return HttpResponse(status=404)
    data, content_type = bytes(obj.data), obj.content_type
    obj.delete()
    return HttpResponse(data, content_type=content_type)
