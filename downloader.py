"""Bounded subprocess download; no shell, no user gallery-dl configuration."""
import asyncio
import shutil
import sys
from pathlib import Path

MEDIA = {'.mp4', '.mov', '.webm', '.mkv', '.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}
MAX_UPLOAD = 49_000_000
MAX_WORK = 600_000_000


async def download(url, directory, cancelled, browser=''):
    directory = Path(directory)
    if shutil.disk_usage(directory).free < 1_000_000_000:
        return [], 'Diskda kamida 1 GB bo‘sh joy kerak.'
    args = [sys.executable, '-m', 'gallery_dl', '--config-ignore', '--no-input',
            '--no-colors', '--no-postprocessors', '--restrict-filenames', 'ascii',
            '--directory', str(directory), '--filename', '{id}_{num:03}.{extension}',
            '--filesize-max', str(MAX_UPLOAD), '--retries', '2', '--http-timeout', '25']
    if browser == 'firefox':
        args += ['--cookies-from-browser', 'firefox/instagram.com']
    args += [url]
    log = directory/'download.log'
    reason = ''
    with log.open('wb') as output:
        process = await asyncio.create_subprocess_exec(*args, stdout=output, stderr=asyncio.subprocess.STDOUT)
        waiter = asyncio.create_task(process.wait())
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 300
            while loop.time() < deadline:
                if waiter.done():
                    break
                if cancelled.is_set():
                    reason = 'To‘xtatildi.'
                    break
                if sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()) > MAX_WORK:
                    reason = 'Bir post uchun vaqtinchalik disk limiti oshdi.'
                    break
                if shutil.disk_usage(directory).free < 200_000_000:
                    reason = 'Diskda bo‘sh joy tugayapti.'
                    break
                # Wake as soon as the child exits, rather than polling once per second.
                await asyncio.wait({waiter}, timeout=0.2)
            else:
                reason = 'Postni yuklash 5 daqiqadan oshdi.'
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(asyncio.shield(waiter), 5)
                except asyncio.TimeoutError:
                    process.kill()
                    await waiter
            else:
                await waiter
    # Never ship .part, logs, cookies or arbitrary files returned by a tool.
    files = sorted(p for p in directory.iterdir() if p.is_file() and not p.is_symlink() and p.suffix.lower() in MEDIA and p.stat().st_size > 0)
    if not reason:
        with log.open('rb') as handle:
            handle.seek(max(0, log.stat().st_size-16000))
            tail = handle.read().decode('utf-8', errors='replace').lower()
        if '429' in tail or 'rate limit' in tail:
            reason = 'Instagram so‘rovlarni vaqtincha chekladi. Keyinroq qayta urinib ko‘ring.'
        elif 'login' in tail or 'authentication' in tail or 'cookies' in tail or '401' in tail:
            reason = 'Instagram kirishni talab qildi. Linux’da Firefox ulanishini sozlang.'
        elif 'filesize' in tail or 'file size' in tail:
            reason = 'Ayrim fayllar Telegram uchun belgilangan 49 MB limitidan katta.'
        elif process.returncode != 0:
            reason = 'Instagram postni bermadi: yopiq/o‘chirilgan post yoki yuklash xatosi.'
        elif not files:
            reason = 'Media topilmadi. Post yopiq, o‘chirilgan yoki Instagram kirishni talab qilmoqda.'
    return files, reason
