#!/usr/bin/env bash
set -e

echo "=== [NOMAD PROTOCOL] Развертывание Hexagonal Telegram Bot ==="

if [ ! -f ".env" ]; then
    echo "Создание .env из шаблона .env.example..."
    cp .env.example .env
    echo "⚠️ Заполните .env валидным BOT_TOKEN и HF_API_KEY перед запуском!"
    exit 1
fi

echo "Сборка и запуск контейнеров через docker compose..."
docker compose pull || true
docker compose up -d --build

echo "Проверка запущенных сервисов..."
docker compose ps

echo "Бот и сопутствующие сервисы успешно запущены!"
