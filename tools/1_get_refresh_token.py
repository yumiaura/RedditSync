#!/usr/bin/env python3
"""Get refresh token for Reddit OAuth2 Authorization Code Flow.

How it works: opens browser, starts local server, captures code, exchanges it for tokens.
"""
import argparse
import http.server
import socketserver
import webbrowser
import urllib.parse as urlparse
import requests
import os
from dotenv import set_key, load_dotenv

# Load .env from current working directory if present
load_dotenv()


class CodeHandler(http.server.BaseHTTPRequestHandler):
    server_version = "GetRefreshToken/0.1"

    def do_GET(self):
        parsed = urlparse.urlparse(self.path)
        qs = urlparse.parse_qs(parsed.query)
        if 'code' in qs:
            code = qs['code'][0]
            self.server.code = code
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Code received. You can close this window.</h2></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        # silence
        return


def run_local_server(port=8080, timeout=300):
    handler = CodeHandler
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        httpd.code = None
        httpd.timeout = timeout
        while httpd.code is None:
            httpd.handle_request()
        return httpd.code


def exchange_code_for_token(client_id, client_secret, code, user_agent, redirect_uri="http://127.0.0.1:8080"):
    token_url = "https://www.reddit.com/api/v1/access_token"
    auth = (client_id, client_secret)
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    headers = {'User-Agent': user_agent}
    resp = requests.post(token_url, auth=auth, data=data, headers=headers)
    resp.raise_for_status()
    return resp.json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Reddit client id (overridden by .env REDDIT_CLIENT_ID)')
    parser.add_argument('--client-secret', help='Reddit client secret (overridden by .env REDDIT_CLIENT_SECRET)')
    parser.add_argument('--user-agent', help='User-Agent header (overridden by .env REDDIT_USER_AGENT)')
    parser.add_argument('--port', type=int, default=8080, help='Local port for redirect (can be overridden by REDIRECT_PORT in .env)')
    parser.add_argument('--save', action='store_true', help='Save refresh_token to .env')
    args = parser.parse_args()

    client_id = os.getenv('REDDIT_CLIENT_ID') or args.client_id
    client_secret = os.getenv('REDDIT_CLIENT_SECRET') or args.client_secret
    user_agent = os.getenv('REDDIT_USER_AGENT') or args.user_agent
    port = int(os.getenv('REDIRECT_PORT') or args.port)

    if not client_id or not client_secret or not user_agent:
        print('Missing credentials. Provide REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT in .env or via CLI flags.')
        parser.print_help()
        raise SystemExit(2)

    redirect_uri = f"http://127.0.0.1:{port}"

    encoded_redirect = urlparse.quote_plus(redirect_uri)
    auth_url = (
        f"https://www.reddit.com/api/v1/authorize?client_id={client_id}"
        f"&response_type=code&state=state123&redirect_uri={encoded_redirect}"
        f"&duration=permanent&scope=read"
    )

    print("Opening browser for authorization. If it doesn't open, visit this URL manually:\n")
    print(auth_url)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print(f"Waiting for redirect with code on {redirect_uri} ...")
    try:
        code = run_local_server(port=port)
    except Exception as e:
        print(f'Error while running local server: {e}')
        raise

    print("Code received, exchanging for tokens...")
    try:
        token_data = exchange_code_for_token(client_id, client_secret, code, user_agent, redirect_uri=redirect_uri)
    except requests.HTTPError as e:
        print('HTTP error while exchanging code for token:', e.response.text if e.response is not None else e)
        raise
    print("Token response:")
    for k, v in token_data.items():
        print(f"{k}: {v}")

    if args.save:
        env_path = os.path.join(os.getcwd(), '.env')
        if not os.path.exists(env_path):
            open(env_path, 'a').close()
        load_dotenv(env_path)
        rt = token_data.get('refresh_token')
        if not rt:
            print('No refresh_token in response; cannot save.')
        else:
            set_key(env_path, 'REDDIT_REFRESH_TOKEN', rt)
            set_key(env_path, 'REDDIT_CLIENT_ID', client_id)
            set_key(env_path, 'REDDIT_CLIENT_SECRET', client_secret)
            set_key(env_path, 'REDDIT_USER_AGENT', user_agent)

            print(f'Saved refresh_token to {env_path}')
