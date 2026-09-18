"""Обработчики сообщений Telegram (Aiogram 3.x).

Слой: Adapters (Inbound)
Особенности:
- Защита от превышения лимита Telegram (4096 символов) через разбиение на фрагменты (chunking).
- Безопасная отправка сырого текста модели без риска падения парсера Markdown/HTML.
"""

from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandStart

from app.application.use_cases.process_prompt import ProcessPromptUseCase, ProcessPromptUseCaseError
from app.domain.models import UserPromptDTO

logger = logging.getLogger(__name__)

router = Router(name="main_router")

TELEGRAM_MAX_MESSAGE_LENGTH = 4000  # Безопасный порог с запасом под лимит 4096


def split_text_into_chunks(text: str, max_chunk_size: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Разбивает длинный текст на фрагменты без разрыва слов по возможности."""
    if len(text) <= max_chunk_size:
        return [text]

    chunks: list[str] = []
    current_text = text

    while current_text:
        if len(current_text) <= max_chunk_size:
            chunks.append(current_text)
            break

        # Ищем ближайший перенос строки или пробел
        split_index = current_text.rfind("\n", 0, max_chunk_size)
        if split_index == -1 or split_index < max_chunk_size // 2:
            split_index = current_text.rfind(" ", 0, max_chunk_size)
        if split_index == -1:
            split_index = max_chunk_size

        chunk = current_text[:split_index].strip()
        if chunk:
            chunks.append(chunk)
        current_text = current_text[split_index:].strip()

    return chunks


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    """Обработка команды /start."""
    welcome_text = (
        "👋 Привет! Я асинхронный ИИ-ассистент на базе гексагональной архитектуры.\n\n"
        "Отправьте мне любой запрос или вопрос — я выполню поиск через SearXNG/Tavily, "
        "извлеку векторный контекст и сгенерирую ответ через модель инференса."
    )
    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Обработка команды /help."""
    help_text = (
        "⚙️ Доступные команды:\n"
        "/start — Перезапуск бота и приветствие\n"
        "/help — Справка\n\n"
        "Просто напишите сообщение, и бот сформирует структурированный ответ с учетом веб-поиска."
    )
    await message.answer(help_text)


@router.message()
async def handle_prompt(
    message: types.Message,
    use_case: ProcessPromptUseCase,
) -> None:
    """Обработчик входящего текста.

    Преобразует событие в UserPromptDTO, делегирует задачу в ProcessPromptUseCase,
    разбивает ответ на чанки (при превышении 4096 символов) и безопасно отправляет пользователю.
    """
    if not message.text or not message.from_user:
        return

    # Конвертация входящего события в чистый DTO
    dto = UserPromptDTO(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        prompt=message.text,
        username=message.from_user.username,
    )

    logger.info("Получен запрос от user_id=%s: %.40s...", dto.user_id, dto.prompt)

    # Индикация набора текста
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response_text = await use_case.execute(prompt=dto.prompt)
        chunks = split_text_into_chunks(response_text)

        for chunk in chunks:
            # Отправка без явного parse_mode, чтобы символы разметки от LLM не ломали отправку
            await message.reply(chunk, parse_mode=None)

    except ProcessPromptUseCaseError as exc:
        logger.error("Ошибка бизнес-логики: %s", exc)
        await message.reply("⚠️ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.", parse_mode=None)
    except Exception as exc:
        logger.error("Непредвиденный сбой хендлера: %s", exc, exc_info=True)
        await message.reply("❌ Внутренняя ошибка сервиса.", parse_mode=None)
