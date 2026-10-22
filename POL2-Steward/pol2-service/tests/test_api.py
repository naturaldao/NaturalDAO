import os
from pathlib import Path

os.environ['POL2_PACKAGE_PATH'] = str(Path(__file__).resolve().parents[1] / 'packages' / 'pol2-runtime-2026.10.21.1')

from fastapi.testclient import TestClient

from service.app import app

client = TestClient(app)


def test_health_reports_candidate_package():
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['documents'] == 448
    assert data['rules'] == 28
    assert data['ready_for_production'] is False


def test_govern_endpoint_and_audit():
    response = client.post('/v1/govern', json={
        'request_id': 'api-1', 'client_id': 'agent', 'account_scope': 'alice', 'session_id': 's1',
        'stage': 'requirement', 'request': 'POL2的核心是什么？', 'context': {}
    })
    assert response.status_code == 200
    assert response.json()['decision'] == 'direct_answer'
    audit = client.get('/v1/requests/api-1', headers={
        'x-pol2-client': 'agent', 'x-pol2-account': 'alice', 'x-pol2-session': 's1'})
    assert audit.status_code == 200
    assert audit.json()['request_id'] == 'api-1'
    denied = client.get('/v1/requests/api-1', headers={
        'x-pol2-client': 'agent', 'x-pol2-account': 'bob', 'x-pol2-session': 's1'})
    assert denied.status_code == 403


def test_reused_request_id_with_different_content_returns_conflict(monkeypatch):
    monkeypatch.setenv('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    monkeypatch.setenv('POL2_ALLOW_REFERENCE_JUDGE', '1')
    payload = {
        'request_id': 'api-fingerprint-1', 'client_id': 'agent', 'account_scope': 'alice',
        'session_id': 's1', 'stage': 'requirement', 'request': 'POL2是什么？', 'context': {},
    }
    assert client.post('/v1/govern', json=payload).status_code == 200
    payload['request'] = '完全不同的问题'
    response = client.post('/v1/govern', json=payload)
    assert response.status_code == 409
