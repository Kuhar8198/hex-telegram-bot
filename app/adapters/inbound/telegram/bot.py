"""Инициализация Telegram бота и диспетчера.

Слой: Adapters (Inbound)
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from app.adapters.inbound.telegram.handlers import router
from app.application.use_cases.process_prompt import ProcessPromptUseCase

logger = logging.getLogger(__name__)


def create_bot_and_dispatcher(
    bot_token: str,
    process_prompt_use_case: ProcessPromptUseCase,
    redis_url: str | None = None,
) -> tuple[Bot, Dispatcher]:
    """Фабрика для создания бота и диспетчера с внедрением Use Case."""
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Инициализация FSM-хранилища
    storage: BaseStorage
    if redis_url:
        try:
            storage = RedisStorage.from_url(redis_url)
            logger.info("Подключено FSM хранилище Redis: %s", redis_url)
        except Exception as exc:
            logger.warning("Не удалось подключить RedisStorage: %s. Используется MemoryStorage.", exc)
            storage = MemoryStorage()
    else:
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # Внедрение зависимостей в контекст Aiogram
    dp["use_case"] = process_prompt_use_case
    dp.include_router(router)

    return bot, dp
