"""操作审计日志 API：查询 / 导出（CSV 流式）/ 导出后删除。"""

import csv
import io
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import AppError, success
from app.schemas.operation_log import OperationLogOut, OperationLogPage
from app.services import audit as audit_service

router = APIRouter(prefix="/audit-logs", tags=["操作日志"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

# ruff B008 对 datetime + Query(None) 误报，统一用 Annotated + Query() 写法
TimeQuery = Annotated[datetime | None, Query()]
# 删除边界：end_time 必填（= 导出时刻，防误删导出后新产生的日志）
RequiredTimeQuery = Annotated[datetime, Query()]

CSV_HEADERS = [
    "ID",
    "操作人",
    "模块",
    "动作",
    "方法",
    "路径",
    "状态码",
    "IP",
    "操作时间",
    "请求参数",
]


async def _csv_stream(db: AsyncSession, **filters) -> AsyncGenerator[str, None]:
    """逐行生成 CSV（UTF-8 带 BOM，Excel 打开中文不乱码）。"""
    yield "\ufeff"
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADERS)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    async for log in audit_service.iter_export_logs(db, **filters):
        writer.writerow(
            [
                log.id,
                log.username or "（匿名）",
                log.module,
                log.action,
                log.method,
                log.path,
                log.response_status,
                log.ip,
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                log.request_body,
            ]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


@router.get("")
async def list_audit_logs(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("audit:read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    username: str | None = Query(None),
    module: str | None = Query(None),
    action: str | None = Query(None),
    status: int | None = Query(None),
    start_time: TimeQuery = None,
    end_time: TimeQuery = None,
):
    total, rows = await audit_service.list_operation_logs(
        db,
        page,
        page_size,
        username=username,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    return success(
        OperationLogPage(total=total, items=[OperationLogOut.model_validate(r) for r in rows])
    )


@router.get("/export")
async def export_audit_logs(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("audit:read"))],
    username: str | None = Query(None),
    module: str | None = Query(None),
    action: str | None = Query(None),
    status: int | None = Query(None),
    start_time: TimeQuery = None,
    end_time: TimeQuery = None,
):
    """按当前筛选条件导出 CSV（流式，不落盘）。"""
    filters = dict(
        username=username,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    total = await audit_service.count_export_logs(db, **filters)
    if total > audit_service.MAX_EXPORT_ROWS:
        raise AppError(400, f"数据量过大（{total} 条），请缩小筛选范围后导出")
    filename = f"audit-logs-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        _csv_stream(db, **filters),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("")
async def delete_audit_logs(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("audit:delete"))],
    end_time: RequiredTimeQuery,
    username: str | None = Query(None),
    module: str | None = Query(None),
    action: str | None = Query(None),
    status: int | None = Query(None),
    start_time: TimeQuery = None,
):
    """删除已导出的日志（范围=导出范围，end_time=导出时刻，防误删新数据）。"""
    deleted = await audit_service.delete_operation_logs(
        db,
        username=username,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    return success({"deleted": deleted}, f"已删除 {deleted} 条")
