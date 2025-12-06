#!/bin/sh
set -e

# Копируем prod .env и ставим MODE=prod
sed -i 's/^MODE=.*/MODE=prod/' /app/.env

# Ждём, пока PostgreSQL станет доступен
until pg_isready -h "$DB_HOST_PROD" -p 5432 -U "$DB_USER"; do
  echo "Waiting for Postgres..."
  sleep 2
done

# Выполняем миграции
python -m alembic upgrade head

# Запускаем приложение
python main.py
