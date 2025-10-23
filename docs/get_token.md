# How to Get Reddit API Tokens

Instructions: step-by-step guide to obtain client_id/client_secret and refresh_token for the application.

**In short**: you need to create a Reddit application, specify the correct Redirect URI, get a one-time code, and exchange it for tokens. Below are the verified steps.

## 1) Create a Reddit Application
   - Open https://www.reddit.com/prefs/apps and click "Create App".
   - Name: any name (e.g., RedditSync)
   - Type: choose "installed app" (if you plan local redirect) or "web app".
   - Redirect URI: specify http://127.0.0.1:8000 (or another port you'll use). Exact match is required.
   - Save — you'll get `client id` (visible under the name) and `client secret` (if available).

## 2) Prepare `.env` file (locally) with minimum variables

```
REDDIT_CLIENT_ID=<client_id>
REDDIT_CLIENT_SECRET=<client_secret>
REDDIT_USER_AGENT=python:redditsync:v1.0 (by /u/yourusername)
REDIRECT_PORT=8000
```

## 3) Get authorization code
   - Form the URL (replace values):

      ```
      https://www.reddit.com/api/v1/authorize?client_id=<CLIENT_ID>&response_type=code&state=state123&redirect_uri=http://127.0.0.1:<PORT>&duration=permanent&scope=read
      ```

   - Open URL in browser, allow access. After authorization you'll be redirected to http://127.0.0.1:<PORT>/?code=XXXXX — save the `code` value (this is a one-time code).

## 4) Exchange code for tokens (curl)

   ```bash
   curl -X POST -u "<CLIENT_ID>:<CLIENT_SECRET>" \
      -d "grant_type=authorization_code&code=<THE_CODE>&redirect_uri=http://127.0.0.1:<PORT>" \
      -A "<USER_AGENT>" \
      https://www.reddit.com/api/v1/access_token
   ```

   Successful response — JSON with keys: `access_token`, `expires_in`, `scope` and (if duration=permanent) `refresh_token`.

## 5) Save `refresh_token` in `.env` as `REDDIT_REFRESH_TOKEN` and never publish it.

## Convenient: helper scripts in the project
   - `tools/1_get_refresh_token.py` — automatically opens browser, captures code and exchanges it; `--save` flag writes `REDDIT_REFRESH_TOKEN` to `.env`.
   - `tools/2_check_env.py` — checks that `.env` contains required fields.

## Troubleshooting 400 errors
   - Check exact match of Redirect URI in Reddit settings and in `.env` (host, scheme, port, slash).
   - Make sure `client_id` is not empty and copied correctly (watch for spaces/invisible characters).
   - For errors when exchanging code for token — check response body (curl will output it) and verify that redirect_uri in request matches the one specified in the application.

## Security
   - Don't publish `client_secret` and `refresh_token` — regenerate if leaked.

---
Short and practical — if you want, I can reduce it to a single command or automatically save the token to `.env` (script already added).
