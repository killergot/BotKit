# BotKit
`BotKit` — Telegram‑бот для личного учёта лекарств и совместного доступа к "аптечкам".

**Кратко**: храните лекарства в аптечках, добавляйте заметки и сроки годности, делитесь доступом к аптечке с другими пользователями, удаляйте аптечки в корзину и восстанавливайте при необходимости.

**Стек**: Python, aiogram, SQLAlchemy (async), PostgreSQL (asyncpg), Alembic, Redis (опционально).

**Содержание README**
- Клонирование и установка
- Переменные окружения
- Миграции базы
- Запуск бота
- Структура проекта
- Основные команды бота
- Разработка

## Production на сервере

Настройки контейнеров находятся в `docker-compose.yml`, пример серверных переменных —
`.env.example`. Реальные значения храните только на сервере в закрытом файле
`/etc/botkit/compose.env` (0600); `.env` в checkout может быть ссылкой на него.
Production-приложение читает переменные контейнера, а не встроенный `.env`.

Перед первым запуском необходимы существующие volumes `botkit_postgres_data`,
`botkit_redis_data`, `botkit_grafana_data`, `botkit_prometheus_data`, проверенный backup,
роли из `scripts/database-roles.sql` и Redis ACL `/etc/botkit/redis-users.acl`.
Этот Compose намеренно не создаёт пустую БД взамен существующего тома.
Пример ACL (замените пароли независимыми случайными значениями):

```text
user default off
user admin on >ADMIN_PASSWORD ~* &* +@all
user botkit on >APP_PASSWORD ~* &* +@all -@admin -@dangerous
```

Файл ACL на данном сервере — root:1000, 0640, каталог `/etc/botkit` — 0700.
`botkit_app` получает CRUD и sequences; `botkit_migrator` владеет таблицами для DDL.
Миграционный и административные пароли не передаются обычному контейнеру бота.
Смена переменной POSTGRES_USER не создаёт роль в заполненной БД.

Production deploy выполняется от root командой `bash scripts/deploy.sh`.
Она собирает образ, запускает тесты без сети/секретов, делает PG/Redis/Grafana backup
с короткой остановкой бота, применяет отдельный firewall, запускает миграции одноразово
и ждёт готовности бота. При ошибке возвращается предыдущая конфигурация контейнеров;
данные не откатываются поверх новых записей. Резервные копии — `/var/backups/botkit`,
состояние и закрытая конфигурация отката — `/var/lib/botkit`.
Начальный `last-good.json` должен быть сохранён до первого deploy. Совместимость
будущих миграций со старым приложением необходимо проверять до push.

Push в main запускает тот же deploy через GitHub Actions. Установленный secret
`SSH_PASSWORD` содержит SSH **ключ**, его существующее имя сохранено.
При смене SSH host key обновите закреплённый fingerprint в workflow.
Не запускайте старый `make down` перед deploy. Удаление volumes через `make clean`
отключено. Для ручной миграции: `make migrate`; для тестов: `make test`.

Бот работает UID 10001, без capabilities, с NNP/read-only rootfs и writable `/tmp`.
БД/Redis отделены от мониторинга; firewall разрешает только необходимые связи и
HTTPS/DNS бота наружу. SSH, VPN и игровой контейнер этим deploy не меняются.
Административные порты опубликованы на localhost; пример туннелей:

```bash
ssh -i ~/.ssh/serv -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 root@185.200.176.8
```

Далее Grafana доступна на `http://127.0.0.1:3000`. Для psql/Redis аналогично
пробрасываются 5432/6379; используйте административные credentials из закрытого env,
а не runtime-логин. Доступ через общий VPN-IP больше не публикуется.
Образы PG/Redis закреплены на ранее работающих digest; обновление их версий требует
отдельной проверки восстановления. Патч Grafana 12.1.10 закрывает обнаруженные
CVE-2026-27876/27880, но это не заменяет регулярную проверку обновлений.

Ниже — инструкции для локальной разработки; пример с DATABASE_URL исторический:
фактические параметры загрузчика — DB_NAME, DB_USER, DB_PASS, DB_HOST_DEV/PROD,
REDIS_HOST_DEV/PROD, REDIS_PORT, REDIS_PASSWORD, REDIS_USER, REDIS_DB.

## Клонирование и установка

```powershell
git clone <repo-url>
cd BotKit
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Переменные окружения

Скопируйте пример `.env` (или создайте свой) и заполните значения:

```text
BOT_TOKEN=ваш_токен_бота
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
REDIS_URL=redis://localhost:6379/0   # необязательно
```

Файл `.env` используется библиотекой `python-dotenv`/`environs` для конфигурации.

## Миграции базы данных

Проект использует `alembic`. Примените миграции перед запуском:

```powershell
alembic upgrade head
```

Создать новую миграцию (при изменениях моделей):

```powershell
alembic revision --autogenerate -m "Описание изменений"
alembic upgrade head
```

## Запуск бота

После настройки переменных окружения и миграций запустите:

```powershell
python main.py
```

Или через `docker-compose` (если настроено):

```powershell
docker-compose up --build
```

## Структура проекта (кратко)

- `main.py` — инициализация бота, регистрация роутеров и запуск.
- `app/handlers/` — обработчики Telegram команд и callback'ов (например `app/handlers/medicine/kits.py`).
- `app/keyboard/` — генерация inline-клавиатур.
- `app/database/` — конфигурация БД и модели SQLAlchemy (`models/medicine.py`, `models/users.py`).
- `app/repositoryes/` — классы-репозитории для CRUD операций.
- `app/middleware/` — middleware для DB/Redis/пользовательских данных.
- `app/lexicon/` — тексты и локализация (команды и подсказки).
- `migrations/` — alembic миграции.
- `requirements.txt` — зависимости проекта.

## Основные команды и поведение бота

- `/start` — регистрация/приветствие.
- `/help` — краткий список команд.
- `/upload` — добавить лекарство: выбор аптечки → ввод данных лекарства.
- `/my_kits` — показать ваши аптечки. Отсюда доступны:
	- удаление конкретной аптечки (пометка `deleted=True`),
	- **Корзина аптечек** — показать удалённые аптечки (`deleted=True`), и восстановить их (снятие флага `deleted`).
	- отмена действий.
- `/share` — отправить запрос на шаринг аптечки другому пользователю.
- `/update`, `/del`, `/find`, `/expired` и др. — обновление, удаление и поиск лекарств.

Тексты команд и сообщений хранятся в `app/lexicon/lexicon.py`.

## Как реализовано восстановление аптечек

Репозиторий `MedicineKitRepository` содержит метод `get_all(...)`, который поддерживает фильтр `deleted`.
Для пользователя доступен `get_by_user(user_id, deleted=None)`. Корзина формируется вызовом `get_by_user(user_id, deleted=True)`.
Восстановление выполняется через `update(kit_id, deleted=False)`.

## Разработка и отладка

- Запуск в dev режиме: убедитесь, что `.env` настроен.
- Логирование настраивается в `main.py` — включите уровень `DEBUG` при необходимости.
- Проверки конфигурации и запуска: `uv run --frozen python -m unittest discover -s tests -v`.

## Полезные команды для администратора

- Просмотреть зависимости: `pip freeze` / `pip install -r requirements.txt`.
- Применить миграции: `alembic upgrade head`.

## Лицензия

Исходный код проекта распространяется по [лицензии MIT](LICENSE).
