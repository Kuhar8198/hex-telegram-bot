from abc import ABC, abstractmethod
from typing import Any


class IVectorStorePort(ABC):
    """Абстрактный порт взаимодействия с векторным хранилищем (Qdrant)."""

    @abstractmethod
    async def search_similar(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        """Асинхронный семантический поиск релевантных фрагментов по запросу.

        Args:
            query: Текстовый запрос для поиска.
            limit: Максимальное количество фрагментов.

        Returns:
            list[dict[str, Any]]: Список найденных фрагментов с метаданными.
        """
        pass

    @abstractmethod
    async def save_context(self, text: str, metadata: dict[str, Any] | None = None) -> bool:
        """Сохранение текстового фрагмента и метаданных в векторное хранилище.

        Args:
            text: Текст для сохранения.
            metadata: Опциональные метаданные (user_id, chat_id, timestamp).

        Returns:
            bool: Успешность операции.
        """
        pass
