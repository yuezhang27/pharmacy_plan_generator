"""
统一异常处理：将 BaseAppException 及 DRF ValidationError 转为统一 JSON 格式
"""
from django.http import JsonResponse

from .exceptions import BaseAppException


def app_exception_handler(request, exception):
    """
    处理 BaseAppException 及其子类，转为统一 JSON
    兼容 DRF ValidationError（当 rest_framework 存在时）
    """
    if isinstance(exception, BaseAppException):
        return JsonResponse(
            exception.to_dict(),
            status=exception.http_status,
            json_dumps_params={"ensure_ascii": False},
        )

    # 兼容 DRF ValidationError
    try:
        from rest_framework.exceptions import ValidationError as DRFValidationError
        if isinstance(exception, DRFValidationError):
            detail = exception.detail
            if isinstance(detail, dict):
                pass
            elif isinstance(detail, list):
                detail = {"errors": detail}
            else:
                detail = {"message": str(detail)}
            return JsonResponse(
                {
                    "success": False,
                    "type": "validation",
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed",
                    "detail": detail,
                },
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
    except ImportError:
        pass

    return None
