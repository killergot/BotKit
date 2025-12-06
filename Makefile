.PHONY: build up down logs restart clean

# Сборка образов
build:
	docker compose build

# Запуск контейнеров
up:
	docker compose up -d

up-build:
	docker compose up -d --build

# Остановка контейнеров
down:
	docker compose down

# Логи всех сервисов
logs:
	docker compose logs -f

# Логи только бота
logs-bot:
	docker compose logs -f bot

# Перезапуск бота
restart:
	docker compose restart bot

# Полная очистка (с удалением volumes)
clean:
	docker compose down -v
	docker system prune -f

# Запуск миграций вручную
migrate:
	docker compose exec bot alembic upgrade head

# Вход в контейнер бота
shell:
	docker compose exec bot /bin/bash

# Вход в PostgreSQL
psql:
	docker compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}