"""Адаптер локального метапоисковика SearXNG.

Слой: Adapters (Outbound)
Имплементирует: ISearchPort
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.application.ports.search_port import ISearchPort

logger = logging.getLogger(__name__)


class SearxngAdapter(ISearchPort):
    """Асинхронный адаптер поиска SearXNG."""

    def __init__(
        self,
        base_url: str = "http://searxng:8080",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url: str = base_url.rstrip("/")
        self._client: httpx.AsyncClient = http_client or httpx.AsyncClient(timeout=10.0)

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Выполняет веб-поиск через SearXNG JSON API."""
        endpoint = f"{self._base_url}/search"
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "language": "auto",
        }

        try:
            logger.debug("Запрос в SearXNG: query=%.40s...", query)
            response = await self._client.get(endpoint, params=params)
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
            logger.warning("Сбой при выполнении поиска в SearXNG: %s", exc)
            return []
