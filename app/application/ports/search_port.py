from abc import ABC, abstractmethod
from typing import Any


class ISearchPort(ABC):
    """Абстрактный порт взаимодействия с поисковыми движками (SearXNG / Tavily)."""

    @abstractmethod
    async def search(self, query: str) -> list[dict[str, Any]]:
        """Асинхронный поиск релевантного контекста в веб-источниках.

        Args:
            query: Поисковый запрос.

        Returns:
            list[dict[str, Any]]: Список найденных результатов со сниппетами и метаданными.
        """
        pass
