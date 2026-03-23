import json
from django.contrib.auth import authenticate, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


def _parse_token(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, "viewer"
    try:
        token = AccessToken(auth[7:])
        return token.get("user_id"), token.get("role", "viewer")
    except TokenError:
        return None, "viewer"


def _require_admin(request):
    user_id, role = _parse_token(request)
    if not user_id:
        return None, JsonResponse({"error": "Unauthorized"}, status=401)
    if role != "admin":
        return None, JsonResponse({"error": "Forbidden"}, status=403)
    return user_id, None


@csrf_exempt
@require_POST
def login(request):
    body = json.loads(request.body)
    user = authenticate(username=body.get("username"), password=body.get("password"))
    if not user:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    token = AccessToken.for_user(user)
    token["role"] = user.role
    return JsonResponse({"access": str(token), "role": user.role})


@csrf_exempt
def users_list(request):
    _, err = _require_admin(request)
    if err:
        return err

    if request.method == "GET":
        qs = User.objects.order_by("date_joined").values(
            "id", "username", "email", "role", "is_active", "date_joined"
        )
        results = [
            {
                "id": str(u["id"]),
                "username": u["username"],
                "email": u["email"],
                "role": u["role"],
                "is_active": u["is_active"],
                "created_at": u["date_joined"].isoformat(),
            }
            for u in qs
        ]
        return JsonResponse(results, safe=False)

    if request.method == "POST":
        body = json.loads(request.body)
        if User.objects.filter(username=body["username"]).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)
        user = User.objects.create_user(
            username=body["username"],
            email=body.get("email", ""),
            password=body["password"],
        )
        user.role = body.get("role", User.Role.VIEWER)
        user.save()
        return JsonResponse({"id": str(user.id), "username": user.username}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def user_detail(request, user_id):
    _, err = _require_admin(request)
    if err:
        return err

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "PUT":
        body = json.loads(request.body)
        if "role" in body:
            user.role = body["role"]
        if "is_active" in body:
            user.is_active = body["is_active"]
        user.save()
        return JsonResponse({"id": str(user.id), "role": user.role, "is_active": user.is_active})

    if request.method == "DELETE":
        user.delete()
        return JsonResponse({"status": "deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)
