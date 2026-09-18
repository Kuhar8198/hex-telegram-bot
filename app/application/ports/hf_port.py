from abc import ABC, abstractmethod


class IHuggingFacePort(ABC):
    """Абстрактный порт взаимодействия с Hugging Face Inference API."""

    @abstractmethod
    async def generate_response(self, prompt: str, model_id: str | None = None) -> str:
        """Асинхронная генерация ответа модели по промпту.

        Args:
            prompt: Входной текстовый промпт для модели.
            model_id: Опциональный идентификатор модели в реестре HF.

        Returns:
            str: Сгенерированный текстовый ответ.
        """
        pass
