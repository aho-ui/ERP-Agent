import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from agent.api.auth import require_auth


@csrf_exempt
@require_POST
async def export(request):
    _, _, err = await require_auth(request)
    if err:
        return err
    # body = json.loads(request.body)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    fmt = body.get("format", "csv")
    title = body.get("title", "export")

    if fmt == "pdf":
        from agent.utils.pdf import generate_pdf_bytes
        data = generate_pdf_bytes(body["columns"], body["rows"], title=title)
        content_type = "application/pdf"
    elif fmt == "xlsx":
        from agent.utils.xlsx_export import generate_xlsx_bytes
        data = generate_xlsx_bytes(body["columns"], body["rows"])
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        from agent.utils.csv_export import generate_csv_bytes
        data = generate_csv_bytes(body["columns"], body["rows"])
        content_type = "text/csv"

    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{title}.{fmt}"'
    return response
