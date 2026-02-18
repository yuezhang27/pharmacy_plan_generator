"""
views.py：只负责接收请求和返回响应，不做任何业务逻辑
所有 BaseAppException 由 middleware 统一处理
"""
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from pharmacy_plan.exceptions import BlockError

from . import services
from . import serializers


def index(request):
    return render(request, "careplan/index.html")


@csrf_exempt
def generate_careplan(request):
    if request.method != "POST":
        raise BlockError(
            message="Method not allowed",
            code="METHOD_NOT_ALLOWED",
            http_status=405,
        )

    data = serializers.parse_generate_careplan_request(request.body)
    result = services.create_careplan(data)
    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})


@csrf_exempt
def get_careplan(request, careplan_id):
    result = services.get_careplan_detail(careplan_id)
    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})


def careplan_status(request, careplan_id):
    result = services.get_careplan_status(careplan_id)
    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})


def download_careplan(request, careplan_id):
    content, filename = services.get_careplan_download(careplan_id)
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def search_careplans(request):
    q = (request.GET.get("q") or "").strip()
    export = request.GET.get("export") == "1"

    result = services.search_careplans(q, export=export)

    if export:
        return result
    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})
