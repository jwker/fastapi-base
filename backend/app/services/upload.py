"""文件上传：校验、存储与 URL 生成（磁盘存储，UUID 文件名防冲突/路径穿越）。"""

import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.response import AppError


def _validate(filename: str, size: int) -> str:
    """校验文件并返回规范化扩展名（小写、不含点）。"""
    if size <= 0:
        raise AppError(400, "文件不能为空")
    if size > settings.UPLOAD_MAX_SIZE:
        mb = settings.UPLOAD_MAX_SIZE // (1024 * 1024)
        raise AppError(400, f"文件大小不能超过 {mb}MB")
    ext = Path(filename).suffix.lower().lstrip(".")
    if not ext or ext not in settings.upload_allowed_ext_set:
        raise AppError(400, "不支持的文件类型")
    return ext


def save_upload(data: bytes, filename: str) -> str:
    """保存文件到 uploads/YYYYMM/UUID.ext，返回可访问 URL 路径（/uploads/...）。

    同步磁盘 IO；调用方应为同步端点（FastAPI 自动放线程池执行）。
    """
    ext = _validate(filename, len(data))
    subdir = datetime.now().strftime("%Y%m")
    base = Path(settings.UPLOAD_DIR)
    rel_dir = base / subdir
    rel_dir.mkdir(parents=True, exist_ok=True)
    rel_path = rel_dir / f"{uuid.uuid4().hex}.{ext}"
    rel_path.write_bytes(data)
    # URL 基于 UPLOAD_DIR 目录名构造（相对/绝对路径均正确，生产容器内是绝对路径）
    return f"/{base.name}/{subdir}/{rel_path.name}"


def remove_upload(url: str) -> None:
    """根据存储 URL 删除磁盘文件（不存在则静默跳过）。

    用于：删除文件记录时清理磁盘；写库失败时回滚已落盘文件。
    文件系统非权威：文件可能已被手动清理，删除失败不抛错（尽力而为）。
    """
    base = Path(settings.UPLOAD_DIR)
    rel = url.removeprefix(f"/{base.name}/")
    target = base / rel
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass
