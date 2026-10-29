.PHONY: build up up-build down logs restart clean migrate deploy test

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

# Production volumes are deliberately never removed by Make.
clean:
	@echo "Volume deletion is disabled. Back up data and manage volumes explicitly." >&2
	@false

# Запуск миграций вручную
migrate:
	docker compose --profile tools run --rm --no-deps migrate

# Вход в контейнер бота
shell:
	docker compose exec bot /bin/bash

# Вход в PostgreSQL
psql:
	docker compose exec postgres sh -c 'exec psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

# Checked deployment with backup, separate migrations and rollback.
deploy:
	bash scripts/deploy.sh

test:
	uv run --frozen python -m unittest discover -s tests -v
