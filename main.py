"""Composition Root (Точка входа приложения).

Отвечает за:
1. Загрузку конфигурации (pydantic-settings).
2. Инициализацию асинхронных HTTP-клиентов и хранилищ.
3. Инстанцирование исходящих адаптеров (HF, Bunker, SearXNG + Tavily Fallback, Qdrant).
4. Внедрение зависимостей (DI) в Use Cases.
5. Запуск Telegram бота через Aiogram 3.x Long Polling.
6. Graceful Shutdown (закрытие bot.session и dp.storage).
"""

from __future__ import annotations

import asyncio
import logging
import sys

import httpx

from app.adapters.inbound.telegram.bot import create_bot_and_dispatcher
from app.adapters.outbound.bunker_adapter import BunkerAdapter
from app.adapters.outbound.composite_search_adapter import CompositeSearchAdapter
from app.adapters.outbound.hf_adapter import HfAdapter
from app.adapters.outbound.qdrant_adapter import QdrantAdapter
from app.adapters.outbound.searxng_adapter import SearxngAdapter
from app.adapters.outbound.tavily_adapter import TavilyAdapter
from app.application.use_cases.process_prompt import ProcessPromptUseCase
from app.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Основная асинхронная процедура запуска приложения."""
    logger.info("Запуск Telegram-бота с гексагональной архитектурой...")

    # Общий пул соединений httpx с настроенными лимитами
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    timeout = httpx.Timeout(60.0, connect=10.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as http_client:
        # 1. Инициализация исходящих адаптеров (Outbound Adapters)
        hf_adapter = HfAdapter(
            api_key=settings.HF_API_KEY,
            default_model=settings.HF_DEFAULT_MODEL,
            http_client=http_client,
            max_retries=3,
        )

        bunker_adapter = BunkerAdapter(
            base_url=settings.BUNKER_API_URL,
            token=settings.BUNKER_TOKEN,
            http_client=http_client,
        )

        searxng_adapter = SearxngAdapter(
            base_url=settings.SEARXNG_URL,
            http_client=http_client,
        )

        tavily_adapter = TavilyAdapter(
            api_key=settings.TAVILY_API_KEY,
            http_client=http_client,
        ) if settings.TAVILY_API_KEY else None

        # Композитный поиск с автоматическим переключением на Tavily при сбое SearXNG
        search_adapter = CompositeSearchAdapter(
            primary_adapter=searxng_adapter,
            fallback_adapter=tavily_adapter,
        )

        # Векторное хранилище Qdrant для семантического RAG
        qdrant_adapter = QdrantAdapter(
            base_url=settings.QDRANT_URL,
            collection_name="bot_context",
            http_client=http_client,
        )

        # 2. Инициализация слоя Use Cases с внедрением зависимостей (DI)
        process_prompt_use_case = ProcessPromptUseCase(
            hf_port=hf_adapter,
            bunker_port=bunker_adapter,
            search_port=search_adapter,
            vector_port=qdrant_adapter,
        )

        # 3. Инициализация входящего адаптера (Telegram)
        bot, dp = create_bot_and_dispatcher(
            bot_token=settings.BOT_TOKEN,
            process_prompt_use_case=process_prompt_use_case,
            redis_url=settings.REDIS_URL,
        )

        # 4. Запуск Long Polling с контролем завершения ресурсов
        logger.info("Бот успешно сконфигурирован. Запуск polling...")
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        finally:
            logger.info("Корректное закрытие ресурсов (Graceful Shutdown)...")
            try:
                if hasattr(dp, "storage") and dp.storage:
                    await dp.storage.close()
                    logger.info("FSM Storage успешно закрыт.")
            except Exception as exc:
                logger.warning("Ошибка при закрытии FSM storage: %s", exc)

            try:
                await bot.session.close()
                logger.info("Telegram Bot session закрыта.")
            except Exception as exc:
                logger.warning("Ошибка при закрытии bot.session: %s", exc)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
