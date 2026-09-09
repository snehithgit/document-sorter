"""Small durable state store and crash-safe file publishing."""
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class StateStore:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    def get(self, key):
        with self.connect() as db:
            row = db.execute('SELECT data FROM jobs WHERE id=?', (key,)).fetchone()
        return json.loads(row[0]) if row else {}

    def put(self, key, **changes):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM jobs WHERE id=?', (key,)).fetchone()
            value = json.loads(row[0]) if row else {}
            value.update(changes)
            db.execute('INSERT OR REPLACE INTO jobs VALUES (?, ?)', (key, json.dumps(value)))

    def all(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM jobs')]
