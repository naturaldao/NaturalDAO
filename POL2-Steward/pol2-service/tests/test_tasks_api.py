from fastapi.testclient import TestClient

from service.app import app


client = TestClient(app)


def test_task_api_lifecycle(monkeypatch):
    monkeypatch.setenv('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    monkeypatch.setenv('POL2_ALLOW_REFERENCE_JUDGE', '1')
    created = client.post('/v1/tasks', json={
        'name': 'documentation-site',
        'goal': '为社区做一个公开的志愿服务网站。',
        'context': {'scope': 'development'},
        'client_id': 'agent',
        'account_scope': 'workspace',
        'session_id': 'api-session-1',
    })
    assert created.status_code == 200, created.text
    body = created.json()
    task_id = body['task']['id']
    run_id = body['run']['id']
    assert body['task']['status'] == 'pending_conditions'

    activated = client.post(f'/v1/tasks/{task_id}/activate', json={'condition_evidence': {'authorized': True}})
    assert activated.status_code == 200, activated.text
    assert activated.json()['status'] == 'active'

    step = client.post(f'/v1/tasks/{task_id}/steps', json={
        'run_id': run_id,
        'request': '生成页面结构',
        'context': {'scope': 'development'},
        'kind': 'model',
        'client_id': 'agent',
        'account_scope': 'workspace',
        'session_id': 'api-session-1',
    })
    assert step.status_code == 200, step.text
    assert step.json()['decision']['decision'] == 'allow'

    delivered = client.post(f'/v1/tasks/{task_id}/deliver', json={
        'run_id': run_id,
        'output': '解释这段Python函数的实现。',
        'context': {'scope': 'development'},
        'client_id': 'agent',
        'account_scope': 'workspace',
        'session_id': 'api-session-1',
    })
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()['task']['status'] == 'delivered'

    timeline = client.get(f'/v1/tasks/{task_id}/timeline')
    assert timeline.status_code == 200
    assert timeline.json()['cards']


def test_permit_consume_api(monkeypatch):
    monkeypatch.setenv('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    monkeypatch.setenv('POL2_ALLOW_REFERENCE_JUDGE', '1')
    decision = client.post('/v1/govern/operation', json={
        'request_id': 'api-permit-consume-1',
        'client_id': 'agent',
        'account_scope': 'workspace',
        'session_id': 'api-session-2',
        'operation': '部署社区志愿服务网站到测试环境',
        'context': {'environment': 'test', 'reviewed': True},
    })
    assert decision.status_code == 200, decision.text
    token = decision.json()['release']['token']
    consumed = client.post('/v1/permits/consume', json={
        'token': token,
        'content': '部署社区志愿服务网站到测试环境',
        'stage': 'operation',
        'request_id': 'api-permit-consume-1',
        'conditions_satisfied': True,
    })
    assert consumed.status_code == 200, consumed.text
    assert consumed.json()['status'] == 'consumed'
    replay = client.post('/v1/permits/consume', json={
        'token': token,
        'content': '部署社区志愿服务网站到测试环境',
        'stage': 'operation',
        'request_id': 'api-permit-consume-1',
        'conditions_satisfied': True,
    })
    assert replay.status_code == 400
