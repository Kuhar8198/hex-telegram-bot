"""Адаптер для взаимодействия с Bunker API (хранилище секретов и конфигурации).

Слой: Adapters (Outbound)
Имплементирует: IBunkerPort
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.application.ports.bunker_port import IBunkerPort

logger = logging.getLogger(__name__)


class BunkerAdapter(IBunkerPort):
    """Асинхронный адаптер сервиса Bunker."""

    def __init__(
        self,
        base_url: str,
        token: str = "",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url: str = base_url.rstrip("/")
        self._token: str = token
        self._client: httpx.AsyncClient = http_client or httpx.AsyncClient(timeout=15.0)

    async def get_config_or_secret(self, key: str) -> dict[str, Any]:
        """Получает параметры конфигурации или секреты по ключу."""
        endpoint = f"{self._base_url}/api/v1/secrets/{key}"
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            logger.debug("Запрос к Bunker API: endpoint=%s", endpoint)
            response = await self._client.get(endpoint, headers=headers)
            if response.status_code == 404:
                logger.warning("Ключ '%s' не найден в Bunker. Возврат пустой конфигурации.", key)
                return {}
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"value": data}
        except httpx.ConnectError:
            logger.warning("Bunker недоступен по адресу %s. Возврат резервного значения.", self._base_url)
            return {}
        except Exception as exc:
            logger.warning("Ошибка при чтении из Bunker (%s): %s. Используются дефолтные параметры.", key, exc)
            return {}
