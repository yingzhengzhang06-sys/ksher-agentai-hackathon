"""
集成器抽象基类

所有外部数据集成器（爬虫、API 等）都应继承此基类。
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseIntegrator(ABC):
    """
    集成器抽象基类。

    子类必须实现：
        - fetch() → dict: 获取数据
        - parse() → list: 解析数据为统一格式
    """

    name: str = "base"
    enabled: bool = True

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._last_error: str = ""

    @abstractmethod
    def fetch(self) -> Any:
        """
        获取原始数据（HTTP请求、爬虫、API调用等）。

        Returns:
            原始数据（HTML/JSON/列表等）
        """
        pass

    @abstractmethod
    def parse(self, raw_data: Any) -> list[dict]:
        """
        解析原始数据为统一格式。

        Returns:
            标准化数据列表
        """
        pass

    def run(self) -> dict:
        """
        执行完整的集成流程：fetch → parse。

        Returns:
            {
                "success": bool,
                "count": int,
                "data": list,
                "error": str
            }
        """
        try:
            raw = self.fetch()
            parsed = self.parse(raw)
            return {
                "success": True,
                "count": len(parsed),
                "data": parsed,
                "error": "",
            }
        except Exception as e:
            self._last_error = str(e)
            logger.exception(f"[{self.name}] 集成失败: {e}")
            return {
                "success": False,
                "count": 0,
                "data": [],
                "error": str(e),
            }

    def get_last_error(self) -> str:
        """获取上次错误信息"""
        return self._last_error

    def is_enabled(self) -> bool:
        """是否启用"""
        return self.enabled and self.config.get("enabled", True)
