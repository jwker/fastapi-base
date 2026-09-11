"""操作审计中间件：自动拦截写操作，脱敏后落库。

实现为纯 ASGI 中间件（而非 BaseHTTPMiddleware）：
BaseHTTPMiddleware 消费请求体后，下游读不到 body（Starlette 已知坑）；
纯 ASGI 通过旁路缓存 body 并原样转发，对业务完全透明。
"""

import json

from loguru import logger
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.auth import decode_token
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services import audit as audit_service

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
EXCLUDE_PATHS = {"/docs", "/redoc", "/metrics", "/health", "/openapi.json", "/favicon.ico"}
LOGIN_PATH_SUFFIX = "/auth/login"


class AuditMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._should_audit(scope):
            await self.app(scope, receive, send)
            return

        body_chunks: list[bytes] = []

        async def receive_wrapper() -> Message:
            message = await receive()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b""))
            return message

        response_status = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_status["code"] = message["status"]
            await send(message)

        # 请求进入时解析用户：此时 token 尚未被登出黑名单，能正确解析（响应后再解析会失败）
        user_id, username = await self._resolve_user(scope)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            # 审计不阻塞业务：写入失败仅服务端留痕，不影响响应
            try:
                await self._record(
                    scope, b"".join(body_chunks), response_status["code"], user_id, username
                )
            except Exception:
                logger.error("审计日志写入失败", exc_info=True)

    def _should_audit(self, scope: Scope) -> bool:
        return (
            scope["type"] == "http"
            and scope["method"] in WRITE_METHODS
            and scope["path"] not in EXCLUDE_PATHS
        )

    async def _record(
        self,
        scope: Scope,
        body: bytes,
        status: int,
        user_id: int | None,
        username: str,
    ) -> None:
        # 登录无 token：从请求体提取登录用户名（业界登录日志记登录名，user_id 留空）
        if user_id is None and scope["path"].endswith(LOGIN_PATH_SUFFIX):
            username = self._extract_login_username(body) or username
        request = Request(scope)
        body_text = audit_service.sanitize_body(body)
        async with AsyncSessionLocal() as db:
            await audit_service.record_operation(
                db,
                user_id=user_id,
                username=username,
                method=request.method,
                path=request.url.path,
                request_body=body_text,
                response_status=status,
                ip=self._client_ip(scope),
                user_agent=request.headers.get("user-agent", "")[:255],
            )

    @staticmethod
    def _extract_login_username(body: bytes) -> str:
        try:
            data = json.loads(body.decode("utf-8", errors="replace"))
            if isinstance(data, dict):
                username = data.get("username")
                return str(username) if isinstance(username, str) else ""
        except (ValueError, TypeError):
            pass
        return ""

    async def _resolve_user(self, scope: Scope) -> tuple[int | None, str]:
        """从 Authorization 头解析操作人；无效 token 视为匿名。"""
        auth = self._headers(scope).get("authorization", "")
        if not auth.startswith("Bearer "):
            return None, ""
        token = auth[len("Bearer ") :].strip()
        try:
            payload = await decode_token(token)
            if payload.get("type") != "access":
                return None, ""
            user_id = int(payload["sub"])
            async with AsyncSessionLocal() as db:
                user = await db.get(User, user_id)
            return (user_id, user.username) if user else (user_id, "")
        except Exception:
            return None, ""

    @staticmethod
    def _headers(scope: Scope) -> dict[str, str]:
        return {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }

    def _client_ip(self, scope: Scope) -> str:
        headers = self._headers(scope)
        forwarded = headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real = headers.get("x-real-ip")
        if real:
            return real.strip()
        client = scope.get("client")
        return client[0] if client else ""
