"""
中间件：捕获 View 中抛出的 BaseAppException，交由 exception_handler 处理
"""
from .exception_handler import app_exception_handler


class AppExceptionMiddleware:
    """
    将 BaseAppException 转为统一 JSON 响应
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        response = app_exception_handler(request, exception)
        if response is not None:
            return response
        return None
