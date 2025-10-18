- Инструкция: как шаг за шагом получить client_id/client_secret и refresh_token для бота

Коротко: нужно создать приложение на Reddit, указать корректный Redirect URI, получить одноразовый code и обменять его на токены. Ниже — проверенные шаги.

1) Создать приложение в Reddit
   - Откройте https://www.reddit.com/prefs/apps и нажмите "Create App".
   - Name: любое (например YuMiBot)
   - Тип: выберите "installed app" (если планируете локальный редирект) или "web app".
   - Redirect URI: укажите http://127.0.0.1:8000 (или другой порт, который будете использовать). Точное совпадение обязательно.
   - Сохраните — вы получите `client id` (виден под названием) и `client secret` (если есть).

2) Подготовьте `.env` (локально) с минимумом переменных

REDDIT_CLIENT_ID=<client_id>
REDDIT_CLIENT_SECRET=<client_secret>
REDDIT_USER_AGENT=mynewsbot/0.1 by u/yourusername
REDIRECT_PORT=8000

3) Получить код авторизации (code)
   - Сформируйте URL (замените значения):

      https://www.reddit.com/api/v1/authorize?client_id=<CLIENT_ID>&response_type=code&state=state123&redirect_uri=http://127.0.0.1:<PORT>&duration=permanent&scope=read

   - Откройте URL в браузере, разрешите доступ. После авторизации вас перенаправят на http://127.0.0.1:<PORT>/?code=XXXXX — сохраните значение `code` (это одноразовый код).

4) Обменять code на токены (curl)

   curl -X POST -u "<CLIENT_ID>:<CLIENT_SECRET>" \
      -d "grant_type=authorization_code&code=<THE_CODE>&redirect_uri=http://127.0.0.1:<PORT>" \
      -A "<USER_AGENT>" \
      https://www.reddit.com/api/v1/access_token

   Успешный ответ — JSON с keys: `access_token`, `expires_in`, `scope` и (если duration=permanent) `refresh_token`.

5) Сохраните `refresh_token` в `.env` как `REDDIT_REFRESH_TOKEN` и больше не публикуйте его.

Удобно: helper-скрипты в проекте
   - `tools/1_get_refresh_token.py` — автоматически откроет браузер, перехватит code и обменяет его; флаг `--save` запишет `REDDIT_REFRESH_TOKEN` в `.env`.
   - `tools/2_check_env.py` — проверит, что в `.env` есть обязательные поля.

Диагностика ошибок 400
   - Проверьте точное совпадение Redirect URI в настройках Reddit и в `.env` (хост, схема, порт, слеш).
   - Убедитесь, что `client_id` не пуст и скопирован корректно (бывают пробелы/невидимые символы).
   - Для ошибок при обмене кода на токен — посмотрите тело ответа (curl выведет его) и проверьте, что redirect_uri в запросе совпадает с указанным в приложении.

Безопасность
   - Не публикуйте `client_secret` и `refresh_token` — регенерируйте при утечке.

---
Коротко и практично — если хотите, могу ещё сократить до одной команды или автоматически сохранить токен в `.env` (скрипт уже добавлен).
