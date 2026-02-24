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
        _record_exception_metric(exception)
        return JsonResponse(
            exception.to_dict(),
            status=exception.http_status,
            json_dumps_params={"ensure_ascii": False},
        )

    # 兼容 DRF ValidationError
    try:
        from rest_framework.exceptions import ValidationError as DRFValidationError
        if isinstance(exception, DRFValidationError):
            _record_validation_error()
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


def _record_validation_error():
    """记录 DRF ValidationError（避免循环导入）"""
    try:
        from careplan.metrics import VALIDATION_ERROR
        VALIDATION_ERROR.inc()
    except ImportError:
        pass


def _record_exception_metric(exception):
    """记录异常指标（避免循环导入）"""
    try:
        from careplan.metrics import (
            VALIDATION_ERROR,
            BLOCK_ERROR,
            DUPLICATION_BLOCK,
            DUPLICATION_WARNING,
        )
        from .exceptions import ValidationError, BlockError, WarningException

        if isinstance(exception, ValidationError):
            VALIDATION_ERROR.inc()
        elif isinstance(exception, BlockError):
            code = getattr(exception, "code", "UNKNOWN")
            BLOCK_ERROR.labels(code=code).inc()
            if code in ("PROVIDER_NPI_NAME_MISMATCH", "ORDER_SAME_DAY_DUPLICATE"):
                DUPLICATION_BLOCK.labels(code=code).inc()
        elif isinstance(exception, WarningException):
            DUPLICATION_WARNING.labels(code=getattr(exception, "code", "UNKNOWN")).inc()
    except ImportError:
        pass
