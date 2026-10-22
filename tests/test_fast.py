"""Regression tests for ordered prefetch, stable media numbers and cancellation."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot import InstaBot
from store import Store


class NumberTests(unittest.TestCase):
    def test_numbers_continue_between_posts_and_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'q.sqlite'
            store=Store(path)
            store.enqueue(1,10,['post1','post2'])
            first,second=store.take(),store.take()
            self.assertEqual(store.media_number(first['id'],'a'),1)
            self.assertEqual(store.media_number(first['id'],'b'),2)
            self.assertEqual(store.media_number(second['id'],'c'),3)
            store.db.close()
            store=Store(path)
            self.assertEqual(store.media_number(second['id'],'c'),3)
            self.assertEqual(store.media_number(second['id'],'d'),4)
            store.enqueue(2,10,['post3'])
            third=store.db.execute("SELECT id FROM jobs WHERE url='post3'").fetchone()[0]
            self.assertEqual(store.media_number(third,'z'),1)
            store.db.close()

    def test_upgrade_accounts_for_previously_delivered_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'q.sqlite'
            store=Store(path)
            store.enqueue(1,10,['post1','post2'])
            first,second=store.take(),store.take()
            store.mark_delivered(first['id'],'a')
            store.mark_delivered(first['id'],'b')
            store.db.close()
            store=Store(path)
            self.assertEqual(store.media_number(second['id'],'c'),3)
            store.db.close()


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.store=Store(self.root/'q.sqlite')
        self.store.enqueue(1,10,['https://www.instagram.com/p/FIRST/',
                                 'https://www.instagram.com/p/SECOND/'])
        self.service=InstaBot({},self.store)
        self.app=SimpleNamespace(bot=SimpleNamespace(send_document=AsyncMock(),send_message=AsyncMock()))
        self.path_patch=patch('bot.DATA',self.root)
        self.path_patch.start()
        async def immediate(action):
            return await action()
        self.service.send=immediate
        self.worker=None

    async def asyncTearDown(self):
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker,return_exceptions=True)
        self.path_patch.stop()
        self.store.db.close()
        self.temp.cleanup()

    async def test_next_download_overlaps_upload_and_every_media_has_unique_number(self):
        second_ready=asyncio.Event()
        finished=asyncio.Event()
        seen=[]
        async def fake_download(url,folder,cancelled,browser):
            files=[]
            for n in range(2 if 'FIRST' in url else 1):
                path=folder/f'{n}.mp4'
                path.write_bytes(f'{url}-{n}'.encode())
                files.append(path)
            if 'SECOND' in url:
                second_ready.set()
            return files,''
        async def upload(**kwargs):
            if not seen:
                # Serial download+upload would deadlock here and fail the test.
                await asyncio.wait_for(second_ready.wait(),1)
            seen.append((kwargs['caption'],kwargs['filename']))
            if len(seen)==3:
                self.service.stop.set()
                finished.set()
        self.app.bot.send_document.side_effect=upload
        with patch('bot.download',side_effect=fake_download):
            self.worker=asyncio.create_task(self.service.worker(self.app))
            await asyncio.wait_for(finished.wait(),2)
            await asyncio.wait_for(self.worker,1)
        self.assertEqual([x[0].splitlines()[0] for x in seen],['📥 #1','📥 #2','📥 #3'])
        self.assertTrue(all('FIRST' in x[0] for x in seen[:2]))
        self.assertIn('SECOND',seen[2][0])
        self.assertEqual([x[1][:4] for x in seen],['001_','002_','003_'])
        self.assertEqual(self.store.counts(),{'success':2})
        self.assertFalse(any((self.root/'work').iterdir()))

    async def test_cancel_stops_prefetch_and_does_not_send_second_post(self):
        uploading=asyncio.Event()
        prefetch_started=asyncio.Event()
        release=asyncio.Event()
        prefetch_cancelled=asyncio.Event()
        async def fake_download(url,folder,cancelled,browser):
            if 'SECOND' in url:
                prefetch_started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    prefetch_cancelled.set()
            path=folder/'one.mp4'
            path.write_bytes(b'first')
            return [path],''
        async def upload(**kwargs):
            uploading.set()
            await release.wait()
        self.app.bot.send_document.side_effect=upload
        with patch('bot.download',side_effect=fake_download):
            self.worker=asyncio.create_task(self.service.worker(self.app))
            await asyncio.wait_for(uploading.wait(),1)
            await asyncio.wait_for(prefetch_started.wait(),1)
            self.service.cancelled.set()
            self.store.cancel()
            release.set()
            await asyncio.wait_for(prefetch_cancelled.wait(),1)
            self.service.stop.set()
            self.service.wake.set()
            await asyncio.wait_for(self.worker,1)
        media = [call.kwargs for call in self.app.bot.send_document.await_args_list if call.kwargs.get('caption')]
        self.assertEqual(len(media),1)
        self.assertIn('FIRST',media[0]['caption'])
        self.assertEqual(self.store.counts(),{'cancelled':2})
        self.assertFalse(any((self.root/'work').iterdir()))

    async def test_shutdown_restores_both_active_and_prefetched_jobs(self):
        uploading=asyncio.Event()
        prefetch_started=asyncio.Event()
        async def fake_download(url,folder,cancelled,browser):
            if 'SECOND' in url:
                prefetch_started.set()
                await asyncio.Event().wait()
            path=folder/'one.mp4'
            path.write_bytes(b'first')
            return [path],''
        async def upload(**kwargs):
            uploading.set()
            await asyncio.Event().wait()
        self.app.bot.send_document.side_effect=upload
        with patch('bot.download',side_effect=fake_download):
            self.worker=asyncio.create_task(self.service.worker(self.app))
            await asyncio.wait_for(uploading.wait(),1)
            await asyncio.wait_for(prefetch_started.wait(),1)
            self.worker.cancel()
            await asyncio.gather(self.worker,return_exceptions=True)
        self.assertEqual(self.store.counts(),{'pending':2})
        self.assertFalse(any((self.root/'work').iterdir()))


if __name__=='__main__':
    unittest.main()
