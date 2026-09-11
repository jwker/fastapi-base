"""loguru 初始化：开发彩色控制台；生产 JSON 文件轮转（保留 30 天）。"""

import json
import logging
import sys
from datetime import datetime

from loguru import logger

from app.core.config import settings


class JsonFormatter:
    def __call__(self, record: dict) -> str:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "message": record["message"],
            "request_id": record.get("extra", {}).get("request_id"),
        }
        return json.dumps(payload, ensure_ascii=False) + "\n"


def setup_logging() -> None:
    logger.remove()

    if settings.is_prod:
        logger.add(
            "logs/app.log",
            format=JsonFormatter(),
            level="INFO",
            rotation="20 MB",
            retention="30 days",
            compression="gz",
            encoding="utf-8",
        )
        # 抑制 uvicorn 默认日志，统一走 loguru
        logging.getLogger("uvicorn").handlers.clear()
    else:
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
            ),
            level="DEBUG",
            colorize=True,
        )
