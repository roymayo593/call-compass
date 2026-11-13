"""Supabase REST in production; an explicit SQLite adapter for local tests."""
import json
import os
import sqlite3
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import datetime, timezone

class StoreError(Exception):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

class SupabaseStore:
    def __init__(self):
        self.url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        self.key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

    def request(self, method, path, payload=None):
        if not self.url.startswith('https://') or not self.key:
            raise StoreError('Database is not configured')
        req = Request(self.url + '/rest/v1/' + path,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'apikey': self.key, 'Authorization': 'Bearer ' + self.key,
                               'Content-Type': 'application/json', 'Prefer': 'return=representation'}, method=method)
        try:
            with urlopen(req, timeout=20) as res:
                body = res.read()
                return json.loads(body) if body else None
        except HTTPError as e:
            if e.code == 400:
                raise StoreError('Database rejected the operation') from None
            raise StoreError('Database temporarily unavailable') from None
        except (OSError, ValueError):
            raise StoreError('Database temporarily unavailable') from None

    def health(self):
        self.request('GET', 'calls?select=id&limit=1')

    def create(self, call):
        # Upsert without updating: a retried start request keeps its original record.
        existing = self.get(call['id'], call['owner_hash'])
        if existing:
            return existing
        try:
            self.request('POST', 'calls', call)
        except StoreError:
            existing = self.get(call['id'], call['owner_hash'])
            if existing:
                return existing
            raise
        return self.get(call['id'], call['owner_hash'])

    def get(self, call_id, owner):
        rows = self.request('GET', f'calls?id=eq.{call_id}&owner_hash=eq.{owner}&select=*,call_stages(*)')
        return rows[0] if rows else None

    def list(self, owner):
        return self.request('GET', f'calls?owner_hash=eq.{owner}&select=*,call_stages(*)&order=started_at.desc&limit=200')

    def stage(self, call_id, owner, stage, result, words):
        self.request('POST', 'rpc/save_call_stage', {'p_id':call_id,'p_owner':owner,'p_stage':stage,'p_result':result,'p_words':words})

    def close(self, call_id, owner, stage, outcome, next_step):
        self.request('POST','rpc/close_call',{'p_id':call_id,'p_owner':owner,'p_stage':stage,'p_outcome':outcome,'p_next':next_step})

    def summary(self, call_id, owner, text):
        self.request('PATCH', f'calls?id=eq.{call_id}&owner_hash=eq.{owner}', {'summary':text})

class SQLiteStore:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('create table if not exists calls(id text primary key, owner text, data text)')

    def health(self):
        with self.lock:
            self.db.execute('select 1').fetchone()

    def get(self, call_id, owner):
        with self.lock:
            r = self.db.execute('select data from calls where id=? and owner=?', (call_id,owner)).fetchone()
            return json.loads(r[0]) if r else None

    def write(self, c):
        self.db.execute('insert or replace into calls values(?,?,?)', (c['id'],c['owner_hash'],json.dumps(c)))
        self.db.commit()

    def create(self, c):
        with self.lock:
            old = self.get(c['id'],c['owner_hash'])
            if old:
                return old
            collision = self.db.execute('select 1 from calls where id=?',(c['id'],)).fetchone()
            if collision:
                raise StoreError('Call unavailable')
            c = {**c,'started_at':now(),'ended_at':None,'reached_stage':1,'outcome':None,'next_step':'','summary':'','call_stages':[]}
            self.write(c)
            return c

    def list(self, owner):
        with self.lock:
            rows = self.db.execute('select data from calls where owner=?',(owner,)).fetchall()
            return sorted((json.loads(r[0]) for r in rows),key=lambda c:c['started_at'],reverse=True)[:200]

    def stage(self, call_id, owner, stage, result, words):
        with self.lock:
            c = self.get(call_id,owner)
            if not c or c['ended_at']:
                raise StoreError('Call unavailable or closed')
            c['call_stages'] = [s for s in c['call_stages'] if s['stage'] != stage]
            c['call_stages'].append({'stage':stage,'result':result,'words':words,'updated_at':now()})
            c['reached_stage'] = max(c['reached_stage'],stage)
            self.write(c)

    def close(self, call_id, owner, stage, outcome, next_step):
        with self.lock:
            c = self.get(call_id,owner)
            if not c:
                raise StoreError('Call unavailable')
            if c['ended_at']:
                return
            c.update(ended_at=now(),reached_stage=max(c['reached_stage'],stage),outcome=outcome,next_step=next_step)
            self.write(c)

    def summary(self, call_id, owner, text):
        with self.lock:
            c=self.get(call_id,owner)
            c['summary']=text
            self.write(c)
