from django.http import JsonResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken as JWTToken


def _parse_token(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, "viewer"
    try:
        token = JWTToken(auth[7:])
        return token.get("user_id"), token.get("role", "viewer")
    except TokenError:
        return None, "viewer"


async def _parse_api_key(request):
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        return None, None
    from asgiref.sync import sync_to_async
    from django.utils import timezone
    from users.models import User
    try:
        user = await sync_to_async(User.objects.get)(api_key=api_key, is_active=True)
        if user.api_key_expires_at and user.api_key_expires_at < timezone.now():
            return None, None
        return str(user.id), user.role
    except Exception:
        return None, None


async def require_auth(request, admin_only=False):
    user_id, role = _parse_token(request)
    if not user_id:
        user_id, role = await _parse_api_key(request)
    if not user_id:
        return None, None, JsonResponse({"error": "Unauthorized"}, status=401)
    if admin_only and role != "admin":
        return None, None, JsonResponse({"error": "Forbidden"}, status=403)
    return user_id, role, None
