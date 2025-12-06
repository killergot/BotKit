#!/bin/sh
set -e

# Ждём, пока PostgreSQL станет доступен
until pg_isready -h "$DB_HOST_PROD" -p 5432 -U "$DB_USER"; do
  echo "Waiting for Postgres..."
  sleep 2
done

# Выполняем миграции
python -m alembic upgrade head

# Запускаем приложение
python main.py
