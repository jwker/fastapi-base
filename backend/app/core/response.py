"""统一响应格式与业务异常。"""

from typing import Any

from fastapi.responses import JSONResponse
from starlette.requests import Request


class AppError(Exception):
    """业务异常基类。"""

    def __init__(self, code: int = 400, message: str = "业务错误", data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


def success(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


def error(code: int, message: str, data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}


def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.code, content=error(exc.code, exc.message, exc.data))
