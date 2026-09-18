"""Адаптер для взаимодействия с векторной базой данных Qdrant.

Слой: Adapters (Outbound)
Имплементирует: IVectorStorePort
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.application.ports.vector_port import IVectorStorePort

logger = logging.getLogger(__name__)


class QdrantAdapter(IVectorStorePort):
    """Асинхронный REST-адаптер для работы с Qdrant."""

    def __init__(
        self,
        base_url: str = "http://qdrant:6333",
        collection_name: str = "bot_context",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url: str = base_url.rstrip("/")
        self._collection: str = collection_name
        self._client: httpx.AsyncClient = http_client or httpx.AsyncClient(timeout=10.0)

    async def search_similar(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        """Поиск похожих векторных записей по коллекции."""
        endpoint = f"{self._base_url}/collections/{self._collection}/points/scroll"
        payload = {
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        }

        try:
            response = await self._client.post(endpoint, json=payload)
            if response.status_code == 404:
                logger.debug("Коллекция '%s' пока не создана в Qdrant.", self._collection)
                return []
            response.raise_for_status()
            data = response.json()
            points = data.get("result", {}).get("points", [])

            results: list[dict[str, Any]] = []
            for pt in points:
                payload_data = pt.get("payload", {})
                if "text" in payload_data:
                    results.append({
                        "id": pt.get("id"),
                        "text": payload_data["text"],
                        "metadata": payload_data.get("metadata", {}),
                    })
            return results
        except Exception as exc:
            logger.warning("Сбой при обращении к Qdrant search_similar: %s", exc)
            return []

    async def save_context(self, text: str, metadata: dict[str, Any] | None = None) -> bool:
        """Сохранение контекста в векторную БД."""
        endpoint = f"{self._base_url}/collections/{self._collection}/points"
        import uuid
        point_id = str(uuid.uuid4())
        # При отсутствии внешнего embedding-сервиса используем плейсхолдер 4D для инициализации
        payload = {
            "points": [
                {
                    "id": point_id,
                    "vector": [0.1, 0.2, 0.3, 0.4],
                    "payload": {
                        "text": text,
                        "metadata": metadata or {},
                    },
                }
            ]
        }

        try:
            response = await self._client.put(endpoint, json=payload)
            return response.is_success
        except Exception as exc:
            logger.warning("Не удалось сохранить контекст в Qdrant: %s", exc)
            return False
