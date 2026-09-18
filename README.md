# 🤖 Hexagonal Telegram AI Bot (Nomad Stack)

Асинхронный Telegram-бот производственного уровня, построенный по принципам **чистой гексагональной архитектуры (Ports and Adapters)** на стеке **Python 3.11+**, **Aiogram 3.x** и **Docker Compose**.

Бот объединяет генеративный искусственный интеллект (Hugging Face Inference API), автономный и внешний веб-поиск (SearXNG + Tavily Fallback), векторную память контекста (Qdrant RAG) и распределенное состояние диалогов (Redis FSM).

---

## 🏛 Архитектура проекта

Проект строго разделен на независимые слои согласно гексагональной архитектуре:

```
├── app/
│   ├── domain/                         # Слой Domain (бизнес-модели, DTO, чистый Python без I/O)
│   │   └── models.py                   # UserPromptDTO, BotResponseDTO, SearchResultDTO
│   │
│   ├── application/                    # Слой Application (UseCase и абстрактные порты)
│   │   ├── ports/                      # Порты (abc.ABC интерфейсы, не знающие о библиотеках)
│   │   │   ├── hf_port.py              # Порт модели генерации (IHuggingFacePort)
│   │   │   ├── bunker_port.py          # Порт безопасного хранилища конфигураций (IBunkerPort)
│   │   │   ├── search_port.py          # Порт поискового движка (ISearchPort)
│   │   │   └── vector_port.py          # Порт векторной памяти (IVectorStorePort)
│   │   └── use_cases/                  # Оркестрация бизнес-логики
│   │       └── process_prompt.py       # Сценарий ProcessPromptUseCase с RAG и веб-поиском
│   │
│   ├── adapters/                       # Слой Adapters (реализации портов и интеграции)
│   │   ├── inbound/telegram/           # Входящий адаптер: Aiogram 3.x
│   │   │   ├── bot.py                  # Инициализация бота, Dispatcher и RedisStorage
│   │   │   └── handlers.py             # Роутеры, чанкинг (до 4000 симв.) и безопасная отправка
│   │   └── outbound/                   # Исходящие адаптеры
│   │       ├── hf_adapter.py           # HF Inference API с обработкой 503 и Exponential Backoff
│   │       ├── bunker_adapter.py       # Клиент безопасного хранилища Bunker
│   │       ├── searxng_adapter.py      # Локальный приватный поиск SearXNG (JSON API)
│   │       ├── tavily_adapter.py       # Резервный поиск Tavily API
│   │       ├── composite_search_adapter.py # Fallback-цепочка: SearXNG -> Tavily
│   │       └── qdrant_adapter.py       # Векторное хранилище Qdrant (семантический RAG)
│   │
│   └── config.py                       # Типизированная валидация конфигурации (Pydantic Settings v2)
│
├── main.py                             # Composition Root: DI, единый пул HTTP-соединений, запуск и Graceful Shutdown
├── Dockerfile                          # Легковесный многоэтапный образ Python 3.11 Slim
├── docker-compose.yml                  # 5 микросервисов: Bot, SearXNG, Qdrant, Redis, Watchtower
├── searxng/settings.yml                # Конфигурация локального поисковика
├── deploy.sh                           # Скрипт развертывания
└── .github/workflows/deploy.yml        # CI/CD: автосборка и публикация в GitHub Packages (GHCR)
```

---

## ⚡ Ключевые возможности

1. **100% Асинхронность и производительность:**
   - Никаких блокирующих вызовов (`requests`, `time.sleep`).
   - Единый пул соединений `httpx.AsyncClient` с контролем `keepalive`, таймаутов и лимитов параллельных коннектов.
   - Чистый `asyncio` и асинхронные интерфейсы.

2. **Интеллектуальный поиск с Fallback:**
   - Первичный источник — локальный автономный **SearXNG** без трекинга и ограничений.
   - Если SearXNG недоступен или выдал пустую выдачу, адаптер автоматически переключается на **Tavily Search API**.

3. **Векторная память (Qdrant RAG):**
   - Бот ищет семантически похожие предыдущие сообщения и диалоги в Qdrant.
   - Контекст подмешивается в промпт модели, а итоговый ответ асинхронно сохраняется в векторную коллекцию.

4. **Защита от холодного старта HF:**
   - Hugging Face часто возвращает `503 Service Unavailable` при развертывании тяжелых моделей. Адаптер парсит поле `estimated_time`, выжидает паузу и повторяет запрос с экспоненциальным бэкоффом.

5. **Безопасная доставка в Telegram:**
   - Длинные ответы модели разбиваются функцией умного чанкинга на фрагменты до 4000 символов без разрыва слов.
   - Сырой текст от LLM отправляется безопасно без падений парсера спецсимволов.

6. **Корректный Graceful Shutdown:**
   - При получении `SIGINT` / `SIGTERM` бот аккуратно завершает polling, закрывает сессию `bot.session` и хранилище `dp.storage` (Redis).

---

## 🚀 Быстрый старт через Docker Compose

### 1. Клонирование и подготовка окружения
```bash
git clone https://github.com/Kuhar8198/hex-telegram-bot.git
cd hex-telegram-bot
cp .env.example .env
```

### 2. Заполнение переменных в `.env`
Откройте файл `.env` и укажите ваши ключи:
```env
# Обязательные ключи
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ        # от @BotFather
HF_API_KEY=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx       # токен с huggingface.co

# Опционально: резервный поиск Tavily
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxx

# Настройки сервисов Docker (по умолчанию уже настроены на локальные контейнеры)
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
SEARXNG_URL=http://searxng:8080
BUNKER_API_URL=http://localhost:8088
LOG_LEVEL=INFO
```

### 3. Запуск всего стека
Запуск выполняется одной командой:
```bash
docker compose up -d --build
```

Или с помощью скрипта:
```bash
chmod +x deploy.sh
./deploy.sh
```

### 4. Проверка работы
```bash
docker compose ps
docker compose logs -f bot
```

---

## 🛠 Запуск в режиме локальной разработки (без Docker)

Если вы хотите запустить только бота локально:

```bash
# 1. Создание виртуального окружения
python3 -m venv .venv
source .venv/bin/activate  # На Windows: .venv\Scripts\activate

# 2. Установка зависимостей
pip install -r requirements.txt

# 3. Запуск зависимостей (Redis, Qdrant, SearXNG) в Docker
docker compose up -d redis qdrant searxng

# 4. Запуск приложения (Composition Root)
python main.py
```

---

## 🔄 Автодеплой «Кочевник» (Watchtower + GHCR)

В состав `docker-compose.yml` входит контейнер **Watchtower**, который опрашивает GitHub Container Registry (`ghcr.io/kuhar8198/hex-telegram-bot/bot:latest`) каждые 5 минут.

При пуше в ветку `main` запускается GitHub Actions пайплайн (`.github/workflows/deploy.yml`):
1. Собирает оптимизированный Docker-образ бота.
2. Публикует его в GHCR.
3. Сервер с Watchtower автоматически скачивает свежий образ и перезапускает контейнер с сохранением персистентных данных в volumes (`qdrant_data`).

---

## 🛡 Безопасность

- Никакие приватные токены и пароли не зашиты в коде или Git-истории.
- Все конфигурационные параметры валидируются строгими Pydantic-схемами.
- Секретный ключ SearXNG передается через переменную среды `SEARXNG_SECRET`.
- Исключена утечка данных при сбоях сетевых вызовов благодаря строгому логированию ошибок.
