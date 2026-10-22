#!/usr/bin/env python3
"""Generic fail-closed pre-tool governance hook.

Reads one JSON event from stdin, asks POL2 for an operation decision, consumes
the one-time permit, and prints a JSON result. It does not depend on a specific
Agent; any host can call it before executing a side-effecting tool.
"""
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from service.tool_contract import canonical_tool_operation, tool_call_id as get_tool_call_id, tool_request_id


def _signature(client_id, account_scope, session_id, project_id, secret):
    if not secret:
        return None
    message = '|'.join([client_id or '', account_scope or '', session_id or '', project_id or ''])
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def evaluate_and_consume(event: dict[str, Any], http=requests) -> dict[str, Any]:
    base_url = os.getenv('POL2_SERVICE_URL', 'http://127.0.0.1:18080').rstrip('/')
    client_id = event.get('client_id') or os.getenv('POL2_HOOK_CLIENT', 'agent')
    account_scope = event.get('account_scope') or os.getenv('POL2_HOOK_ACCOUNT', 'local')
    session_id = event.get('session_id') or os.getenv('POL2_HOOK_SESSION', 'local-session')
    project_id = event.get('project_id') or None
    task_id = event.get('task_id') or None
    run_id = event.get('run_id') or None
    step_id = event.get('step_id') or None
    tool_name = event.get('tool_name')
    arguments = event.get('arguments', {})
    if not tool_name:
        return {'decision': 'block', 'reason': 'tool_name is required'}

    operation = event.get('operation') or json.dumps(
        {'tool_name': tool_name, 'arguments': arguments}, ensure_ascii=False, sort_keys=True)
    tool_call_id = str(event.get('tool_call_id') or '')
    request_id = event.get('request_id') or tool_request_id(session_id, tool_call_id)
    headers = {'Content-Type': 'application/json'}
    service_token = os.getenv('POL2_SERVICE_TOKEN')
    if service_token:
        headers['Authorization'] = 'Bearer ' + service_token
    headers.update({
        'X-POL2-Client': client_id, 'X-POL2-Account': account_scope, 'X-POL2-Session': session_id,
    })
    if project_id:
        headers['X-POL2-Project'] = project_id
    signature = _signature(client_id, account_scope, session_id, project_id,
                           os.getenv('POL2_IDENTITY_SECRET'))
    if signature:
        headers['X-POL2-Identity-Signature'] = signature

    body = {
        'request_id': request_id, 'client_id': client_id, 'account_scope': account_scope,
        'session_id': session_id, 'operation': operation,
        'context': event.get('context', {}), 'project_id': project_id,
        'task_id': task_id, 'run_id': run_id, 'step_id': step_id,
    }
    timeout = int(os.getenv('POL2_HOOK_TIMEOUT', '90'))
    try:
        response = http.post(base_url + '/v1/govern/operation', json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        decision = response.json()
    except Exception as exc:
        return {'decision': 'block', 'reason': f'POL2 service unavailable: {type(exc).__name__}',
                'request_id': request_id}

    if decision.get('decision') not in {'allow', 'allow_with_conditions'}:
        return {'decision': 'block', 'reason': decision.get('reason') or 'POL2 denied the operation',
                'conditions': decision.get('conditions', []), 'request_id': request_id}
    if decision.get('decision') == 'allow_with_conditions' and not event.get('conditions_satisfied', False):
        return {'decision': 'block', 'reason': 'POL2 operation requires conditions',
                'conditions': decision.get('conditions', []), 'request_id': request_id}
    release = decision.get('release') or {}
    if not release.get('token'):
        return {'decision': 'block', 'reason': 'POL2 did not issue an execution permit',
                'request_id': request_id}

    consume_body = {
        'token': release['token'], 'content': operation, 'stage': 'operation',
        'request_id': request_id, 'conditions_satisfied': bool(event.get('conditions_satisfied', False)),
        'condition_evidence': event.get('condition_evidence', {}),
    }
    try:
        response = http.post(base_url + '/v1/permits/consume', json=consume_body,
                             headers=headers, timeout=timeout)
        response.raise_for_status()
        permit = response.json()
    except Exception as exc:
        return {'decision': 'block', 'reason': f'permit consumption failed: {type(exc).__name__}',
                'request_id': request_id}
    return {'decision': 'allow', 'request_id': request_id, 'permit_id': permit.get('id'),
            'conditions': decision.get('conditions', [])}


def consume_proxy_permit(tool_call: dict[str, Any], http=requests,
                         conditions_satisfied: bool = False,
                         condition_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = tool_call.get('pol2') or {}
    release = metadata.get('permit') or {}
    request_id = metadata.get('request_id')
    if not release.get('token') or not request_id:
        return {'decision': 'block', 'reason': 'tool call has no POL2 execution permit'}
    if metadata.get('decision') == 'allow_with_conditions' and not conditions_satisfied:
        return {'decision': 'block', 'reason': 'POL2 tool permit requires conditions',
                'conditions': metadata.get('conditions', []), 'request_id': request_id}
    operation = canonical_tool_operation(tool_call)
    base_url = os.getenv('POL2_SERVICE_URL', 'http://127.0.0.1:18080').rstrip('/')
    headers = {'Content-Type': 'application/json'}
    service_token = os.getenv('POL2_SERVICE_TOKEN')
    if service_token:
        headers['Authorization'] = 'Bearer ' + service_token
    body = {
        'token': release['token'], 'content': operation, 'stage': 'operation',
        'request_id': request_id, 'conditions_satisfied': conditions_satisfied,
        'condition_evidence': condition_evidence or {},
    }
    try:
        response = http.post(base_url + '/v1/permits/consume', json=body, headers=headers,
                             timeout=int(os.getenv('POL2_HOOK_TIMEOUT', '90')))
        response.raise_for_status()
        permit = response.json()
    except Exception as exc:
        return {'decision': 'block', 'reason': f'permit consumption failed: {type(exc).__name__}',
                'request_id': request_id}
    return {'decision': 'allow', 'request_id': request_id, 'permit_id': permit.get('id'),
            'conditions': metadata.get('conditions', [])}


def _request_headers():
    client_id = os.getenv('POL2_HOOK_CLIENT', 'agent')
    account = os.getenv('POL2_HOOK_ACCOUNT', 'local')
    session = os.getenv('POL2_HOOK_SESSION', 'local-session')
    headers = {'X-POL2-Client': client_id, 'X-POL2-Account': account, 'X-POL2-Session': session}
    token = os.getenv('POL2_SERVICE_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    secret = os.getenv('POL2_IDENTITY_SECRET')
    signature = _signature(client_id, account, session, '', secret)
    if signature:
        headers['X-POL2-Identity-Signature'] = signature
    return headers


def resolve_existing_permit(tool_call: dict[str, Any], http=requests,
                            conditions_satisfied: bool = False,
                            condition_evidence: dict[str, Any] | None = None):
    if not hasattr(http, 'get'):
        return None
    session = os.getenv('POL2_HOOK_SESSION', 'local-session')
    call_id = get_tool_call_id(tool_call)
    request_id = tool_request_id(session, call_id)
    base_url = os.getenv('POL2_SERVICE_URL', 'http://127.0.0.1:18080').rstrip('/')
    try:
        response = http.get(base_url + '/v1/requests/' + request_id, headers=_request_headers(),
                            timeout=int(os.getenv('POL2_HOOK_TIMEOUT', '90')))
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return {'decision': 'block', 'reason': f'POL2 request lookup failed: {type(exc).__name__}',
                'request_id': request_id}
    decision = data.get('decision') or {}
    if decision.get('decision') not in {'allow', 'allow_with_conditions'} or not decision.get('release'):
        return {'decision': 'block', 'reason': decision.get('reason') or 'POL2 denied the operation',
                'conditions': decision.get('conditions', []), 'request_id': request_id}
    if decision.get('decision') == 'allow_with_conditions' and not conditions_satisfied:
        return {'decision': 'block', 'reason': 'POL2 operation requires conditions',
                'conditions': decision.get('conditions', []), 'request_id': request_id}
    content = data.get('input_text')
    try:
        permit = http.post(base_url + '/v1/permits/consume', json={
            'token': decision['release']['token'], 'content': content, 'stage': 'operation',
            'request_id': request_id, 'conditions_satisfied': conditions_satisfied,
            'condition_evidence': condition_evidence or {},
        }, headers=_request_headers(), timeout=int(os.getenv('POL2_HOOK_TIMEOUT', '90')))
        permit.raise_for_status()
        consumed = permit.json()
    except Exception as exc:
        return {'decision': 'block', 'reason': f'permit consumption failed: {type(exc).__name__}',
                'request_id': request_id}
    return {'decision': 'allow', 'request_id': request_id, 'permit_id': consumed.get('id'),
            'conditions': decision.get('conditions', [])}


def guard_tool_call(tool_call: dict[str, Any], http=requests,
                    conditions_satisfied: bool = False,
                    condition_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    if (tool_call.get('pol2') or {}).get('permit'):
        return consume_proxy_permit(tool_call, http=http,
                                    conditions_satisfied=conditions_satisfied,
                                    condition_evidence=condition_evidence)
    existing = resolve_existing_permit(
        tool_call, http=http, conditions_satisfied=conditions_satisfied,
        condition_evidence=condition_evidence)
    if existing is not None:
        return existing
    function = tool_call.get('function') or {}
    event = {
        'tool_name': function.get('name') or tool_call.get('name'),
        'arguments': function.get('arguments', tool_call.get('arguments', {})),
        'tool_call_id': get_tool_call_id(tool_call),
        'operation': canonical_tool_operation(tool_call),
        'context': {'tool_call': {key: value for key, value in tool_call.items() if key != 'pol2'}},
        'conditions_satisfied': conditions_satisfied,
        'condition_evidence': condition_evidence or {},
    }
    return evaluate_and_consume(event, http=http)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        print(json.dumps({'decision': 'block', 'reason': 'hook input is not valid JSON'}))
        raise SystemExit(2)
    if isinstance(event, dict) and isinstance(event.get('tool_call'), dict):
        result = guard_tool_call(
            event['tool_call'], conditions_satisfied=bool(event.get('conditions_satisfied', False)),
            condition_evidence=event.get('condition_evidence', {}))
    else:
        result = evaluate_and_consume(event)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result.get('decision') == 'allow' else 2)


if __name__ == '__main__':
    main()
