import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from agent.api.auth import require_auth


@csrf_exempt
@require_POST
async def po_document(request):
    _, _, err = await require_auth(request)
    if err:
        return err
    data = json.loads(request.body)
    from agent.utils.documents.po import generate_po_pdf
    pdf_bytes = generate_po_pdf(data)
    title = data.get("po_number", "po")
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{title}.pdf"'
    return response
