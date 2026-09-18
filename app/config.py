"""Конфигурация приложения на базе pydantic-settings.

Строгая валидация переменных окружения.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки и переменные окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str = Field(..., description="Токен Telegram бота от @BotFather")

    # Hugging Face
    HF_API_KEY: str = Field(default="", description="API токен Hugging Face")
    HF_DEFAULT_MODEL: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.3",
        description="Идентификатор модели HF по умолчанию",
    )

    # Bunker API
    BUNKER_API_URL: str = Field(
        default="http://localhost:8088",
        description="Базовый URL Bunker API для получения секретов",
    )
    BUNKER_TOKEN: str = Field(default="", description="Сервисный токен Bunker")

    # Search (SearXNG / Tavily)
    SEARXNG_URL: str = Field(
        default="http://searxng:8080",
        description="URL локального экземпляра SearXNG",
    )
    TAVILY_API_KEY: str = Field(default="", description="Опциональный ключ Tavily API")

    # Хранилища
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="URL подключения к Redis (кэш и FSM)",
    )
    QDRANT_URL: str = Field(
        default="http://qdrant:6333",
        description="URL векторной БД Qdrant",
    )

    # Логирование
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")


settings = Settings()
