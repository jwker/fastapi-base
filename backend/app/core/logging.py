"""loguru 初始化：开发彩色控制台；生产 JSON 文件轮转（保留最近 30 份 gz）。"""

import gzip
import json
import logging
import os
import sys
from datetime import datetime

from loguru import logger

from app.core.config import settings


class JsonFileSink:
    """loguru 自定义 sink：JSON 行写文件，按大小轮转并 gzip 保留最近 N 份。

    为什么不用 format 参数：loguru 的 format 模板机制会把 callable 返回值
    当作字符串模板再次执行 format_map，JSON 含花括号必然触发 KeyError
    （0.7.3 emit 实现如此），因此 JSON 输出必须走自定义 sink。
    """

    def __init__(
        self,
        path: str,
        *,
        max_bytes: int = 20 * 1024 * 1024,
        backups: int = 30,
    ):
        self.path = path
        self.max_bytes = max_bytes
        self.backups = backups
        self._fh = open(path, "a", encoding="utf-8")

    def write(self, message) -> None:
        record = message.record
        payload = {
            "timestamp": datetime.now().isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "message": record["message"],
            "request_id": record.get("extra", {}).get("request_id"),
        }
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        if self._fh.tell() + len(line) > self.max_bytes:
            self._rotate()
        self._fh.write(line)
        self._fh.flush()

    def _rotate(self) -> None:
        """当前文件超过阈值 → 关闭、gzip 备份、重开新文件、清理旧备份。"""
        self._fh.close()
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = f"{self.path}.{stamp}.gz"
        with open(self.path, "rb") as f_in, gzip.open(backup, "wb") as f_out:
            f_out.write(f_in.read())
        os.remove(self.path)
        self._fh = open(self.path, "a", encoding="utf-8")

        dirname, basename = os.path.dirname(self.path), os.path.basename(self.path)
        backups = sorted(p for p in os.listdir(dirname) if p.startswith(basename + "."))
        for old in backups[: max(0, len(backups) - self.backups)]:
            os.remove(os.path.join(dirname, old))

    def stop(self) -> None:
        self._fh.close()


def setup_logging() -> None:
    logger.remove()

    if settings.is_prod:
        logger.add(
            JsonFileSink("logs/app.log"),
            level="INFO",
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
