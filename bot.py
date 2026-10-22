#!/usr/bin/env python3
"""Dava Insta Bot: private Telegram inbox for ordered Instagram TXT batches."""
import asyncio
import fcntl
import hashlib
import io
import json
import logging
import secrets
import shutil
from pathlib import Path

from telegram import Update
from telegram.error import RetryAfter, TelegramError
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from core import MAX_INPUT, decode_text, parse_links
from downloader import MAX_UPLOAD, download
from store import Store

ROOT = Path(__file__).resolve().parent
DATA = ROOT/'data'
HELP = ('Dava Insta Bot 📥\n\nInstagram post yoki Reels linkini yuboring. '
        'Ko‘p link bo‘lsa, .txt fayl yuboring (har qatorda bitta link).\n\n'
        '/status — navbat holati\n/cancel — barcha joriy va kutilayotgan ishlarni to‘xtatish\n'
        '/retry — oldingi xatoli postlardan yangi navbat yaratish\n/help — yordam\n\n'
        'Rasm va videolar asl fayl sifatida yuboriladi. Profil va kolleksiya linklari qabul qilinmaydi.')


def digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


class InstaBot:
    def __init__(self, config, store):
        self.config, self.store = config, store
        self.cancelled = asyncio.Event()
        self.stop = asyncio.Event()
        self.task = None
        self.active = None
        self.send_lock = asyncio.Lock()
        self.last_send = 0.0
        self.wake = asyncio.Event()

    async def send(self, action):
        async with self.send_lock:
            loop = asyncio.get_running_loop()
            await asyncio.sleep(max(0, 1.1-(loop.time()-self.last_send)))
            for attempt in range(3):
                try:
                    # Telegram limits message start frequency, not the time after an upload.
                    self.last_send = loop.time()
                    return await action()
                except RetryAfter as exc:
                    if attempt == 2:
                        raise
                    delay = exc.retry_after
                    await asyncio.sleep((delay.total_seconds() if hasattr(delay,'total_seconds') else delay)+1)

    async def message(self, app, chat, text):
        return await self.send(lambda: app.bot.send_message(chat_id=chat, text=text))

    def authorized(self, update):
        return bool(update.effective_user and update.effective_chat and
                    update.effective_chat.type == 'private' and
                    update.effective_user.id == self.store.owner)

    async def start(self, update, context):
        if not update.effective_chat or update.effective_chat.type != 'private':
            return
        if self.store.owner is None:
            code = context.args[0] if context.args else ''
            if not secrets.compare_digest(code, self.config['pair_code']):
                await self.message(context.application, update.effective_chat.id,
                                   'Bu shaxsiy bot. Linux terminalida ko‘rsatilgan /start KOD buyrug‘ini yuboring.')
                return
            self.store.claim(update.effective_user.id)
        if self.authorized(update):
            await self.message(context.application, update.effective_chat.id, HELP)

    async def help(self, update, context):
        if self.authorized(update):
            await self.message(context.application, update.effective_chat.id, HELP)

    async def status(self, update, context):
        if self.authorized(update):
            counts = self.store.counts()
            lines = ['📊 Umumiy tarix va navbat:']
            for state, label in [('pending','Kutmoqda'),('running','Yuklanmoqda'),('success','Tayyor'),
                                 ('partial','Qisman'),('failed','Xato'),('cancelled','To‘xtatilgan')]:
                lines.append(f'{label}: {counts.get(state,0)}')
            if self.active:
                lines.append('\nJoriy post: '+self.active['url'])
            await self.message(context.application, update.effective_chat.id, '\n'.join(lines))

    async def cancel(self, update, context):
        if self.authorized(update):
            self.cancelled.set()
            n = self.store.cancel()
            self.wake.set()
            await self.message(context.application, update.effective_chat.id,
                               f'{n} ta ish to‘xtatildi. Boshlangan Telegram yuborishi tugashi mumkin.')

    async def submit(self, update, context, text):
        links, ignored = parse_links(text)
        if not links:
            await self.message(context.application, update.effective_chat.id,
                               'Post/Reels linki topilmadi. /p/… yoki /reel/… linklarini yuboring; profil linklari ishlanmaydi.')
            return
        batch, count = self.store.enqueue(update.update_id, update.effective_chat.id, links)
        self.wake.set()
        await self.message(context.application, update.effective_chat.id,
                           f'📥 #{batch}: {count} ta takrorlanmagan post navbatga olindi.\n'
                           f'Qabul qilinmagan profil/boshqa Instagram linklari: {ignored}.\n/status — holat, /cancel — to‘xtatish.')

    async def text(self, update, context):
        if self.authorized(update):
            try:
                await self.submit(update, context, update.effective_message.text)
            except ValueError as exc:
                await self.message(context.application, update.effective_chat.id, str(exc))

    async def document(self, update, context):
        if not self.authorized(update):
            return
        doc = update.effective_message.document
        if not (doc.file_name or '').lower().endswith('.txt'):
            await self.message(context.application, update.effective_chat.id, 'Faqat .txt fayl yuboring.')
            return
        if doc.file_size is None or doc.file_size > MAX_INPUT:
            await self.message(context.application, update.effective_chat.id, 'TXT fayl 1 MB dan kichik bo‘lsin.')
            return
        try:
            file = await doc.get_file()
            raw = await file.download_as_bytearray()
            await self.submit(update, context, decode_text(raw))
        except ValueError as exc:
            await self.message(context.application, update.effective_chat.id, str(exc))

    async def retry(self, update, context):
        if self.authorized(update):
            urls = self.store.failures()
            if urls:
                await self.submit(update, context, '\n'.join(urls))
            else:
                await self.message(context.application, update.effective_chat.id, 'Qayta urinish uchun xatoli post yo‘q.')

    async def prepare(self, job):
        folder = DATA/'work'/str(job['id'])
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, mode=0o700)
        return await download(job['url'], folder, self.cancelled, self.config.get('browser',''))

    async def process(self, app, job, prepared=None):
        folder = DATA/'work'/str(job['id'])
        try:
            files, note = await self.prepare(job) if prepared is None else prepared
            sent, failed = 0, 0
            for path in files:
                if self.cancelled.is_set():
                    break
                if path.stat().st_size > MAX_UPLOAD:
                    failed += 1
                    note = '49 MB dan katta fayl yuborilmadi.'
                    continue
                digest = await asyncio.to_thread(digest_file, path)
                if self.store.delivered(job['id'], digest):
                    sent += 1
                    continue
                number = self.store.media_number(job['id'], digest)
                try:
                    # Reopen on an explicit RetryAfter; do not auto-retry ambiguous upload timeouts.
                    async def upload(p=path):
                        with p.open('rb') as stream:
                            return await app.bot.send_document(chat_id=job['chat'], document=stream,
                                filename=f'{number:03d}_{p.name}', caption=f"📥 #{number}\n{job['url']}",
                                connect_timeout=30, write_timeout=180, read_timeout=180)
                    await self.send(upload)
                    self.store.mark_delivered(job['id'], digest)
                    sent += 1
                except TelegramError:
                    failed += 1
                    note = 'Telegramga yuborishda xato; ayrim fayllar yetib bormagan bo‘lishi mumkin.'
            if self.cancelled.is_set():
                self.store.set_state(job['id'], 'cancelled', 'Foydalanuvchi to‘xtatdi')
            elif sent and not failed and not note:
                self.store.set_state(job['id'], 'success')
            else:
                self.store.set_state(job['id'], 'partial' if sent else 'failed', note or 'Media yuborilmadi.')
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    async def reports(self, app):
        for batch in self.store.finished():
            rows = self.store.report(batch['id'])
            good = sum(r['state']=='success' for r in rows)
            partial = sum(r['state']=='partial' for r in rows)
            bad = sum(r['state']=='failed' for r in rows)
            cancelled = sum(r['state']=='cancelled' for r in rows)
            await self.message(app, batch['chat'], f"✅ #{batch['id']} navbat yakunlandi.\n"
                               f'Postlar: {len(rows)}\nTayyor: {good}\nQisman: {partial}\n'
                               f'Xato: {bad}\nTo‘xtatilgan: {cancelled}\n'
                               'Xatoli postlar uchun /retry yuborishingiz mumkin.')
            problems = [r for r in rows if r['state'] != 'success']
            if problems:
                report = '\n\n'.join(f"{r['url']}\n{r['state']}: {r['note']}" for r in problems)
                async def upload_report():
                    return await app.bot.send_document(chat_id=batch['chat'],
                        document=io.BytesIO(report.encode('utf-8')), filename=f"xatolar_{batch['id']}.txt")
                await self.send(upload_report)
            self.store.notified(batch['id'])

    async def discard_prefetch(self, item):
        if item is None:
            return
        job, task = item
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self.store.requeue_running(job['id'])
        shutil.rmtree(DATA/'work'/str(job['id']), ignore_errors=True)

    async def worker(self, app):
        # One download runs ahead while the previous post uploads to Telegram.
        # Only one Instagram download at a time; delivery remains in input order.
        prefetched = None
        try:
            while not self.stop.is_set():
                job = None
                task = None
                try:
                    self.wake.clear()
                    if self.cancelled.is_set():
                        await self.discard_prefetch(prefetched)
                        prefetched = None
                        self.cancelled.clear()
                    await self.reports(app)
                    if prefetched:
                        job, task = prefetched
                        prefetched = None
                    else:
                        job = self.store.take()
                        if job:
                            task = asyncio.create_task(self.prepare(job))
                    if not job:
                        await self.wake.wait()
                        continue
                    self.active = job
                    prepared = await task
                    if self.cancelled.is_set():
                        self.store.set_state(job['id'], 'cancelled', 'Foydalanuvchi to‘xtatdi')
                        continue
                    next_job = self.store.take()
                    if next_job:
                        prefetched = (next_job, asyncio.create_task(self.prepare(next_job)))
                    await self.process(app, job, prepared=prepared)
                except asyncio.CancelledError:
                    if job:
                        self.store.requeue_running(job['id'])
                    raise
                except Exception as exc:
                    logging.warning('Worker error class: %s', type(exc).__name__)
                    if job:
                        if self.cancelled.is_set():
                            self.store.set_state(job['id'], 'cancelled', 'Foydalanuvchi to‘xtatdi')
                        else:
                            self.store.set_state(job['id'], 'failed', 'Ichki yoki tarmoq xatosi. /retry bilan qayta urinib ko‘ring.')
                    await asyncio.sleep(2)
                finally:
                    if job:
                        shutil.rmtree(DATA/'work'/str(job['id']), ignore_errors=True)
                    self.active = None
        finally:
            await self.discard_prefetch(prefetched)

    async def init(self, app):
        # An old webhook must not prevent polling; no Telegram account login is used.
        await app.bot.delete_webhook(drop_pending_updates=False)
        self.task = asyncio.create_task(self.worker(app))
        print(f'Bot ishga tushdi: https://t.me/{app.bot.username}', flush=True)
        if self.store.owner is None:
            print('Telegramda botga buni yuboring: /start '+self.config['pair_code'], flush=True)

    async def shutdown(self, app):
        self.stop.set()
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def error(self, update, context):
        # Never log the HTTP URL or raw exceptions: the URL contains the bot token.
        logging.warning('Telegram handler error class: %s', type(context.error).__name__)
        if isinstance(update, Update) and self.authorized(update):
            try:
                await self.message(context.application, update.effective_chat.id,
                                   'Tarmoq yoki Telegram xatosi. /status bilan navbatni tekshiring.')
            except TelegramError:
                pass


def main():
    import os
    os.umask(0o077)
    DATA.mkdir(mode=0o700, exist_ok=True)
    lock = (DATA/'bot.lock').open('w')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Bot allaqachon ishlayapti. Ikkinchi nusxani ishga tushirmang.')
    config_path = DATA/'config.json'
    if not config_path.exists():
        raise SystemExit('Avval bash install.sh buyrug‘ini ishlating.')
    config = json.loads(config_path.read_text())
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    logging.getLogger('httpx').disabled = True
    logging.getLogger('httpcore').disabled = True
    service = InstaBot(config, Store(DATA/'queue.sqlite'))
    app = (Application.builder().token(config['token']).connect_timeout(30).read_timeout(30)
           .write_timeout(180).post_init(service.init).post_stop(service.shutdown).build())
    for name, action in [('start',service.start),('help',service.help),('status',service.status),
                         ('cancel',service.cancel),('retry',service.retry)]:
        app.add_handler(CommandHandler(name, action))
    app.add_handler(MessageHandler(filters.Document.ALL, service.document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.text))
    app.add_error_handler(service.error)
    try:
        app.run_polling(allowed_updates=['message'], drop_pending_updates=False, bootstrap_retries=3)
    except Exception as exc:
        print(f'Bot to‘xtadi ({type(exc).__name__}). Internetni va BotFather tokenini tekshiring.')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
