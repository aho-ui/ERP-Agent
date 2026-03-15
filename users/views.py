import json
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.tokens import AccessToken


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
