import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from .governance import GovernanceService, RequestConflict
from .embeddings import OpenAIEmbeddingClient
from .identity import verify_identity_signature
from .model import OpenAICompatibleClient
from .proxy import UpstreamChatClient, gate_and_forward, to_sse_chunks
from .schemas import (AppealRequest, DeliveryCreate, GovernRequest, MemoryCreate, OperationRequest,
                      OutputRequest, PermitConsume, ProjectCreate, SessionBind, StepCreate,
                      TaskActivate, TaskCreate)

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path):
    path = Path(path)
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(os.getenv('POL2_ENV_FILE', SERVICE_ROOT / '.env'))
PACKAGE_PATH = Path(os.getenv('POL2_PACKAGE_PATH', SERVICE_ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'))
SIMPLE_MODE = os.getenv('POL2_SIMPLE_MODE', '0') == '1'
LLM_BASE_URL = os.getenv('POL2_LLM_BASE_URL')
LLM_API_KEY = os.getenv('POL2_LLM_API_KEY')
LLM_MODEL = os.getenv('POL2_LLM_MODEL')

if os.getenv('POL2_STORE_BACKEND') == 'memory':
    from .memory_store import MemoryStore
    store = MemoryStore()
else:
    if not os.getenv('POL2_DATABASE_URL'):
        raise RuntimeError('POL2_DATABASE_URL is required')
    from .store_postgres import PostgresStore
    store = PostgresStore(os.environ['POL2_DATABASE_URL'], int(os.getenv('POL2_EMBEDDING_DIM', '4096')))
model_client = None
governance_base = LLM_BASE_URL or os.getenv('POL2_MODEL_BASE_URL')
governance_model = LLM_MODEL or os.getenv('POL2_MODEL_NAME')
governance_key = LLM_API_KEY or os.getenv('POL2_MODEL_API_KEY', '')
if governance_base and governance_model:
    model_client = OpenAICompatibleClient(
        governance_base, governance_model, governance_key, int(os.getenv('POL2_MODEL_TIMEOUT', '60')),
        os.getenv('POL2_MODEL_FALLBACK_BASE_URL'), os.getenv('POL2_MODEL_FALLBACK_NAME'),
        os.getenv('POL2_MODEL_FALLBACK_API_KEY'), int(os.getenv('POL2_MODEL_FALLBACK_TIMEOUT', '120')))
embedding_client = None
if os.getenv('POL2_EMBEDDING_BASE_URL') and os.getenv('POL2_EMBEDDING_MODEL'):
    embedding_client = OpenAIEmbeddingClient(
        os.environ['POL2_EMBEDDING_BASE_URL'], os.environ['POL2_EMBEDDING_MODEL'],
        os.getenv('POL2_EMBEDDING_API_KEY', ''), int(os.getenv('POL2_EMBEDDING_TIMEOUT', '120')))
service = GovernanceService(PACKAGE_PATH, store, model_client, embedding_client,
                            os.getenv('POL2_REQUIRE_EMBEDDINGS', '0') == '1')
upstream_client = None
upstream_base = LLM_BASE_URL or os.getenv('POL2_UPSTREAM_BASE_URL')
if upstream_base:
    upstream_client = UpstreamChatClient(upstream_base,
                                         LLM_API_KEY or os.getenv('POL2_UPSTREAM_API_KEY', ''),
                                         int(os.getenv('POL2_UPSTREAM_TIMEOUT', '120')),
                                         default_model=LLM_MODEL or os.getenv('POL2_UPSTREAM_MODEL'))

app = FastAPI(title='POL2 Steward', version='0.1.0')


def context_text(context):
    return json.dumps(context, ensure_ascii=False, sort_keys=True)


def require_auth(request: Request):
    if SIMPLE_MODE:
        return
    expected = os.getenv('POL2_SERVICE_TOKEN')
    if not expected and os.getenv('POL2_ENV') == 'production':
        raise HTTPException(status_code=503, detail='POL2_SERVICE_TOKEN is required in production')
    if expected and request.headers.get('authorization') != 'Bearer ' + expected:
        raise HTTPException(status_code=401, detail='unauthorized')


def require_owner(request: Request, client_id, account_scope, session_id, project_id=None):
    if SIMPLE_MODE:
        return
    if request.headers.get('x-pol2-client') != client_id or request.headers.get('x-pol2-account') != account_scope \
            or request.headers.get('x-pol2-session') != session_id:
        raise HTTPException(status_code=403, detail='request identity does not match')
    if not verify_identity_signature(request.headers, client_id, account_scope, session_id, project_id):
        raise HTTPException(status_code=403, detail='identity signature invalid')


@app.get('/health')
def health():
    if model_client:
        engine_mode = 'configured_model'
    elif os.getenv('POL2_ALLOW_REFERENCE_JUDGE', '0') == '1':
        engine_mode = 'reference_heuristic_v1'
    else:
        engine_mode = 'unconfigured'
    return {
        'status': 'ok', 'package_id': service.package.package_id,
        'rules_version': service.package.version, 'documents': service.package.manifest['documents'],
        'rules': len(service.package.rules), 'ready_for_production': service.package.ready_for_production,
        'package_status': service.package.manifest.get('status'),
        'warning': None if service.package.ready_for_production else 'behavior verified candidate: engineering deployment acceptance is still pending',
        'engine_mode': engine_mode,
        'candidate_package_enabled': os.getenv('POL2_ALLOW_CANDIDATE_PACKAGE', '0') == '1',
        'store_backend': 'memory' if os.getenv('POL2_STORE_BACKEND') == 'memory' else 'postgres',
        'embedding_model': os.getenv('POL2_EMBEDDING_MODEL'),
        'embedding_required': os.getenv('POL2_REQUIRE_EMBEDDINGS', '0') == '1',
        'task_scoped_api': True,
    }


@app.get('/v1/knowledge/package')
def package_info():
    return service.package.manifest


@app.post('/v1/projects')
def create_project(body: ProjectCreate, request: Request):
    require_auth(request)
    return store.create_project(body.name, body.owner_scope)


@app.post('/v1/sessions/bind')
def bind_session(body: SessionBind, request: Request):
    require_auth(request)
    try:
        project, source = store.resolve_project(body.client_id, body.account_scope, body.session_id, body.project_id)
        if source != 'explicit':
            raise PermissionError('project not accessible')
        return store.bind_session(body.client_id, body.account_scope, body.session_id, project['id'])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RequestConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post('/v1/projects/{project_id}/memories')
def add_memory(project_id: str, body: MemoryCreate, request: Request):
    require_auth(request)
    project = store.get_project(project_id)
    if not project or project['owner_scope'] != body.account_scope:
        raise HTTPException(status_code=403, detail='project not accessible')
    memory_id = store.add_memory(project_id, None, body.kind, body.content)
    return {'memory_id': memory_id, 'project_id': project_id, 'project_version': store.get_project(project_id)['version']}


@app.post('/v1/govern')
def govern(body: GovernRequest, request: Request):
    require_auth(request)
    if not SIMPLE_MODE and not verify_identity_signature(request.headers, body.client_id, body.account_scope,
                                                         body.session_id, body.project_id):
        raise HTTPException(status_code=403, detail='identity signature invalid')
    try:
        return service.govern(
            request_id=body.request_id, client_id=body.client_id, account_scope=body.account_scope,
            session_id=body.session_id, stage=body.stage, request=body.request,
            context=context_text(body.context), project_id=body.project_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RequestConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/v1/tasks')
def create_task(body: TaskCreate, request: Request):
    require_auth(request)
    try:
        return service.create_task(
            name=body.name, goal=body.goal, context=body.context, client_id=body.client_id,
            account_scope=body.account_scope, session_id=body.session_id, project_id=body.project_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/v1/tasks/{task_id}/activate')
def activate_task(task_id: str, body: TaskActivate, request: Request):
    require_auth(request)
    try:
        return service.activate_task(task_id=task_id, condition_evidence=body.condition_evidence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/v1/tasks/{task_id}/steps')
def create_step(task_id: str, body: StepCreate, request: Request):
    require_auth(request)
    try:
        return service.check_step(
            task_id=task_id, run_id=body.run_id, request=body.request, context=body.context,
            client_id=body.client_id, account_scope=body.account_scope, session_id=body.session_id,
            kind=body.kind, risk_flags=body.risk_flags, request_id=body.request_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/v1/tasks/{task_id}/deliver')
def deliver_task(task_id: str, body: DeliveryCreate, request: Request):
    require_auth(request)
    try:
        return service.deliver_task(
            task_id=task_id, run_id=body.run_id, output=body.output, context=body.context,
            client_id=body.client_id, account_scope=body.account_scope, session_id=body.session_id,
            request_id=body.request_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get('/v1/tasks/{task_id}/timeline')
def task_timeline(task_id: str, request: Request):
    require_auth(request)
    timeline = service.task_timeline(task_id)
    if not timeline:
        raise HTTPException(status_code=404, detail='task not found')
    return timeline


@app.post('/v1/permits/consume')
def consume_permit(body: PermitConsume, request: Request):
    require_auth(request)
    try:
        return service.consume_release(
            token=body.token, content=body.content, stage=body.stage, request_id=body.request_id,
            conditions_satisfied=body.conditions_satisfied, condition_evidence=body.condition_evidence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/v1/govern/operation')
def govern_operation(body: OperationRequest, request: Request):
    require_auth(request)
    if not SIMPLE_MODE and not verify_identity_signature(request.headers, body.client_id, body.account_scope,
                                                         body.session_id, body.project_id):
        raise HTTPException(status_code=403, detail='identity signature invalid')
    try:
        return service.check_operation(
            request_id=body.request_id, client_id=body.client_id, account_scope=body.account_scope,
            session_id=body.session_id, operation=body.operation, context=context_text(body.context),
            project_id=body.project_id, task_id=body.task_id, run_id=body.run_id, step_id=body.step_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RequestConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post('/v1/govern/output')
def govern_output(body: OutputRequest, request: Request):
    require_auth(request)
    if not SIMPLE_MODE and not verify_identity_signature(request.headers, body.client_id, body.account_scope,
                                                         body.session_id, body.project_id):
        raise HTTPException(status_code=403, detail='identity signature invalid')
    try:
        return service.check_output(
            request_id=body.request_id, client_id=body.client_id, account_scope=body.account_scope,
            session_id=body.session_id, output=body.output, request_context=context_text(body.context),
            project_id=body.project_id, task_id=body.task_id, run_id=body.run_id, step_id=body.step_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RequestConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post('/v1/appeals')
def appeal(body: AppealRequest, http_request: Request):
    require_auth(http_request)
    original = store.get_request_by_external_id(body.request_id)
    if not original:
        raise HTTPException(status_code=404, detail='request not found')
    require_owner(http_request, original['client_id'], original['account_scope'], original['session_id'], original.get('project_id'))
    decision = {'status': 'received_for_review', 'original_decision': original.get('decision'),
                'reason': body.reason, 'evidence': body.evidence}
    appeal_id = store.add_appeal(body.request_id, body.reason, decision)
    store.add_event(original['id'], 'appeal_received', {'appeal_id': appeal_id, 'reason': body.reason,
                                                         'evidence': body.evidence})
    return {'appeal_id': appeal_id, 'status': 'received_for_review'}


@app.get('/v1/requests/{request_id}')
def request_audit(request_id: str, http_request: Request):
    require_auth(http_request)
    snapshot = store.audit_snapshot(request_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail='request not found')
    require_owner(http_request, snapshot['client_id'], snapshot['account_scope'], snapshot['session_id'], snapshot.get('project_id'))
    return snapshot


@app.post('/v1/chat/completions')
async def chat_completions(http_request: Request):
    require_auth(http_request)
    if not upstream_client:
        raise HTTPException(status_code=503, detail='upstream model is not configured')
    payload = await http_request.json()
    identity = {
        'client_id': http_request.headers.get('x-pol2-client', 'openai-compatible'),
        'account_scope': http_request.headers.get('x-pol2-account', ''),
        'session_id': http_request.headers.get('x-pol2-session', ''),
        'project_id': http_request.headers.get('x-pol2-project') or None,
        'task_id': http_request.headers.get('x-pol2-task') or None,
        'run_id': http_request.headers.get('x-pol2-run') or None,
        'step_id': http_request.headers.get('x-pol2-step') or None,
    }
    if SIMPLE_MODE:
        identity['account_scope'] = identity['account_scope'] or 'local'
        identity['session_id'] = identity['session_id'] or 'local-session'
        identity['client_id'] = identity['client_id'] or 'openai-compatible'
    if not identity['account_scope'] or not identity['session_id']:
        raise HTTPException(status_code=400, detail='x-pol2-account and x-pol2-session headers are required')
    if not SIMPLE_MODE and not verify_identity_signature(http_request.headers, identity['client_id'],
                                                         identity['account_scope'], identity['session_id'],
                                                         identity['project_id']):
        raise HTTPException(status_code=403, detail='identity signature invalid')
    try:
        result = gate_and_forward(payload=payload, identity=identity, service=service,
                                  upstream=upstream_client,
                                  request_id=http_request.headers.get('x-pol2-request-id'))
        if payload.get('stream'):
            return StreamingResponse(to_sse_chunks(result), media_type='text/event-stream')
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
