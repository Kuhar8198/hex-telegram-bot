"""Композитный адаптер поиска с поддержкой Fallback.

Слой: Adapters (Outbound)
Имплементирует: ISearchPort
Паттерн: Fallback / Chain of Responsibility
"""

from __future__ import annotations

import logging
from typing import Any

from app.application.ports.search_port import ISearchPort

logger = logging.getLogger(__name__)


class CompositeSearchAdapter(ISearchPort):
    """Комбинированный поиск: сначала SearXNG, при сбое или пустом ответе — Tavily."""

    def __init__(
        self,
        primary_adapter: ISearchPort,
        fallback_adapter: ISearchPort | None = None,
    ) -> None:
        self._primary: ISearchPort = primary_adapter
        self._fallback: ISearchPort | None = fallback_adapter

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Выполняет поиск с автоматическим переключением на резервный источник."""
        try:
            logger.debug("Попытка поиска через Primary Search Adapter (SearXNG)...")
            results = await self._primary.search(query)
            if results:
                return results
            logger.info("Primary Search Adapter вернул пустой список. Переключение на Fallback...")
        except Exception as exc:
            logger.warning("Ошибка Primary Search Adapter: %s. Переключение на Fallback...", exc)

        if self._fallback is not None:
            try:
                logger.debug("Попытка поиска через Fallback Search Adapter (Tavily)...")
                return await self._fallback.search(query)
            except Exception as exc:
                logger.warning("Ошибка Fallback Search Adapter: %s", exc)

        return []
