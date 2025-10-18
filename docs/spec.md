# Reddit Bot Technical Specification and Architecture

Goal: Implement a Python bot that connects to the Reddit API with read-only permissions, periodically (or on-demand) fetches up to 100 latest messages from subscribed threads, and saves new posts to a local SQLite database. The bot also downloads media files from links and saves them to a `media/` folder, while storing the reference to the downloaded file (generated uid) in the `news` table.

Key Requirements:
- All credentials and configuration parameters in `.env` file (example in `env.example`)
- Authentication: bot uses OAuth2 with read permissions (scope: read, maybe identity if needed)
- Database contains tables: `subscriptions`, `news`, `media`
- For each subscription, bot fetches up to 100 latest comments/posts (in thread) and adds only new ones to `news`
- Media (from `news.media_url`) are downloaded and saved to `media/` with unique uid filename; `media` table stores uid -> original name/type mapping

Контракт (inputs/outputs):
- Входы: файл `.env` с creds (CLIENT_ID, CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD или refresh token flow), список тредов в таблице `subscriptions`.
- Выходы: обновлённая SQLite БД (`db.sqlite`), скачанные файлы в `media/`.
- Ошибки: сетевые ошибки, ошибки аутентификации; логируем и повторяем с экспоненциальным бэкофф.

Архитектура — кратко:

- Компоненты:
  - main.py — точка входа; инициализирует конфиг, логгер и запускает синхронизацию.
  - reddit_client.py — обёртка для Reddit API (пагинация, получение 100 последних сообщений для треда).
  - db.py — слой работы с SQLite: инициализация схемы, функции для чтения `subscriptions`, проверки наличия новости, вставки в `news`, `media`.
  - media_downloader.py — скачивание файлов (параллельно, ограничение на concurrency), генерация uid для имён файлов.
  - workers/sync_worker.py — оркеструет цикл: читает подписки, для каждой вызывает reddit_client, фильтрует новые и сохраняет.
  - config.py — загрузка `.env` и валидация переменных.
  - utils.py — утилиты (uid generation, retry decorator, нормализация ссылок).

- Схема потоков данных:
  1. main -> config -> db
  2. db: читаем `subscriptions` (список тредов, например `thread_fullname` или `submission id`)
  3. reddit_client: для каждого треда получаем элементы (до 100) — posts/comments
  4. sync_worker: для каждого элемента проверяем, есть ли в `news` (по внешнему id), если нет — вставляем запись (включая media_url если есть)
  5. media_downloader: для новых записей со ссылками скачивает файлы, генерирует uid filename и добавляет запись в `media`.

База данных — структура таблиц (пример SQL):

-- subscriptions: список тредов за которыми следим
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL UNIQUE,
    title TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- news: все новости / элементы
CREATE TABLE news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE, -- id из Reddit (например t1_... для коммента или t3_... для поста)
    thread_id TEXT, -- внешний ключ к subscriptions.thread_id
    author TEXT,
    created_utc INTEGER,
    title TEXT,
    body TEXT,
    media_url TEXT, -- оригинальная ссылка
    media_uid TEXT, -- имя файла в папке media/ если скачано
    raw_json TEXT, -- необязательное: полная запись в json
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- media: информация о скачанных файлах
CREATE TABLE media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid_filename TEXT NOT NULL UNIQUE,
    original_url TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

Валидация дубликатов:
- Проверять `news.external_id` уникальность перед вставкой. Для дополнительной безопасности можно хэшировать контент и сохранять хэш, чтобы отфильтровать идентичные тексты с разными id.

Полезные детали реализации:
- Использовать библиотеку `praw` или `httpx` + `requests` напрямую. PRAW упрощает работу, но требует конфигурации OAuth. Я рекомендую `praw` для стабильности и простоты.
- Для скачивания медиа — `httpx` с лимитом concurrency через `asyncio` или `concurrent.futures.ThreadPoolExecutor`.
- UID для файлов: использовать `uuid4().hex` + оригинальное расширение файла (если известно) или content-type -> extension map.
- Логирование: использовать `logging` с ротацией (RotatingFileHandler) и уровнем DEBUG при разработке.
- Retry: обернуть сетевые вызовы в retry с экспоненциальным бэкофф (например tenacity или самодельный декоратор).

Порядок работы (runtime):
1. Запуск: main загружает `.env`, инициализирует БД (если нужно), создаёт папку `media/`.
2. Чтение подписок из таблицы `subscriptions`.
3. Для каждой подписки получить 100 последних items через reddit_client.
4. Фильтровать уже существующие записи по `external_id`.
5. Вставить новые в `news` (с media_url если есть).
6. Запустить скачивание медиа для новых записей, записать `media_uid` в `news` и создать запись в `media`.

Критические моменты и edge-cases:
- Rate limits Reddit API: ограничивать частоту запросов, использовать backoff по 429/5xx.
- Ссылки на сторонние файло-хостинги (imgur, reddit media, gfycat): поддержать redirect и различные content-type.
- Большие файлы: ограничить максимальный размер скачивания.
- Прерывание во время записи: использовать транзакции для атомарности вставок и обновлений.

Мониторинг и операции:
- Логи и метрики (счётчик новых записей, ошибок скачивания).
- Возможность ручной синхронизации для одного треда.

Дополнения (опционально):
- Web API для просмотра новостей.
- Отправка уведомлений (email/webhook) при новых записях.

---
Файл создан: краткая спецификация и архитектура. Следующий шаг — инструкция по получению авторизационных данных для Reddit API.
