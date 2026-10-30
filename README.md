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

Production: `157.228.114.185`, доступ администратора с ноутбука:

```bash
ssh -i ~/.ssh/id_ed25519 rub@157.228.114.185
```

Парольный SSH root временно сохранён по указанию владельца. `rub` имеет sudo;
непривилегированный `botkit-deploy` допускается только по отдельному ключу и может
вызвать только ограниченный обработчик деплоя. В Docker group он не состоит.

Push в `main` запускает `.github/workflows/deploy.yml`. Workflow закрепляет
ED25519 host fingerprint нового сервера и отправляет `git archive` проверенного
revision через SSH. Единственный нужный Actions secret — `BOTKIT_DEPLOY_KEY`.
Старые `SSH_HOST`, `SSH_USERNAME`, `SSH_PASSWORD`, `SERVER_PORT` этим workflow
не используются. Приватный deploy-ключ и реальные credentials не коммитить.

Обработчик принимает только `deploy <40 hex symbols>`, отклоняет traversal,
symlinks, hardlinks, повторные пути и слишком большие архивы. CI не получает shell,
SSH forwarding, произвольный sudo, Docker socket или доступ к административным
секретам. Полученный исходный код выполняется внутри контейнеров с заданными
сервером ограничениями. Разрешение выкладывать приложение всё равно позволяет
менять его поведение и читать доступные ему прикладные данные; защищайте `main`
и deploy secret соответственно.

Production Compose находится в root-only `/etc/botkit/compose.yml`, переменные —
в `/etc/botkit/compose.env`, Redis ACL — `/etc/botkit/redis-users.acl`.
Код релизов хранится в `/opt/botkit/releases/<revision>`, текущий — ссылка
`/opt/botkit/current`. Host policy и deploy scripts загружаемый архив не заменяет:
их эталонные копии для ручного review находятся в `deployment/host/`.
При изменении Compose/firewall/host scripts администратор должен отдельно
проверить и установить новую политику; обычный CI обновляет приложение.

Все пять сервисов используют непривилегированные UID, cap_drop ALL, NNP,
read-only rootfs, writable volumes/tmpfs, ограничения RAM/CPU/PID и ротацию логов.
Docker socket и каталоги хоста с секретами боту не монтируются. PostgreSQL и Redis
изолированы от мониторинга; только бот выходит наружу по HTTPS/DNS. Приватные
адреса и cloud metadata из egress-сети запрещены. У БД отдельные роли приложения
и миграций; runtime не может выполнять DDL, TRUNCATE, создавать роли, читать
pg_authid или переключаться на postgres. Redis default user отключён.

Порты сервисов на хосте не публикуются. SSH-туннель для мониторинга:

```bash
ssh -i ~/.ssh/id_ed25519 -N \
  -L 3000:172.30.33.30:3000 -L 9090:172.30.33.20:9090 rub@157.228.114.185
```

После этого Grafana: `http://127.0.0.1:3000`. Для PG/Redis аналогично
`-L 5432:172.30.30.20:5432 -L 6379:172.30.30.30:6379`.
Административные пароли находятся в закрытом env на сервере.

Деплой собирает образ и запускает тесты без сети и production secrets до остановки
бота, делает согласованный PG/Redis/Grafana backup, запускает миграции отдельной
ролью и ожидает health. При ошибке пытается вернуть предыдущие контейнеры;
данные и миграции поверх новых записей автоматически не откатываются.
При будущих изменениях схемы проверяйте совместимость со старым приложением.
Рабочая конфигурация отката — `/var/lib/botkit/last-good.json`, статус —
`/var/lib/botkit/deploy-status`.

Ежедневные согласованные снимки создаёт `botkit-backup.timer` в
`/var/backups/botkit` (30 дней, не менее 14 последних копий). На ноутбуке
`botkit-backup-pull.timer` каждые шесть часов при доступности компьютера копирует
последний snapshot с шифрованием до записи на диск в `~/Desktop/BotKit-backups`.
Ключ восстановления — `~/.local/share/botkit-recovery/backup-passphrase`, 0600.
Для ручной выгрузки: `~/.local/bin/botkit-backup-pull`.

Восстановление исходного снимка проверено по полным хешам строк шести таблиц,
sequence values и Alembic revision. Новый snapshot также проверен восстановлением
в отдельных контейнерах без сети и Telegram. Redis TTL продолжает действовать;
история Prometheus в исходном архиве отсутствовала и начинается заново.

Для локальной разработки используйте `docker-compose.yml` и `.env.example`.
Production bootstrap требует явного создания volumes, восстановления данных и
прав ролей. `scripts/deploy.sh` относится к прежнему серверу; на новом сервере
вызывается установленный `/usr/local/sbin/botkit-deploy` через ограниченный SSH.
Удаление production volumes командой `make clean` отключено.

Изоляция инфраструктуры не исправляет ранее отмеченные пропуски пользовательской
авторизации в обработчиках BotKit. Прикладной аудит и обновление закреплённых
образов PG/Redis/Prometheus выполняются отдельно от переноса совместимого снимка.

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
