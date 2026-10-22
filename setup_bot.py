#!/usr/bin/env python3
import argparse
import getpass
import json
import os
import re
import secrets
from pathlib import Path


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--cookies', action='store_true', help='Firefox orqali Instagramga ulanish')
    parser.add_argument('--token', action='store_true', help='Bot tokenini qayta kiritish')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent/'data'
    root.mkdir(mode=0o700, exist_ok=True)
    target = root/'config.json'
    config = json.loads(target.read_text()) if target.exists() else {}
    if not config.get('token') or args.token:
        print('Telegramda @BotFather → /newbot → bot nomi va username tanlang.')
        print('BotFather bergan tokenni shu yerga kiriting. Kiritishda ekranda ko‘rinmaydi.')
        token = getpass.getpass('BOT TOKEN: ').strip()
        if not re.fullmatch(r'\d+:[A-Za-z0-9_-]{20,}', token):
            raise SystemExit('Token shakli noto‘g‘ri. BotFather bergan tokenni to‘liq kiriting.')
        config['token'] = token
    config.setdefault('pair_code', secrets.token_hex(8))
    if args.cookies or 'browser' not in config:
        answer = input('Firefox’da Instagramga kirilgan hisobdan foydalanilsinmi? [h/yo‘q]: ').strip().lower()
        config['browser'] = 'firefox' if answer in ('h','ha','y','yes') else ''
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(config, indent=2)+'\n')
    temp.chmod(0o600)
    temp.replace(target)
    print('\nSozlandi. Botni ishga tushirgach Telegramda yuboring:')
    print('/start '+config['pair_code'])
    print('Keyin instagram_links.txt faylingizni botga yuboring.')


if __name__ == '__main__':
    main()
