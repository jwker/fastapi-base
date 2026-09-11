"""请求日志中间件：方法、路径、状态码、耗时。"""

import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        cost_ms = (time.perf_counter() - start) * 1000
        request_id = getattr(request.state, "request_id", "-")
        logger.info(
            "{} {} {} {}ms",
            request.method,
            request.url.path,
            response.status_code,
            f"{cost_ms:.1f}",
            request_id=request_id,
        )
        return response
