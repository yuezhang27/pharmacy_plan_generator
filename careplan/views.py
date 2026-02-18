"""
views.py：只负责接收请求和返回响应，不做任何业务逻辑
"""
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from . import services
from . import serializers
from .duplication_detection import DuplicationError


def index(request):
    return render(request, 'careplan/index.html')


@csrf_exempt
def generate_careplan(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = serializers.parse_generate_careplan_request(request.body)
        result = services.create_careplan(data)
        return JsonResponse(result)
    except DuplicationError as e:
        return JsonResponse({'error': e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def get_careplan(request, careplan_id):
    data, error, status_code = services.get_careplan_detail(careplan_id)
    if error is not None:
        return JsonResponse(error, status=status_code)
    return JsonResponse(data)


def careplan_status(request, careplan_id):
    data, error, status_code = services.get_careplan_status(careplan_id)
    if error is not None:
        return JsonResponse(error, status=status_code)
    return JsonResponse(data)


def download_careplan(request, careplan_id):
    content, filename, err = services.get_careplan_download(careplan_id)
    if err is not None:
        msg, status_code = err
        return HttpResponse(msg, status=status_code)
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def search_careplans(request):
    q = (request.GET.get('q') or '').strip()
    export = request.GET.get('export') == '1'

    result = services.search_careplans(q, export=export)

    if export:
        return result
    return JsonResponse(result)
