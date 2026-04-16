# import base64
# import csv
# import io

# from asgiref.sync import sync_to_async
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt

# from agent.api.auth import require_auth


# def _extract_pdf(data: bytes) -> str:
#     from pypdf import PdfReader
#     reader = PdfReader(io.BytesIO(data))
#     return "\n".join(page.extract_text() or "" for page in reader.pages)


# def _extract_docx(data: bytes) -> str:
#     from docx import Document
#     doc = Document(io.BytesIO(data))
#     return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# def _extract_xlsx(data: bytes) -> str:
#     from openpyxl import load_workbook
#     wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
#     rows = []
#     for sheet in wb.worksheets:
#         for row in sheet.iter_rows(values_only=True):
#             rows.append(",".join("" if v is None else str(v) for v in row))
#     return "\n".join(rows)


# def _extract_csv(data: bytes) -> str:
#     text = data.decode("utf-8", errors="replace")
#     reader = csv.reader(io.StringIO(text))
#     return "\n".join(",".join(row) for row in reader)


# def _extract_image(data: bytes, content_type: str) -> str:
#     import litellm
#     from agent.framework.nanobot.config.loader import load
#     config, _ = load()
#     model = config.agents.defaults.model
#     b64 = base64.b64encode(data).decode()
#     response = litellm.completion(
#         model=model,
#         messages=[{
#             "role": "user",
#             "content": [
#                 {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{b64}"}},
#                 {"type": "text", "text": "Extract all data, text, and relevant information from this image. Be thorough and structured."},
#             ],
#         }],
#     )
#     return response.choices[0].message.content


# @csrf_exempt
# async def upload(request):
#     _, _, err = await require_auth(request)
#     if err:
#         return err

#     if request.method != "POST":
#         return JsonResponse({"error": "POST required"}, status=405)

#     file = request.FILES.get("file")
#     if not file:
#         return JsonResponse({"error": "file is required"}, status=400)

#     content_type = file.content_type or ""
#     filename = file.name or ""
#     data = file.read()

#     try:
#         if content_type == "application/pdf" or filename.endswith(".pdf"):
#             content = await sync_to_async(_extract_pdf)(data)
#         elif (
#             content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#             or filename.endswith(".docx")
#         ):
#             content = await sync_to_async(_extract_docx)(data)
#         elif (
#             content_type in (
#                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                 "application/vnd.ms-excel",
#             )
#             or filename.endswith(".xlsx")
#         ):
#             content = await sync_to_async(_extract_xlsx)(data)
#         elif content_type in ("text/csv", "text/plain") or filename.endswith(".csv"):
#             content = _extract_csv(data)
#         elif content_type.startswith("image/"):
#             content = await sync_to_async(_extract_image)(data, content_type)
#         else:
#             return JsonResponse({"error": f"Unsupported file type: {content_type}"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": f"Failed to process file: {e}"}, status=500)

#     return JsonResponse({"content": content, "filename": filename})
