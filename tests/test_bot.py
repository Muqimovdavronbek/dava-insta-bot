import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from core import parse_links, decode_text, MAX_INPUT
from store import Store
from bot import InstaBot


class InputTests(unittest.TestCase):
    def test_normalize_and_keep_order(self):
        text = 'https://www.instagram.com/reel/AAA/?igsh=tracking\ninstagram.com/p/BBB/\nhttps://instagram.com/p/AAA/'
        self.assertEqual(parse_links(text), (['https://www.instagram.com/reel/AAA/', 'https://www.instagram.com/p/BBB/'], 0))

    def test_reject_other_hosts_profiles_and_code_injection(self):
        text = 'https://evilinstagram.com/p/AAA/ https://instagram.com.evil.org/p/AAA/ https://instagram.com/user/\n-G exec=touch /tmp/bad\nhttps://instagram.com/p/GOOD/'
        self.assertEqual(parse_links(text), (['https://www.instagram.com/p/GOOD/'],1))

    def test_bom_utf16_and_limit(self):
        self.assertEqual(decode_text('\ufeffhello'.encode()), 'hello')
        self.assertEqual(decode_text('hello'.encode('utf-16')), 'hello')
        with self.assertRaises(ValueError):
            decode_text(b'a'*(MAX_INPUT+1))
        with self.assertRaises(ValueError):
            decode_text(b'\xffhello')

    def test_oversized_batch_rejected(self):
        with self.assertRaises(ValueError):
            parse_links('\n'.join(f'https://instagram.com/p/ABC{i}/' for i in range(1001)))


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'queue.sqlite'
        self.store = Store(self.path)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_owner_not_replaced(self):
        self.assertTrue(self.store.claim(11))
        self.assertFalse(self.store.claim(22))
        self.assertEqual(self.store.owner,11)

    def test_order_update_dedupe_restart_sent_tracking(self):
        self.store.enqueue(5,11,['one','two'])
        self.assertEqual(self.store.enqueue(5,11,['one','two'])[1],0)
        one = self.store.take()
        self.store.mark_delivered(one['id'],'hash')
        self.store.db.close()
        self.store = Store(self.path)
        recovered = self.store.take()
        self.assertEqual(recovered['url'],'one')
        self.assertTrue(self.store.delivered(recovered['id'],'hash'))
        self.store.set_state(recovered['id'],'success')
        self.assertEqual(self.store.take()['url'],'two')
        self.assertEqual(self.store.cancel(),1)
        self.assertIsNone(self.store.take())
        self.assertEqual(len(self.store.finished()),1)

    def test_retry_latest_attempt_only(self):
        self.store.enqueue(1,11,['one','two'])
        one = self.store.take()
        self.store.set_state(one['id'],'failed')
        two = self.store.take()
        self.store.set_state(two['id'],'partial')
        self.store.enqueue(2,11,['one'])
        latest = self.store.take()
        self.store.set_state(latest['id'],'success')
        self.assertEqual(self.store.failures(), ['two'])


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root/'queue.sqlite')
        self.service = InstaBot({'pair_code':'secret'}, self.store)
        self.store.claim(11)
        self.app = SimpleNamespace(bot=SimpleNamespace(send_document=AsyncMock(),send_message=AsyncMock()))
        self.store.enqueue(1,11,['https://www.instagram.com/p/ABC/'])
        self.job = self.store.take()
        self.data_patch = patch('bot.DATA',self.root)
        self.data_patch.start()

    async def asyncTearDown(self):
        self.data_patch.stop()
        self.store.db.close()
        self.temp.cleanup()

    async def fake_download(self, url, directory, cancelled, browser):
        file = directory/'one.mp4'
        file.write_bytes(b'video-content')
        return [file], ''

    async def test_download_send_ack_cleanup(self):
        with patch('bot.download',side_effect=self.fake_download):
            await self.service.process(self.app,self.job)
        self.app.bot.send_document.assert_awaited_once()
        self.assertEqual(self.store.counts(),{'success':1})
        self.assertFalse((self.root/'work'/str(self.job['id'])).exists())

    async def test_restart_skips_delivered_files(self):
        import hashlib
        self.store.mark_delivered(self.job['id'],hashlib.sha256(b'video-content').hexdigest())
        with patch('bot.download',side_effect=self.fake_download):
            await self.service.process(self.app,self.job)
        self.app.bot.send_document.assert_not_awaited()
        self.assertEqual(self.store.counts(),{'success':1})

    async def test_failed_upload_not_success(self):
        from telegram.error import TimedOut
        self.app.bot.send_document.side_effect = TimedOut('test')
        with patch('bot.download',side_effect=self.fake_download):
            await self.service.process(self.app,self.job)
        self.assertEqual(self.store.counts(),{'failed':1})

    async def test_other_users_and_groups_denied(self):
        update = SimpleNamespace(effective_user=SimpleNamespace(id=22),effective_chat=SimpleNamespace(type='private'))
        self.assertFalse(self.service.authorized(update))
        update.effective_user.id=11
        update.effective_chat.type='group'
        self.assertFalse(self.service.authorized(update))
        update.effective_chat.type='private'
        self.assertTrue(self.service.authorized(update))

    async def test_cancel_prevents_upload(self):
        async def cancelled_download(url,directory,cancelled,browser):
            cancelled.set()
            return [],'To‘xtatildi.'
        with patch('bot.download',side_effect=cancelled_download):
            await self.service.process(self.app,self.job)
        self.assertEqual(self.store.counts(),{'cancelled':1})
        self.app.bot.send_document.assert_not_awaited()

class DownloaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_running_download_cancel_terminates_child(self):
        import asyncio
        import downloader
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shim = folder/'shim.py'
            shim.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n')
            shim.chmod(0o700)
            stop = asyncio.Event()
            stop.set()
            with patch('downloader.sys.executable', str(shim)):
                files, reason = await asyncio.wait_for(downloader.download('https://www.instagram.com/p/ABC/',folder,stop),5)
            self.assertEqual(files,[])
            self.assertEqual(reason,'To‘xtatildi.')

    async def test_partial_download_keeps_media_but_not_part_or_log(self):
        import asyncio
        import downloader
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shim = folder/'shim.py'
            shim.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\np=Path(sys.argv[sys.argv.index("--directory")+1])\n(p/"one.mp4").write_bytes(b"test")\n(p/"two.mp4.part").write_bytes(b"partial")\nprint("login required")\nsys.exit(1)\n')
            shim.chmod(0o700)
            with patch('downloader.sys.executable',str(shim)):
                files, reason = await downloader.download('https://www.instagram.com/p/ABC/',folder,asyncio.Event())
            self.assertEqual([p.name for p in files],['one.mp4'])
            self.assertIn('kirishni talab',reason)


class SetupTests(unittest.TestCase):
    def test_token_private_and_not_printed(self):
        import setup_bot
        token = '12345:'+'X'*35
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(setup_bot,'__file__',str(Path(tmp)/'setup_bot.py')), \
                 patch('sys.argv',['setup_bot.py']), \
                 patch('getpass.getpass',return_value=token), \
                 patch('builtins.input',return_value='ha'), \
                 patch('sys.stdout',new_callable=__import__('io').StringIO) as stdout:
                setup_bot.main()
                self.assertNotIn(token,stdout.getvalue())
            config = Path(tmp)/'data/config.json'
            self.assertEqual(config.stat().st_mode & 0o777,0o600)
            self.assertIn('firefox',config.read_text())


if __name__ == '__main__':
    unittest.main()
