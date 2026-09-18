"""Адаптер для внешнего поискового API Tavily.

Слой: Adapters (Outbound)
Имплементирует: ISearchPort
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.application.ports.search_port import ISearchPort

logger = logging.getLogger(__name__)


class TavilyAdapter(ISearchPort):
    """Асинхронный адаптер Tavily Search API."""

    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key: str = api_key
        self._client: httpx.AsyncClient = http_client or httpx.AsyncClient(timeout=15.0)

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Выполняет поиск через официальный Tavily REST API."""
        if not self._api_key:
            logger.debug("TAVILY_API_KEY не сконфигурирован. Пропуск.")
            return []

        endpoint = "https://api.tavily.com/search"
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 5,
        }

        try:
            logger.debug("Отправка запроса в Tavily API: query=%.40s...", query)
            response = await self._client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])

            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                }
                for item in results
                if isinstance(item, dict)
            ]
        except Exception as exc:
            logger.warning("Сбой при выполнении запроса к Tavily API: %s", exc)
            return []
