"""
views.py：只负责接收请求和返回响应，不做任何业务逻辑
所有 BaseAppException 由 middleware 统一处理
"""
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from pharmacy_plan.exceptions import BlockError

from . import services
from .intake import get_adapter


def index(request):
    return render(request, "careplan/index.html")


def _get_intake_source(request) -> str:
    """根据请求确定数据来源，用于选择 Adapter"""
    return request.headers.get("X-Intake-Source", "webform").lower()


@csrf_exempt
def generate_careplan(request):
    if request.method != "POST":
        raise BlockError(
            message="Method not allowed",
            code="METHOD_NOT_ALLOWED",
            http_status=405,
        )

    source = _get_intake_source(request)
    try:
        adapter = get_adapter(source)
    except ValueError as e:
        raise BlockError(
            message=str(e),
            code="UNKNOWN_INTAKE_SOURCE",
            http_status=400,
        )
    order = adapter.process(request.body, source=source)
    data = order.to_create_careplan_dict()
    result = services.create_careplan(data)
    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})


@csrf_exempt
def intake_pharmacorp(request):
    """
    PharmaCorp Portal XML 接入点
    POST 请求体为 CareOrderRequest XML，使用 PharmaCorpAdapter 解析
    """
    if request.method != "POST":
        raise BlockError(
            message="Method not allowed",
            code="METHOD_NOT_ALLOWED",
            http_status=405,
        )
    adapter = get_adapter("pharmacorp_portal")
    order = adapter.process(request.body, source="pharmacorp_portal")
    data = order.to_create_careplan_dict()
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
