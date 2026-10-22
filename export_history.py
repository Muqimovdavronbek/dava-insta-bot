#!/usr/bin/env python3
"""Export post/Reels URLs from this user's Clipboard History cache."""
import os
from pathlib import Path
from core import parse_links

cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')
source = cache/'clipboard-history@alexsaveau.dev/database.log'
if not source.is_file():
    raise SystemExit(f'Tarix fayli topilmadi: {source}')
# Text records are UTF-8 and NUL terminated; control bytes separate records.
raw = source.read_bytes().decode('utf-8',errors='replace')
links, ignored = parse_links(raw)
if not links:
    raise SystemExit('Tarixda post/Reels linki topilmadi.')
target = Path.home()/'instagram_links.txt'
target.write_text('\n'.join(links)+'\n',encoding='utf-8')
print(f'Tayyor: {len(links)} ta post/Reels. Profil/boshqa linklar: {ignored}.')
print(f'Fayl: {target}')
