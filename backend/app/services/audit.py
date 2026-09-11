"""操作审计日志：脱敏、记录与查询。"""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.operation_log import OperationLog

# 请求参数截断长度（若依同款，防大 body 撑爆表）
MAX_BODY_LEN = 2000
# 单次导出上限（防内存/响应滥用）
MAX_EXPORT_ROWS = 100_000
# 导出分批游标大小
EXPORT_BATCH_SIZE = 1000

# 全量脱敏关键词：字段名包含以下词 → 替换为占位符
FULL_MASK_KEYWORDS = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "apikey",
    "credential",
    "sms_code",
    "captcha_code",
)
# 部分脱敏关键词：手机号/邮箱类，保留首尾
PARTIAL_MASK_KEYWORDS = ("phone", "mobile", "email")
MASK_PLACEHOLDER = "******"

# 路径前缀 → 业务模块
MODULE_MAP: dict[str, str] = {
    "/users": "用户管理",
    "/roles": "角色管理",
    "/permissions": "权限管理",
    "/menus": "菜单管理",
    "/auth": "认证",
    "/files": "文件管理",
    "/audit-logs": "操作日志",
}


def _mask_value(key: str, value: object) -> object:
    """按字段名对值脱敏：全量或部分。"""
    if not isinstance(value, (str, int, float, bool)) or value in ("", None):
        return value
    key_lower = key.lower()
    if any(kw in key_lower for kw in FULL_MASK_KEYWORDS):
        return MASK_PLACEHOLDER
    if any(kw in key_lower for kw in PARTIAL_MASK_KEYWORDS):
        text = str(value)
        if "@" in text:  # 邮箱：保留首字符 + ***@域名
            local, _, domain = text.partition("@")
            return f"{local[:1]}***@{domain}" if local else MASK_PLACEHOLDER
        if len(text) >= 7:  # 手机号：138****0000
            return f"{text[:3]}****{text[-4:]}"
        return MASK_PLACEHOLDER
    return value


def _sanitize(data: object) -> object:
    if isinstance(data, dict):
        return {str(k): _sanitize(_mask_value(str(k), v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize(item) for item in data]
    return data


def sanitize_body(body: bytes | str) -> str:
    """请求体脱敏 + 截断。非 JSON 或解析失败时原样截断。"""
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
    try:
        data = json.loads(text)
        text = json.dumps(_sanitize(data), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        pass
    return text[:MAX_BODY_LEN]


def infer_module(path: str) -> str:
    # 剥离 API 前缀（如 /api/v1/users → /users）再匹配
    prefix = settings.API_V1_PREFIX
    p = path[len(prefix) :] if prefix and path.startswith(prefix) else path
    for key, name in MODULE_MAP.items():
        if p.startswith(key):
            return name
    return "未分类"


def infer_action(method: str, path: str) -> str:
    if path.endswith("/auth/login"):
        return "login"
    if path.endswith("/auth/logout"):
        return "logout"
    return {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}.get(
        method, "other"
    )


async def record_operation(
    db: AsyncSession,
    *,
    user_id: int | None,
    username: str,
    method: str,
    path: str,
    request_body: str,
    response_status: int,
    ip: str,
    user_agent: str,
) -> None:
    """写入一条审计日志。调用方负责 try/except 降级（审计不阻塞业务）。"""
    log = OperationLog(
        user_id=user_id,
        username=username,
        module=infer_module(path),
        action=infer_action(method, path),
        method=method,
        path=path,
        request_body=request_body,
        response_status=response_status,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(log)
    await db.commit()


def _apply_filters(
    stmt,
    *,
    username: str | None = None,
    module: str | None = None,
    action: str | None = None,
    status: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    """公共筛选条件（查询/导出/删除共用，保证范围一致）。"""
    if username:
        stmt = stmt.where(OperationLog.username.contains(username))
    if module:
        stmt = stmt.where(OperationLog.module == module)
    if action:
        stmt = stmt.where(OperationLog.action == action)
    if status is not None:
        stmt = stmt.where(OperationLog.response_status == status)
    if start_time:
        stmt = stmt.where(OperationLog.created_at >= start_time)
    if end_time:
        stmt = stmt.where(OperationLog.created_at <= end_time)
    return stmt


async def list_operation_logs(
    db: AsyncSession,
    page: int,
    page_size: int,
    *,
    username: str | None = None,
    module: str | None = None,
    action: str | None = None,
    status: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[int, list[OperationLog]]:
    stmt = _apply_filters(
        select(OperationLog),
        username=username,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(OperationLog.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return total, rows


async def count_export_logs(
    db: AsyncSession,
    *,
    username: str | None = None,
    module: str | None = None,
    action: str | None = None,
    status: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> int:
    """导出前统计命中条数（用于超上限拦截）。"""
    stmt = _apply_filters(
        select(OperationLog),
        username=username,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    return (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()


async def iter_export_logs(
    db: AsyncSession,
    *,
    username: str | None = None,
    module: str | None = None,
    action: str | None = None,
    status: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    """流式导出：按 id 游标分批读取（避免深分页），逐条 yield。"""
    base = _apply_filters(
        select(OperationLog),
        username=username,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    last_id = 0
    while True:
        rows = (
            (
                await db.execute(
                    base.where(OperationLog.id > last_id)
                    .order_by(OperationLog.id)
                    .limit(EXPORT_BATCH_SIZE)
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            break
        for row in rows:
            yield row
        last_id = rows[-1].id


async def delete_operation_logs(
    db: AsyncSession,
    *,
    username: str | None = None,
    module: str | None = None,
    action: str | None = None,
    status: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime,
) -> int:
    """按导出范围删除（含 created_at <= end_time 边界，end_time 必填=导出时刻）。

    删除范围与导出完全一致（同筛选 + 同一 end_time），保证"删的一定已导出"。
    """
    from sqlalchemy import delete

    stmt = _apply_filters(
        delete(OperationLog),
        username=username,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount
