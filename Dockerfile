FROM python:3.13.3-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Явно добавляем uv в PATH
ENV PATH="/root/.local/bin:${PATH}"

# Проверяем, что uv доступен
RUN which uv && uv --version

COPY requirements.txt .

# Устанавливаем зависимости через uv
RUN uv pip install --system --no-cache -r requirements.txt

# Копируем весь проект
COPY . .

# Исправляем окончания строк в скрипте (CRLF -> LF) и даём права на выполнение
RUN sed -i 's/\r$//' /app/scripts/run.sh && \
    chmod +x /app/scripts/run.sh

# Обновляем .env если существует
RUN if [ -f /app/.env ]; then sed -i 's/^MODE=.*/MODE=prod/' /app/.env; fi
