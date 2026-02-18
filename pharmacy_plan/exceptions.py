"""
统一错误处理：BaseAppException 及子类
所有异常格式：type, code, message, detail, http_status
"""


class BaseAppException(Exception):
    """基类：统一错误格式"""
    type = "error"
    code = "UNKNOWN"
    message = "Unknown error"
    http_status = 400

    def __init__(self, message=None, code=None, detail=None, http_status=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.detail = detail if detail is not None else {}
        if http_status is not None:
            self.http_status = http_status

    def to_dict(self):
        return {
            "success": False,
            "type": self.type,
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


class ValidationError(BaseAppException):
    """验证错误：输入格式不对，由 serializer 检查"""
    type = "validation"
    code = "VALIDATION_ERROR"
    message = "Validation failed"
    http_status = 400


class BlockError(BaseAppException):
    """业务阻止：业务规则不允许"""
    type = "block"
    code = "BLOCK"
    message = "Operation blocked"
    http_status = 409


class WarningException(BaseAppException):
    """业务警告：可能有问题，允许用户确认后继续"""
    type = "warning"
    code = "WARNING"
    message = "Please confirm to continue"
    http_status = 200
