"""Durable, single-owner job queue. Accessed only on the asyncio main thread."""
import sqlite3


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY, update_id INTEGER UNIQUE,
          chat INTEGER NOT NULL, notified INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, batch INTEGER NOT NULL,
          url TEXT NOT NULL, state TEXT DEFAULT 'pending', note TEXT DEFAULT '',
          UNIQUE(batch, url));
        CREATE TABLE IF NOT EXISTS deliveries(job INTEGER, digest TEXT, PRIMARY KEY(job,digest));
        CREATE TABLE IF NOT EXISTS media_numbers(job INTEGER, digest TEXT, number INTEGER NOT NULL,
          PRIMARY KEY(job,digest));
        ''')
        self.db.execute("UPDATE jobs SET state='pending' WHERE state='running'")
        self.db.commit()
        # Upgrade existing queues without resetting numbering after files were sent.
        old = self.db.execute('SELECT d.job,d.digest FROM deliveries d LEFT JOIN media_numbers n '
                              'ON n.job=d.job AND n.digest=d.digest WHERE n.job IS NULL '
                              'ORDER BY d.job,d.rowid').fetchall()
        for item in old:
            self.media_number(item['job'], item['digest'])

    @property
    def owner(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='owner'").fetchone()
        return int(row[0]) if row else None

    def claim(self, user):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO settings VALUES('owner', ?)", (str(user),))
        return self.owner == user

    def enqueue(self, update_id, chat, urls):
        old = self.db.execute('SELECT id FROM batches WHERE update_id=?', (update_id,)).fetchone()
        if old:
            return old[0], 0
        pending = self.db.execute("SELECT count(*) FROM jobs WHERE state IN ('pending','running')").fetchone()[0]
        if pending + len(urls) > 2000:
            raise ValueError('Navbat to‘lib qoldi. Hozirgi yuklashlar tugashini kuting.')
        with self.db:
            batch = self.db.execute('INSERT INTO batches(update_id,chat) VALUES(?,?)', (update_id, chat)).lastrowid
            self.db.executemany('INSERT INTO jobs(batch,url) VALUES(?,?)', [(batch, u) for u in urls])
        return batch, len(urls)

    def take(self):
        row = self.db.execute("SELECT jobs.*, batches.chat FROM jobs JOIN batches ON batches.id=jobs.batch WHERE state='pending' ORDER BY jobs.id LIMIT 1").fetchone()
        if row:
            self.set_state(row['id'], 'running')
        return row

    def set_state(self, job, state, note=''):
        with self.db:
            self.db.execute('UPDATE jobs SET state=?,note=? WHERE id=?', (state, note, job))

    def cancel(self):
        with self.db:
            result = self.db.execute("UPDATE jobs SET state='cancelled',note='Foydalanuvchi to‘xtatdi' WHERE state IN ('pending','running')")
        return result.rowcount

    def counts(self):
        return dict(self.db.execute('SELECT state,count(*) FROM jobs GROUP BY state').fetchall())

    def failures(self):
        rows = self.db.execute("SELECT j.url FROM jobs j WHERE j.state IN ('failed','partial') AND j.id=(SELECT MAX(k.id) FROM jobs k WHERE k.url=j.url) ORDER BY j.id DESC LIMIT 1000").fetchall()
        return [r[0] for r in rows]

    def delivered(self, job, digest):
        return self.db.execute('SELECT 1 FROM deliveries WHERE job=? AND digest=?', (job,digest)).fetchone() is not None

    def mark_delivered(self, job, digest):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO deliveries VALUES(?,?)', (job,digest))

    def media_number(self, job, digest):
        """Reserve a stable, per-batch number before sending, including after restart."""
        with self.db:
            existing = self.db.execute('SELECT number FROM media_numbers WHERE job=? AND digest=?',
                                       (job, digest)).fetchone()
            if existing:
                return existing[0]
            batch = self.db.execute('SELECT batch FROM jobs WHERE id=?', (job,)).fetchone()[0]
            number = self.db.execute('SELECT COALESCE(MAX(n.number),0)+1 FROM media_numbers n '
                                     'JOIN jobs j ON j.id=n.job WHERE j.batch=?', (batch,)).fetchone()[0]
            self.db.execute('INSERT INTO media_numbers VALUES(?,?,?)', (job, digest, number))
            return number

    def requeue_running(self, job):
        with self.db:
            self.db.execute("UPDATE jobs SET state='pending' WHERE id=? AND state='running'", (job,))

    def finished(self):
        return self.db.execute("SELECT * FROM batches WHERE notified=0 AND NOT EXISTS(SELECT 1 FROM jobs WHERE batch=batches.id AND state IN ('pending','running')) ORDER BY id").fetchall()

    def report(self, batch):
        return self.db.execute('SELECT url,state,note FROM jobs WHERE batch=? ORDER BY id', (batch,)).fetchall()

    def notified(self, batch):
        with self.db:
            self.db.execute('UPDATE batches SET notified=1 WHERE id=?', (batch,))
