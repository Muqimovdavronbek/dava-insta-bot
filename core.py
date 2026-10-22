"""Instagram-only input parsing; never interprets uploaded text as commands."""
import re
from urllib.parse import urlsplit

MAX_INPUT = 1024 * 1024
MAX_LINKS = 1000
PATTERN = re.compile(r'(?<![\w./])(?:https?://)?(?:www\.|m\.)?instagram\.com/[^\s<>"\\\x00-\x1f]+', re.I)
POST = re.compile(r'^/(p|reel|reels|tv)/([A-Za-z0-9_-]+)/?$')


def parse_links(text):
    links, seen, ignored = [], set(), 0
    for match in PATTERN.finditer(text):
        raw = match.group().rstrip(".,;!)]}’'")
        if not raw.lower().startswith(('http://', 'https://')):
            raw = 'https://' + raw
        parsed = urlsplit(raw)
        if parsed.hostname not in ('instagram.com', 'www.instagram.com', 'm.instagram.com'):
            ignored += 1
            continue
        post = POST.fullmatch(parsed.path)
        if not post:
            ignored += 1
            continue
        kind, code = post.groups()
        kind = 'reel' if kind == 'reels' else kind
        # A shortcode refers to the same media across p/reel/tv URL forms.
        if code not in seen:
            seen.add(code)
            links.append(f'https://www.instagram.com/{kind}/{code}/')
    if len(links) > MAX_LINKS:
        raise ValueError(f'Bir faylda ko‘pi bilan {MAX_LINKS} ta post bo‘lsin. Ro‘yxatni bo‘lib yuboring.')
    return links, ignored


def decode_text(raw):
    if len(raw) > MAX_INPUT:
        raise ValueError('TXT fayl 1 MB dan kichik bo‘lishi kerak.')
    try:
        return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError:
        raise ValueError('TXT faylni UTF-8 formatida saqlang.') from None
