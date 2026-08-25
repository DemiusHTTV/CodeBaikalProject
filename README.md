# CodeBaikal — SQL-ассистент для университета

Бэкенд-прототип, который переводит вопрос сотрудника вуза на русском языке
в SQL-запрос, безопасно проверяет его и выполняет на реальной базе данных.

Вопрос → YandexGPT генерирует SQL → `sql_guard` проверяет и обезвреживает
запрос → PostgreSQL выполняет его в режиме "только чтение" → результат
выводится таблицей.


## Как это устроено

```
Вопрос (рус.) → YandexGPT (LLM) → sql_guard (проверка SQL) → PostgreSQL (read-only) → результат
```

- **YandexGPT** (`src/llm.py`) — получает вопрос и схему БД, возвращает SQL-запрос.
  Авторизация статичным API-ключом (`Authorization: Api-Key ...`), без обмена
  на временный токен. Модуль ничего не знает про безопасность и структуру БД —
  только отправляет (system, user) и возвращает текст ответа.
- **sql_guard** (`src/sql_guard/`) — проверяет сгенерированный SQL перед выполнением:
  - разрешён только один `SELECT`-оператор (никаких `INSERT/UPDATE/DELETE/DROP/...`,
    в том числе спрятанных внутри CTE);
  - запрещены блокировки строк (`FOR UPDATE`/`FOR SHARE`);
  - разрешены только таблицы из белого списка (выводится из `db/schema.sql`);
  - запрещены опасные функции PostgreSQL (доступ к файлам, `pg_sleep`, `dblink` и т.д.);
  - гарантированно добавляется `LIMIT` (по умолчанию 200, максимум 1000);
  - каждое отклонение записывается в лог с причиной.
- **PostgreSQL** (`src/db.py`) — запрос выполняется в `READ ONLY` транзакции с
  таймаутом — вторая линия защиты на случай, если `sql_guard` что-то пропустит.

## Структура проекта

```
backend/
├── db/
│   ├── docker-compose.yml   # локальный Postgres в Docker
│   ├── schema.sql           # схема БД университета
│   └── seed.sql             # тестовые данные
├── src/
│   ├── ask.py                # консольная точка входа
│   ├── config.py              # настройки БД из .env
│   ├── db.py                  # подключение к PostgreSQL
│   ├── llm.py                  # клиент YandexGPT
│   ├── schema_context.py       # парсинг схемы БД для промпта и белого списка таблиц
│   ├── logging_config.py       # настройка логирования (JSON, файл logs/app.log)
│   └── sql_guard/               # проверка SQL перед выполнением
└── Tests/
    ├── core/                     # юнит-тесты (config, db, schema_context, sql_guard)
    └── model/                    # интеграционный тест YandexGPT
```

## Требования

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) для управления зависимостями
- Docker (для локальной БД)

## Установка и запуск

1. Скопировать `.env.example` в `.env` и заполнить значения:

   ```bash
   cp .env.example .env
   ```

   | Переменная | Назначение |
   |---|---|
   | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | подключение к PostgreSQL |
   | `YANDEX_AUTH` | API-ключ Yandex Cloud |
   | `YANDEX_FOLDER` | ID каталога Yandex Cloud |
   | `YANDEX_MODEL` | название модели YandexGPT |
   | `LOG_LEVEL` | уровень логирования (`DEBUG`/`INFO`/`WARNING`/`ERROR`), по умолчанию `INFO` |

2. Поднять локальную базу данных:

   ```bash
   cd backend/db
   docker compose up -d
   ```

   При первом запуске Postgres сам выполнит `schema.sql` и `seed.sql`.

3. Установить зависимости и запустить консольный клиент:

   ```bash
   cd backend
   uv run python -m src.ask
   ```

   Дальше просто пишем вопрос по-русски и жмём Enter. Пустая строка — выход.

   Вместо `.env` параметры подключения к БД можно передать переменными
   окружения прямо в команде запуска — например, для локальной БД из
   `docker-compose.yml` (host/port/name/user/password по умолчанию оттуда):

   ```bash
   cd backend
   DB_HOST=127.0.0.1 DB_PORT=5432 DB_NAME=university DB_USER=hackathon DB_PASSWORD=hackathon \
     .venv/bin/python -m src.ask
   ```

## Тесты

```bash
cd backend
uv run pytest
```

Тесты, которым нужна реальная БД или доступ к YandexGPT, сами помечаются
`skip`, если соответствующие переменные окружения/сервисы недоступны.

## Логи

Логи пишутся в `backend/logs/app.log` в формате JSON (по одной записи на
строку), в консоль не выводятся — там остаётся только диалог с пользователем.
