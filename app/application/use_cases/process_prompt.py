"""Use Case для оркестрации обработки пользовательского промпта.

Слой: Application (Use Cases)
Архитектурный паттерн: Hexagonal Architecture (Ports and Adapters)
"""

from __future__ import annotations

import logging
from typing import Any

from app.application.ports.bunker_port import IBunkerPort
from app.application.ports.hf_port import IHuggingFacePort
from app.application.ports.search_port import ISearchPort
from app.application.ports.vector_port import IVectorStorePort

logger = logging.getLogger(__name__)


class UseCaseError(Exception):
    """Базовое исключение для слоя Application Use Cases."""
    pass


class ProcessPromptUseCaseError(UseCaseError):
    """Исключение, возникающее при ошибках исполнения пайплайна обработки промпта."""
    pass


class ProcessPromptUseCase:
    """Use Case для обработки запроса пользователя.

    Координирует работу внешних портов:
    - Запрашивает конфигурацию и секреты из Bunker API;
    - При наличии ISearchPort обогащает промпт внешним веб-контекстом;
    - При наличии IVectorStorePort подтягивает семантический контекст из Qdrant;
    - Вызывает Hugging Face Inference API для генерации итогового ответа;
    - Асинхронно сохраняет контекст диалога в векторное хранилище.
    """

    def __init__(
        self,
        hf_port: IHuggingFacePort,
        bunker_port: IBunkerPort,
        search_port: ISearchPort | None = None,
        vector_port: IVectorStorePort | None = None,
    ) -> None:
        """Инициализация Use Case через внедрение абстрактных портов (Dependency Injection).

        Args:
            hf_port: Абстрактный порт взаимодействия с моделью генерации (Hugging Face).
            bunker_port: Абстрактный порт взаимодействия с защищенным хранилищем Bunker.
            search_port: Опциональный абстрактный порт веб-поиска (SearXNG / Tavily).
            vector_port: Опциональный абстрактный порт векторной БД (Qdrant).
        """
        self._hf_port: IHuggingFacePort = hf_port
        self._bunker_port: IBunkerPort = bunker_port
        self._search_port: ISearchPort | None = search_port
        self._vector_port: IVectorStorePort | None = vector_port

    async def execute(self, prompt: str, model_id: str | None = None) -> str:
        """Выполняет полный цикл обработки промпта.

        Args:
            prompt: Текстовый запрос пользователя.
            model_id: Идентификатор целевой модели.

        Returns:
            str: Сгенерированный текстовый ответ.

        Raises:
            ProcessPromptUseCaseError: При критических сбоях вызовов внешних сервисов.
        """
        clean_prompt: str = prompt.strip()
        if not clean_prompt:
            logger.warning("Получен пустой промпт для обработки.")
            return "Запрос не может быть пустым. Пожалуйста, введите текст."

        logger.info(
            "Начало выполнения ProcessPromptUseCase (длина промпта: %d симв., переданный model_id: %s)",
            len(clean_prompt),
            model_id,
        )

        # 1. Запрос конфигурации и параметров из Bunker API
        bunker_config: dict[str, Any] = await self._fetch_bunker_config("llm_settings")

        target_model_id: str | None = (
            model_id
            or bunker_config.get("default_model_id")
            or bunker_config.get("model_id")
        )

        # 2. Обогащение контекстом веб-поиска (SearXNG / Tavily fallback)
        search_context: str = ""
        if self._search_port is not None:
            search_context = await self._retrieve_search_context(clean_prompt)

        # 3. Обогащение семантическим контекстом из векторной БД (Qdrant)
        vector_context: str = ""
        if self._vector_port is not None:
            vector_context = await self._retrieve_vector_context(clean_prompt)

        # 4. Сборка итогового промпта
        final_prompt: str = self._compose_prompt(
            user_prompt=clean_prompt,
            search_context=search_context,
            vector_context=vector_context,
            system_instruction=bunker_config.get("system_prompt"),
        )

        # 5. Асинхронная генерация ответа через порт Hugging Face
        response = await self._generate_llm_response(
            prompt=final_prompt,
            model_id=target_model_id,
        )

        # 6. Фоновое сохранение истории в векторное хранилище
        if self._vector_port is not None:
            try:
                await self._vector_port.save_context(
                    text=f"Q: {clean_prompt}\nA: {response}",
                    metadata={"model": target_model_id},
                )
            except Exception as exc:
                logger.warning("Не удалось фоново сохранить контекст в векторный стор: %s", exc)

        return response

    async def _fetch_bunker_config(self, key: str) -> dict[str, Any]:
        """Безопасное получение конфигурации из порта Bunker."""
        try:
            logger.debug("Запрос конфигурации '%s' из BunkerPort", key)
            config = await self._bunker_port.get_config_or_secret(key)
            return config if isinstance(config, dict) else {}
        except Exception as exc:
            logger.error("Критический сбой при обращении к Bunker API (key=%s): %s", key, exc, exc_info=True)
            raise ProcessPromptUseCaseError(f"Ошибка получения конфигурации из Bunker: {exc}") from exc

    async def _retrieve_search_context(self, query: str) -> str:
        """Поиск дополнительного веб-контекста с отказоустойчивой обработкой."""
        if self._search_port is None:
            return ""

        try:
            results = await self._search_port.search(query)
            if not results:
                return ""

            formatted_snippets: list[str] = []
            for idx, item in enumerate(results[:5], start=1):
                title = str(item.get("title", "Без заголовка")).strip()
                content = str(item.get("content") or item.get("snippet") or "").strip()
                url = str(item.get("url", "")).strip()

                if content:
                    snippet = f"[{idx}] {title}\nИсточник: {url}\nИнформация: {content}"
                    formatted_snippets.append(snippet)

            return "\n\n".join(formatted_snippets)
        except Exception as exc:
            logger.warning("Ошибка поиска веб-контекста: %s. Генерация продолжается.", exc)
            return ""

    async def _retrieve_vector_context(self, query: str) -> str:
        """Поиск семантического контекста из векторной БД."""
        if self._vector_port is None:
            return ""

        try:
            results = await self._vector_port.search_similar(query, limit=3)
            if not results:
                return ""

            chunks = [item["text"] for item in results if "text" in item]
            return "\n---\n".join(chunks)
        except Exception as exc:
            logger.warning("Ошибка получения векторного контекста: %s. Пропуск.", exc)
            return ""

    def _compose_prompt(
        self,
        user_prompt: str,
        search_context: str,
        vector_context: str = "",
        system_instruction: str | None = None,
    ) -> str:
        """Формирует итоговую структуру промпта с секционированием."""
        parts: list[str] = []

        if system_instruction and system_instruction.strip():
            parts.append(f"### СИСТЕМНЫЕ ИНСТРУКЦИИ:\n{system_instruction.strip()}")

        if vector_context and vector_context.strip():
            parts.append(
                f"### ПРЕДЫДУЩИЙ РЕЛЕВАНТНЫЙ КОНТЕКСТ (RAG):\n"
                f"{vector_context.strip()}"
            )

        if search_context and search_context.strip():
            parts.append(
                f"### АКТУАЛЬНЫЙ ВЕБ-КОНТЕКСТ ДЛЯ СПРАВКИ:\n"
                f"{search_context.strip()}\n\n"
                f"Используй данный контекст при ответе, если он релевантен."
            )

        parts.append(f"### ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_prompt}")

        return "\n\n".join(parts)

    async def _generate_llm_response(self, prompt: str, model_id: str | None) -> str:
        """Вызов порта инференса Hugging Face."""
        try:
            response: str = await self._hf_port.generate_response(
                prompt=prompt,
                model_id=model_id,
            )
            return response if response else "Модель вернула пустой ответ. Попробуйте переформулировать запрос."
        except Exception as exc:
            logger.error("Критический сбой генерации в HuggingFacePort: %s", exc, exc_info=True)
            raise ProcessPromptUseCaseError(f"Ошибка генерации ответа в Hugging Face: {exc}") from exc
