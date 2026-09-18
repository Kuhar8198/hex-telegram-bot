"""Доменные сущности и DTO.

Слой: Domain
Не содержит внешних зависимостей или фреймворков.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class UserPromptDTO:
    """DTO запроса пользователя из Telegram."""

    user_id: int
    chat_id: int
    prompt: str
    username: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class SearchResultDTO:
    """DTO результата поиска."""

    title: str
    url: str
    snippet: str
    engine: str = "searxng"


@dataclass(frozen=True, slots=True)
class BotResponseDTO:
    """DTO сгенерированного ответа."""

    text: str
    model_used: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
