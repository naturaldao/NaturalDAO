"""In-memory test backend. Production uses PostgreSQL only."""
import copy
import uuid
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self):
        self.projects = {}
        self.sessions = {}
        self.requests = {}
        self.request_index = {}
        self.memories = []
        self.cache = {}
        self.appeals = []
        self.events = []
        self.tasks = {}
        self.runs = {}
        self.steps = {}
        self.permits = {}
        self.cards = []

    def create_project(self, name, owner_scope):
        project = {'id': 'prj_' + uuid.uuid4().hex, 'name': name, 'owner_scope': owner_scope,
                   'status': 'active', 'version': 1, 'created_at': utc_now()}
        self.projects[project['id']] = project
        return copy.deepcopy(project)

    def get_project(self, project_id):
        return copy.deepcopy(self.projects.get(project_id))

    def bind_session(self, client_id, account_scope, session_id, project_id):
        key = (client_id, account_scope, session_id)
        self.sessions[key] = {'client_id': client_id, 'account_scope': account_scope,
                              'session_id': session_id, 'project_id': project_id, 'updated_at': utc_now()}
        return self.session_binding(client_id, account_scope, session_id)

    def session_binding(self, client_id, account_scope, session_id):
        return copy.deepcopy(self.sessions.get((client_id, account_scope, session_id)))

    def resolve_project(self, client_id, account_scope, session_id, explicit_project_id=None):
        if explicit_project_id:
            project = self.projects.get(explicit_project_id)
            if not project or project['owner_scope'] != account_scope:
                raise PermissionError('project not found or not accessible')
            return copy.deepcopy(project), 'explicit'
        binding = self.sessions.get((client_id, account_scope, session_id))
        if binding:
            project = self.projects.get(binding['project_id'])
            if project and project['owner_scope'] == account_scope:
                return copy.deepcopy(project), 'session'
        return None, 'one_shot'

    def begin_request(self, request_id, client_id, account_scope, session_id, project_id, stage, input_text, context,
                      input_sha256=None, context_sha256=None, package_id=None, task_id=None, run_id=None, step_id=None):
        if request_id in self.request_index:
            return self.get_request_by_external_id(request_id), False
        row = {'id': 'req_' + uuid.uuid4().hex, 'request_id': request_id, 'client_id': client_id,
               'account_scope': account_scope, 'session_id': session_id, 'project_id': project_id,
               'stage': stage, 'input_text': input_text, 'context': copy.deepcopy(context),
               'input_sha256': input_sha256, 'context_sha256': context_sha256, 'package_id': package_id,
               'task_id': task_id, 'run_id': run_id, 'step_id': step_id, 'status': 'received',
               'decision': None, 'created_at': utc_now()}
        self.requests[row['id']] = row
        self.request_index[request_id] = row['id']
        return copy.deepcopy(row), True

    def get_request(self, internal_id):
        return copy.deepcopy(self.requests.get(internal_id))

    def get_request_by_external_id(self, request_id):
        internal_id = self.request_index.get(request_id)
        return copy.deepcopy(self.requests.get(internal_id)) if internal_id else None

    def latest_request(self, client_id, account_scope, session_id, stage='requirement'):
        rows = [row for row in self.requests.values()
                if row['client_id'] == client_id and row['account_scope'] == account_scope
                and row['session_id'] == session_id and row['stage'] == stage]
        if not rows:
            return None
        row = sorted(rows, key=lambda item: item['created_at'])[-1]
        return {'input_text': row['input_text'], 'context': copy.deepcopy(row['context']),
                'created_at': row['created_at']}

    def finish_request(self, internal_id, status, decision):
        row = self.requests.get(internal_id)
        if not row:
            return
        row['status'] = status
        row['decision'] = copy.deepcopy(decision)

    def add_memory(self, project_id, source_request_id, kind, content, status='valid', scope='project'):
        memory_id = 'mem_' + uuid.uuid4().hex
        self.memories.append({'id': memory_id, 'project_id': project_id,
                              'source_request_id': source_request_id, 'kind': kind, 'content': content,
                              'status': status, 'scope': scope, 'created_at': utc_now()})
        if project_id in self.projects:
            self.projects[project_id]['version'] += 1
        return memory_id

    def project_memories(self, project_id, limit=30):
        rows = [copy.deepcopy(row) for row in self.memories
                if row['project_id'] == project_id and row['status'] == 'valid']
        return list(reversed(rows))[:limit]

    def add_event(self, request_id, event_type, data, task_id=None, run_id=None, step_id=None):
        self.events.append({'request_id': request_id, 'event_type': event_type, 'task_id': task_id,
                            'run_id': run_id, 'step_id': step_id, 'data': copy.deepcopy(data),
                            'created_at': utc_now()})

    def add_appeal(self, request_id, reason, decision):
        appeal_id = 'apl_' + uuid.uuid4().hex
        self.appeals.append({'id': appeal_id, 'request_id': request_id, 'reason': reason,
                             'decision': copy.deepcopy(decision), 'created_at': utc_now()})
        return appeal_id

    def get_cached(self, cache_key):
        row = self.cache.get(cache_key)
        if not row or row['expires_at'] <= utc_now():
            return None
        return copy.deepcopy(row['value'])

    def set_cached(self, cache_key, value, expires_at):
        self.cache[cache_key] = {'value': copy.deepcopy(value), 'expires_at': expires_at}

    def audit_snapshot(self, request_id):
        request = self.get_request_by_external_id(request_id)
        if not request:
            return None
        request['events'] = [copy.deepcopy(row) for row in self.events if row['request_id'] == request['id']]
        request['appeals'] = [copy.deepcopy(row) for row in self.appeals if row['request_id'] == request_id]
        return request

    def create_task(self, name, goal, project_id=None):
        task = {'id': 'task_' + uuid.uuid4().hex, 'project_id': project_id, 'name': name, 'goal': goal,
                'status': 'intake', 'scope': {}, 'conditions': [], 'version': 1,
                'created_at': utc_now(), 'updated_at': utc_now()}
        self.tasks[task['id']] = task
        return copy.deepcopy(task)

    def get_task(self, task_id):
        return copy.deepcopy(self.tasks.get(task_id))

    def set_task_state(self, task_id, status, scope=None, conditions=None):
        task = self.tasks.get(task_id)
        if not task:
            return None
        task['status'] = status
        if scope is not None:
            task['scope'] = copy.deepcopy(scope)
        if conditions is not None:
            task['conditions'] = copy.deepcopy(conditions)
        task['version'] += 1
        task['updated_at'] = utc_now()
        return copy.deepcopy(task)

    def create_run(self, task_id):
        run = {'id': 'run_' + uuid.uuid4().hex, 'task_id': task_id, 'status': 'active',
               'created_at': utc_now(), 'updated_at': utc_now()}
        self.runs[run['id']] = run
        return copy.deepcopy(run)

    def get_run(self, run_id):
        return copy.deepcopy(self.runs.get(run_id))

    def set_run_state(self, run_id, status):
        run = self.runs.get(run_id)
        if run:
            run['status'] = status
            run['updated_at'] = utc_now()
        return copy.deepcopy(run)

    def create_step(self, task_id, run_id, kind, request_id=None, input_sha256=None):
        seq = sum(1 for row in self.steps.values() if row['run_id'] == run_id) + 1
        step = {'id': 'step_' + uuid.uuid4().hex, 'task_id': task_id, 'run_id': run_id, 'seq': seq,
                'kind': kind, 'request_id': request_id, 'input_sha256': input_sha256,
                'status': 'running', 'decision': None, 'created_at': utc_now(), 'ended_at': None}
        self.steps[step['id']] = step
        return copy.deepcopy(step)

    def get_step(self, step_id):
        return copy.deepcopy(self.steps.get(step_id))

    def finish_step(self, step_id, status, decision):
        step = self.steps.get(step_id)
        if step:
            step['status'] = status
            step['decision'] = copy.deepcopy(decision)
            step['ended_at'] = utc_now()
        return copy.deepcopy(step)

    def create_task_permit(self, task_id, run_id, scope, conditions, evidence, ttl_seconds):
        now = datetime.now(timezone.utc)
        permit = {'id': 'pmt_' + uuid.uuid4().hex, 'request_id': None, 'task_id': task_id,
                  'run_id': run_id, 'permit_type': 'task', 'stage': 'task', 'subject_sha256': None,
                  'scope': copy.deepcopy(scope), 'conditions': copy.deepcopy(conditions),
                  'evidence': copy.deepcopy(evidence), 'rules_version': None, 'model_version': None,
                  'status': 'issued', 'issued_at': now.isoformat(),
                  'expires_at': datetime.fromtimestamp(now.timestamp() + ttl_seconds, timezone.utc).isoformat(),
                  'consumed_at': None}
        self.permits[permit['id']] = permit
        return copy.deepcopy(permit)

    def register_permit(self, **permit):
        row = {'id': permit['id'], 'request_id': permit.get('request_id'),
               'task_id': permit.get('task_id'), 'run_id': permit.get('run_id'),
               'permit_type': permit.get('permit_type', 'content'), 'stage': permit.get('stage'),
               'subject_sha256': permit.get('subject_sha256'), 'scope': copy.deepcopy(permit.get('scope', {})),
               'conditions': copy.deepcopy(permit.get('conditions', [])),
               'evidence': copy.deepcopy(permit.get('evidence', {})),
               'rules_version': permit.get('rules_version'), 'model_version': permit.get('model_version'),
               'status': 'issued', 'issued_at': permit['issued_at'], 'expires_at': permit['expires_at'],
               'consumed_at': None}
        self.permits[row['id']] = row
        return copy.deepcopy(row)

    def get_permit(self, permit_id):
        return copy.deepcopy(self.permits.get(permit_id))

    def active_task_permit(self, task_id):
        rows = [row for row in self.permits.values()
                if row['task_id'] == task_id and row['permit_type'] == 'task'
                and row['status'] == 'issued' and row['expires_at'] > utc_now()]
        return copy.deepcopy(sorted(rows, key=lambda row: row['issued_at'])[-1]) if rows else None

    def consume_permit(self, permit_id, subject_sha256, stage, rules_version, evidence=None):
        row = self.permits.get(permit_id)
        if not row or row['status'] != 'issued' or row['subject_sha256'] != subject_sha256 \
                or row['stage'] != stage or row['rules_version'] != rules_version \
                or row['expires_at'] <= utc_now():
            raise ValueError('permit is invalid, expired, already consumed, or does not match the content')
        row['status'] = 'consumed'
        row['consumed_at'] = utc_now()
        if evidence is not None:
            row['evidence'] = copy.deepcopy(evidence)
        return copy.deepcopy(row)

    def add_card_event(self, task_id, run_id, card_type, decision):
        card_id = 'card_' + uuid.uuid4().hex
        self.cards.append({'id': card_id, 'task_id': task_id, 'run_id': run_id,
                           'card_type': card_type, 'decision': copy.deepcopy(decision),
                           'created_at': utc_now()})
        return card_id

    def task_timeline(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return None
        runs = [copy.deepcopy(row) for row in self.runs.values() if row['task_id'] == task_id]
        steps = [copy.deepcopy(row) for row in self.steps.values() if row['task_id'] == task_id]
        permits = [copy.deepcopy(row) for row in self.permits.values() if row['task_id'] == task_id]
        cards = [copy.deepcopy(row) for row in self.cards if row['task_id'] == task_id]
        requests = [copy.deepcopy(row) for row in self.requests.values() if row['task_id'] == task_id]
        events = [copy.deepcopy(row) for row in self.events if row['task_id'] == task_id]
        return {'task': task,
                'runs': sorted(runs, key=lambda row: row['created_at']),
                'steps': sorted(steps, key=lambda row: row['seq']),
                'permits': sorted(permits, key=lambda row: row['issued_at']),
                'cards': sorted(cards, key=lambda row: row['created_at']),
                'requests': sorted(requests, key=lambda row: row['created_at']),
                'events': events}
