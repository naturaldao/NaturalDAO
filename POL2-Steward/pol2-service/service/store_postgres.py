import json
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def utc_now():
    return datetime.now(timezone.utc)


class PostgresStore:
    def __init__(self, database_url, embedding_dim=4096):
        self.database_url = database_url
        self.embedding_dim = embedding_dim
        self._init()

    def connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def reset_for_tests(self):
        tables = ('projects,sessions,requests,memories,cache,appeals,events,tasks,runs,steps,permits,card_events')
        with self.connect() as db, db.cursor() as cur:
            cur.execute(f'TRUNCATE {tables} RESTART IDENTITY CASCADE')

    def _init(self):
        with self.connect() as db:
            with db.cursor() as cur:
                try:
                    cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
                    self.vector_available = True
                except Exception:
                    db.rollback()
                    self.vector_available = False
                cur.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                  id text PRIMARY KEY, name text NOT NULL, owner_scope text NOT NULL,
                  status text NOT NULL DEFAULT 'active', version integer NOT NULL DEFAULT 1,
                  created_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                  client_id text NOT NULL, account_scope text NOT NULL, session_id text NOT NULL,
                  project_id text NOT NULL REFERENCES projects(id), updated_at timestamptz NOT NULL,
                  PRIMARY KEY (client_id, account_scope, session_id)
                );
                CREATE TABLE IF NOT EXISTS requests (
                  id text PRIMARY KEY, request_id text NOT NULL UNIQUE,
                  client_id text NOT NULL, account_scope text NOT NULL, session_id text NOT NULL,
                  project_id text REFERENCES projects(id), stage text NOT NULL,
                  input_text text NOT NULL, context_json jsonb NOT NULL,
                  input_sha256 text, context_sha256 text, package_id text,
                  task_id text, run_id text, step_id text,
                  status text NOT NULL, decision_json jsonb, created_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                  id text PRIMARY KEY, project_id text NOT NULL REFERENCES projects(id),
                  source_request_id text, kind text NOT NULL, content text NOT NULL,
                  status text NOT NULL, scope text NOT NULL, created_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cache (
                  cache_key text PRIMARY KEY, response_json jsonb NOT NULL, expires_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS appeals (
                  id text PRIMARY KEY, request_id text NOT NULL, reason text NOT NULL,
                  decision_json jsonb, created_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                  id bigserial PRIMARY KEY, request_id text, event_type text NOT NULL,
                  task_id text, run_id text, step_id text,
                  data_json jsonb NOT NULL, created_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                  id text PRIMARY KEY, project_id text, name text NOT NULL, goal text NOT NULL,
                  status text NOT NULL, scope_json jsonb NOT NULL DEFAULT '{}'::jsonb,
                  conditions_json jsonb NOT NULL DEFAULT '[]'::jsonb, version integer NOT NULL DEFAULT 1,
                  created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                  id text PRIMARY KEY, task_id text NOT NULL REFERENCES tasks(id),
                  status text NOT NULL, created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL
                );
                CREATE TABLE IF NOT EXISTS steps (
                  id text PRIMARY KEY, task_id text NOT NULL REFERENCES tasks(id),
                  run_id text NOT NULL REFERENCES runs(id), seq integer NOT NULL,
                  kind text NOT NULL, request_id text, input_sha256 text,
                  status text NOT NULL, decision_json jsonb, created_at timestamptz NOT NULL, ended_at timestamptz
                );
                CREATE TABLE IF NOT EXISTS permits (
                  id text PRIMARY KEY, request_id text, task_id text, run_id text,
                  permit_type text NOT NULL, stage text NOT NULL, subject_sha256 text,
                  scope_json jsonb NOT NULL DEFAULT '{}'::jsonb,
                  conditions_json jsonb NOT NULL DEFAULT '[]'::jsonb,
                  evidence_json jsonb NOT NULL DEFAULT '{}'::jsonb,
                  rules_version text, model_version text, status text NOT NULL,
                  issued_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, consumed_at timestamptz
                );
                CREATE TABLE IF NOT EXISTS card_events (
                  id text PRIMARY KEY, task_id text NOT NULL REFERENCES tasks(id), run_id text,
                  card_type text NOT NULL, decision_json jsonb NOT NULL, created_at timestamptz NOT NULL
                );
                ''')
                cur.execute('''
                CREATE INDEX IF NOT EXISTS requests_request_id_idx ON requests(request_id);
                CREATE INDEX IF NOT EXISTS memories_project_idx ON memories(project_id, status);
                CREATE INDEX IF NOT EXISTS steps_task_idx ON steps(task_id, seq);
                CREATE INDEX IF NOT EXISTS permits_task_idx ON permits(task_id, status);
                ''')
                if self.vector_available:
                    cur.execute(f'''
                    CREATE TABLE IF NOT EXISTS embeddings (
                      record_id text PRIMARY KEY, record_type text NOT NULL,
                      embedding halfvec({self.embedding_dim}) NOT NULL,
                      embedding_model text NOT NULL, indexed_at timestamptz NOT NULL DEFAULT now()
                    );
                    ''')
                for table, columns in {
                    'requests': {'input_sha256': 'text', 'context_sha256': 'text', 'package_id': 'text',
                                 'task_id': 'text', 'run_id': 'text', 'step_id': 'text'},
                    'events': {'task_id': 'text', 'run_id': 'text', 'step_id': 'text'},
                }.items():
                    for column, declaration in columns.items():
                        cur.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {declaration}')

    def create_project(self, name, owner_scope):
        project_id = 'prj_' + uuid.uuid4().hex
        with self.connect() as db, db.cursor() as cur:
            cur.execute('INSERT INTO projects(id,name,owner_scope,created_at) VALUES (%s,%s,%s,%s)',
                        (project_id, name, owner_scope, utc_now()))
        return self.get_project(project_id)

    def get_project(self, project_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM projects WHERE id=%s', (project_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def bind_session(self, client_id, account_scope, session_id, project_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO sessions(client_id,account_scope,session_id,project_id,updated_at)
                           VALUES (%s,%s,%s,%s,%s) ON CONFLICT(client_id,account_scope,session_id)
                           DO UPDATE SET project_id=excluded.project_id, updated_at=excluded.updated_at''',
                        (client_id, account_scope, session_id, project_id, utc_now()))
        return self.session_binding(client_id, account_scope, session_id)

    def session_binding(self, client_id, account_scope, session_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM sessions WHERE client_id=%s AND account_scope=%s AND session_id=%s',
                        (client_id, account_scope, session_id))
            row = cur.fetchone()
        return dict(row) if row else None

    def resolve_project(self, client_id, account_scope, session_id, explicit_project_id=None):
        if explicit_project_id:
            project = self.get_project(explicit_project_id)
            if not project or project['owner_scope'] != account_scope:
                raise PermissionError('project not found or not accessible')
            return project, 'explicit'
        binding = self.session_binding(client_id, account_scope, session_id)
        if binding:
            project = self.get_project(binding['project_id'])
            if project and project['owner_scope'] == account_scope:
                return project, 'session'
        return None, 'one_shot'

    def begin_request(self, request_id, client_id, account_scope, session_id, project_id, stage, input_text, context,
                      input_sha256=None, context_sha256=None, package_id=None, task_id=None, run_id=None, step_id=None):
        internal_id = 'req_' + uuid.uuid4().hex
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO requests(id,request_id,client_id,account_scope,session_id,project_id,stage,
                           input_text,context_json,input_sha256,context_sha256,package_id,task_id,run_id,step_id,
                           status,created_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (request_id) DO NOTHING
                           RETURNING id''',
                        (internal_id, request_id, client_id, account_scope, session_id, project_id, stage,
                         input_text, Jsonb(context), input_sha256, context_sha256, package_id,
                         task_id, run_id, step_id, 'received', utc_now()))
            created = cur.fetchone() is not None
        if not created:
            return self.get_request_by_external_id(request_id), False
        return self.get_request(internal_id), True

    def get_request(self, internal_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM requests WHERE id=%s', (internal_id,))
            row = cur.fetchone()
        return self._request_dict(row)

    def get_request_by_external_id(self, request_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM requests WHERE request_id=%s', (request_id,))
            row = cur.fetchone()
        return self._request_dict(row)

    def latest_request(self, client_id, account_scope, session_id, stage='requirement'):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''SELECT input_text, context_json, created_at FROM requests
                           WHERE client_id=%s AND account_scope=%s AND session_id=%s AND stage=%s
                           ORDER BY created_at DESC LIMIT 1''',
                        (client_id, account_scope, session_id, stage))
            row = cur.fetchone()
        if not row:
            return None
        item = dict(row)
        value = item.pop('context_json')
        item['context'] = value if isinstance(value, dict) else json.loads(value)
        return item

    @staticmethod
    def _request_dict(row):
        if not row:
            return None
        result = dict(row)
        context = result.pop('context_json')
        decision = result.pop('decision_json')
        result['context'] = context if isinstance(context, dict) else json.loads(context)
        result['decision'] = decision if isinstance(decision, dict) else (json.loads(decision) if decision else None)
        return result

    def finish_request(self, internal_id, status, decision):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('UPDATE requests SET status=%s, decision_json=%s WHERE id=%s',
                        (status, Jsonb(decision), internal_id))

    def add_memory(self, project_id, source_request_id, kind, content, status='valid', scope='project'):
        memory_id = 'mem_' + uuid.uuid4().hex
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO memories(id,project_id,source_request_id,kind,content,status,scope,created_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                        (memory_id, project_id, source_request_id, kind, content, status, scope, utc_now()))
            cur.execute('UPDATE projects SET version=version+1 WHERE id=%s', (project_id,))
        return memory_id

    def project_memories(self, project_id, limit=30):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''SELECT id,source_request_id,kind,content,status,scope,created_at
                           FROM memories WHERE project_id=%s AND status='valid'
                           ORDER BY created_at DESC LIMIT %s''', (project_id, limit))
            return [dict(row) for row in cur.fetchall()]

    def add_event(self, request_id, event_type, data, task_id=None, run_id=None, step_id=None):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO events(request_id,event_type,task_id,run_id,step_id,data_json,created_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)''',
                        (request_id, event_type, task_id, run_id, step_id, Jsonb(data), utc_now()))

    def add_appeal(self, request_id, reason, decision):
        appeal_id = 'apl_' + uuid.uuid4().hex
        with self.connect() as db, db.cursor() as cur:
            cur.execute('INSERT INTO appeals(id,request_id,reason,decision_json,created_at) VALUES (%s,%s,%s,%s,%s)',
                        (appeal_id, request_id, reason, Jsonb(decision), utc_now()))
        return appeal_id

    def get_cached(self, cache_key):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT response_json FROM cache WHERE cache_key=%s AND expires_at > now()', (cache_key,))
            row = cur.fetchone()
        if not row:
            return None
        value = row['response_json']
        return value if isinstance(value, dict) else json.loads(value)

    def set_cached(self, cache_key, value, expires_at):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO cache(cache_key,response_json,expires_at) VALUES (%s,%s,%s)
                           ON CONFLICT(cache_key) DO UPDATE SET response_json=excluded.response_json, expires_at=excluded.expires_at''',
                        (cache_key, Jsonb(value), expires_at))

    def audit_snapshot(self, request_id):
        request = self.get_request_by_external_id(request_id)
        if not request:
            return None
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT event_type,data_json,created_at FROM events WHERE request_id=%s ORDER BY id', (request['id'],))
            events = [dict(row) for row in cur.fetchall()]
            cur.execute('SELECT id,reason,decision_json,created_at FROM appeals WHERE request_id=%s ORDER BY created_at', (request['request_id'],))
            appeals = [dict(row) for row in cur.fetchall()]
        for event in events:
            value = event.pop('data_json')
            event['data'] = value if isinstance(value, dict) else json.loads(value)
        for appeal in appeals:
            value = appeal.pop('decision_json')
            appeal['decision'] = value if isinstance(value, dict) else (json.loads(value) if value else None)
        request['events'] = events
        request['appeals'] = appeals
        return request

    def create_task(self, name, goal, project_id=None):
        task_id = 'task_' + uuid.uuid4().hex
        now = utc_now()
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO tasks(id,project_id,name,goal,status,created_at,updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)''',
                        (task_id, project_id, name, goal, 'intake', now, now))
        return self.get_task(task_id)

    def get_task(self, task_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM tasks WHERE id=%s', (task_id,))
            row = cur.fetchone()
        return self._task_dict(row)

    @staticmethod
    def _task_dict(row):
        if not row:
            return None
        task = dict(row)
        task['scope'] = task.pop('scope_json') or {}
        task['conditions'] = task.pop('conditions_json') or []
        return task

    def set_task_state(self, task_id, status, scope=None, conditions=None):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''UPDATE tasks SET status=%s, scope_json=COALESCE(%s,scope_json),
                           conditions_json=COALESCE(%s,conditions_json), version=version+1, updated_at=%s
                           WHERE id=%s''',
                        (status, Jsonb(scope) if scope is not None else None,
                         Jsonb(conditions) if conditions is not None else None, utc_now(), task_id))
        return self.get_task(task_id)

    def create_run(self, task_id):
        run_id = 'run_' + uuid.uuid4().hex
        now = utc_now()
        with self.connect() as db, db.cursor() as cur:
            cur.execute('INSERT INTO runs(id,task_id,status,created_at,updated_at) VALUES (%s,%s,%s,%s,%s)',
                        (run_id, task_id, 'active', now, now))
        return self.get_run(run_id)

    def get_run(self, run_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM runs WHERE id=%s', (run_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def set_run_state(self, run_id, status):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('UPDATE runs SET status=%s, updated_at=%s WHERE id=%s', (status, utc_now(), run_id))
        return self.get_run(run_id)

    def create_step(self, task_id, run_id, kind, request_id=None, input_sha256=None):
        step_id = 'step_' + uuid.uuid4().hex
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT COALESCE(MAX(seq),0) FROM steps WHERE run_id=%s', (run_id,))
            seq = int(cur.fetchone()['coalesce']) + 1
            cur.execute('''INSERT INTO steps(id,task_id,run_id,seq,kind,request_id,input_sha256,status,created_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                        (step_id, task_id, run_id, seq, kind, request_id, input_sha256, 'running', utc_now()))
        return self.get_step(step_id)

    def get_step(self, step_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM steps WHERE id=%s', (step_id,))
            row = cur.fetchone()
        return self._step_dict(row)

    @staticmethod
    def _step_dict(row):
        if not row:
            return None
        step = dict(row)
        step['decision'] = step.pop('decision_json')
        return step

    def finish_step(self, step_id, status, decision):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('UPDATE steps SET status=%s, decision_json=%s, ended_at=%s WHERE id=%s',
                        (status, Jsonb(decision), utc_now(), step_id))
        return self.get_step(step_id)

    def create_task_permit(self, task_id, run_id, scope, conditions, evidence, ttl_seconds):
        permit_id = 'pmt_' + uuid.uuid4().hex
        issued = utc_now()
        expires_at = datetime.fromtimestamp(issued.timestamp() + ttl_seconds, timezone.utc)
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO permits(id,request_id,task_id,run_id,permit_type,stage,subject_sha256,
                           scope_json,conditions_json,evidence_json,rules_version,model_version,status,issued_at,expires_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                        (permit_id, None, task_id, run_id, 'task', 'task', None,
                         Jsonb(scope), Jsonb(conditions), Jsonb(evidence), None, None, 'issued', issued, expires_at))
        return self.get_permit(permit_id)

    def register_permit(self, **permit):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO permits(id,request_id,task_id,run_id,permit_type,stage,subject_sha256,
                           scope_json,conditions_json,evidence_json,rules_version,model_version,status,issued_at,expires_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                        (permit['id'], permit.get('request_id'), permit.get('task_id'), permit.get('run_id'),
                         permit.get('permit_type', 'content'), permit.get('stage'), permit.get('subject_sha256'),
                         Jsonb(permit.get('scope', {})), Jsonb(permit.get('conditions', [])),
                         Jsonb(permit.get('evidence', {})), permit.get('rules_version'),
                         permit.get('model_version'), 'issued', permit['issued_at'], permit['expires_at']))
        return self.get_permit(permit['id'])

    def get_permit(self, permit_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM permits WHERE id=%s', (permit_id,))
            row = cur.fetchone()
        return self._permit_dict(row)

    @staticmethod
    def _permit_dict(row):
        if not row:
            return None
        permit = dict(row)
        permit['scope'] = permit.pop('scope_json') or {}
        permit['conditions'] = permit.pop('conditions_json') or []
        permit['evidence'] = permit.pop('evidence_json') or {}
        return permit

    def active_task_permit(self, task_id):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''SELECT * FROM permits WHERE task_id=%s AND permit_type='task'
                           AND status='issued' AND expires_at>now() ORDER BY issued_at DESC LIMIT 1''', (task_id,))
            row = cur.fetchone()
        return self._permit_dict(row)

    def consume_permit(self, permit_id, subject_sha256, stage, rules_version, evidence=None):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''UPDATE permits SET status='consumed', consumed_at=now()
                           WHERE id=%s AND status='issued' AND subject_sha256=%s
                           AND stage=%s AND rules_version=%s AND expires_at>now()''',
                        (permit_id, subject_sha256, stage, rules_version))
            if cur.rowcount != 1:
                raise ValueError('permit is invalid, expired, already consumed, or does not match the content')
            if evidence is not None:
                cur.execute('UPDATE permits SET evidence_json=%s WHERE id=%s', (Jsonb(evidence), permit_id))
        return self.get_permit(permit_id)

    def add_card_event(self, task_id, run_id, card_type, decision):
        card_id = 'card_' + uuid.uuid4().hex
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''INSERT INTO card_events(id,task_id,run_id,card_type,decision_json,created_at)
                           VALUES (%s,%s,%s,%s,%s,%s)''',
                        (card_id, task_id, run_id, card_type, Jsonb(decision), utc_now()))
        return card_id

    def task_timeline(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return None
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT * FROM runs WHERE task_id=%s ORDER BY created_at', (task_id,))
            runs = [dict(row) for row in cur.fetchall()]
            cur.execute('SELECT * FROM steps WHERE task_id=%s ORDER BY seq', (task_id,))
            steps = [self._step_dict(row) for row in cur.fetchall()]
            cur.execute('SELECT * FROM permits WHERE task_id=%s ORDER BY issued_at', (task_id,))
            permits = [self._permit_dict(row) for row in cur.fetchall()]
            cur.execute('SELECT * FROM card_events WHERE task_id=%s ORDER BY created_at', (task_id,))
            cards = []
            for row in cur.fetchall():
                item = dict(row)
                item['decision'] = item.pop('decision_json')
                cards.append(item)
            cur.execute('SELECT * FROM requests WHERE task_id=%s ORDER BY created_at', (task_id,))
            requests = [self._request_dict(row) for row in cur.fetchall()]
            cur.execute('SELECT * FROM events WHERE task_id=%s ORDER BY id', (task_id,))
            events = []
            for row in cur.fetchall():
                item = dict(row)
                item['data'] = item.pop('data_json')
                events.append(item)
        return {'task': task, 'runs': runs, 'steps': steps, 'permits': permits,
                'cards': cards, 'requests': requests, 'events': events}

    def replace_embeddings(self, rows, model):
        if not self.vector_available:
            raise RuntimeError('pgvector extension is not available')
        with self.connect() as db, db.cursor() as cur:
            cur.execute('TRUNCATE TABLE embeddings')
            for record_id, record_type, vector in rows:
                cur.execute('''INSERT INTO embeddings(record_id,record_type,embedding,embedding_model)
                               VALUES (%s,%s,%s::halfvec,%s)''',
                            (record_id, record_type, json.dumps(vector), model))

    def vector_search(self, vector, limit=16):
        if not self.vector_available:
            raise RuntimeError('pgvector extension is not available')
        with self.connect() as db, db.cursor() as cur:
            cur.execute('''SELECT record_id, record_type, 1 - (embedding <=> %s::halfvec) AS score
                           FROM embeddings ORDER BY embedding <=> %s::halfvec LIMIT %s''',
                        (json.dumps(vector), json.dumps(vector), limit))
            return [dict(row) for row in cur.fetchall()]
