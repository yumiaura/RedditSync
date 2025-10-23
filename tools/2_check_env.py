#!/usr/bin/env python3
"""Check presence and format of key variables in .env file
"""
import os
from dotenv import load_dotenv

load_dotenv()

required = [
    'REDDIT_CLIENT_ID',
    'REDDIT_CLIENT_SECRET',
    'REDDIT_USER_AGENT',
]

optional = [
    'REDDIT_REFRESH_TOKEN',
    'REDDIT_USERNAME',
    'REDDIT_PASSWORD',
    'DB_PATH',
    'MEDIA_DIR',
    'REDIRECT_PORT',
]

def status_ok(name):
    v = os.getenv(name)
    if v is None or v == '':
        return False, None
    return True, v

def main():
    print('Checking .env...')
    errors = []
    for k in required:
        ok, v = status_ok(k)
        if ok:
            print(f'[OK]     {k} = {v}')
        else:
            print(f'[ERROR]  {k} is missing or empty')
            errors.append(k)

    print('\nOptional/recommended:')
    for k in optional:
        ok, v = status_ok(k)
        if ok:
            if k in ('REDDIT_PASSWORD', 'REDDIT_CLIENT_SECRET', 'REDDIT_REFRESH_TOKEN'):
                display = '*** (hidden)'
            else:
                display = v
            print(f'[OK]     {k} = {display}')
        else:
            print(f'[WARN]   {k} is not set')

    if errors:
        print('\nResult: FAILED — fix missing required variables')
        raise SystemExit(2)
    else:
        print('\nResult: OK — required variables present')

if __name__ == '__main__':
    main()
