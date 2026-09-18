"""Адаптер для Hugging Face Inference API с поддержкой Cold-Start Retry и Exponential Backoff.

Слой: Adapters (Outbound)
Имплементирует: IHuggingFacePort
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.application.ports.hf_port import IHuggingFacePort

logger = logging.getLogger(__name__)


class HfAdapter(IHuggingFacePort):
    """Асинхронный адаптер Hugging Face Inference API с обработкой 503 Service Unavailable."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "mistralai/Mistral-7B-Instruct-v0.3",
        http_client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
    ) -> None:
        self._api_key: str = api_key
        self._default_model: str = default_model
        self._client: httpx.AsyncClient = http_client or httpx.AsyncClient(timeout=60.0)
        self._max_retries: int = max_retries

    async def generate_response(self, prompt: str, model_id: str | None = None) -> str:
        """Отправляет промпт в HF Inference API с обработкой 'холодного старта'."""
        target_model = model_id or self._default_model
        endpoint = f"https://api-inference.huggingface.co/models/{target_model}"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.7,
                "return_full_text": False,
            },
        }

        logger.debug("Отправка запроса к HF API: model=%s", target_model)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.post(endpoint, headers=headers, json=payload)

                # Обработка 503 (Модель загружается в память)
                if response.status_code == 503:
                    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    estimated_time = float(data.get("estimated_time", 20.0))
                    # Ограничиваем паузу максимум 30 секундами за одну итерацию
                    sleep_time = min(estimated_time, 30.0)
                    logger.warning(
                        "HF модель '%s' загружается (503 Service Unavailable). Повтор через %.1f сек (попытка %d/%d)...",
                        target_model,
                        sleep_time,
                        attempt,
                        self._max_retries,
                    )
                    await asyncio.sleep(sleep_time)
                    continue

                response.raise_for_status()
                data = response.json()

                if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                    return str(data[0]["generated_text"]).strip()
                if isinstance(data, dict) and "generated_text" in data:
                    return str(data["generated_text"]).strip()

                return str(data)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 503 and attempt < self._max_retries:
                    await asyncio.sleep(2.0 ** attempt)
                    continue
                logger.error("HTTP ошибка HF API [%s]: %s", exc.response.status_code, exc.response.text)
                raise RuntimeError(f"HuggingFace API HTTP Error: {exc.response.status_code}") from exc
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if attempt < self._max_retries:
                    backoff = 2.0 ** attempt
                    logger.warning("Сетевой сбой при обращении к HF (%s). Повтор через %.1f сек...", exc, backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise RuntimeError(f"HuggingFace API timeout/network failure after {self._max_retries} attempts: {exc}") from exc
            except Exception as exc:
                logger.error("Непредвиденный сбой HF API: %s", exc, exc_info=True)
                raise RuntimeError(f"HuggingFace API failure: {exc}") from exc

        raise RuntimeError(f"HuggingFace API: превышено максимальное число повторных попыток ({self._max_retries}).")
