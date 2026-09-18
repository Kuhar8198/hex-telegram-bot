from abc import ABC, abstractmethod
from typing import Any


class IBunkerPort(ABC):
    """Абстрактный порт взаимодействия с хранилищем секретов и конфигураций Bunker."""

    @abstractmethod
    async def get_config_or_secret(self, key: str) -> dict[str, Any]:
        """Получение конфигурационного словаря или секрета по ключу.

        Args:
            key: Идентификатор ключа или секции конфигурации.

        Returns:
            dict[str, Any]: Словарь с параметрами конфигурации или секретами.
        """
        pass
