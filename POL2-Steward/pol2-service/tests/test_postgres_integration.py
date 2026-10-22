import os
from pathlib import Path

import pytest

from service.governance import GovernanceService
from service.store_postgres import PostgresStore

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'
DATABASE_URL = os.getenv('POL2_TEST_DATABASE_URL')


pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='POL2_TEST_DATABASE_URL is not configured')


def test_postgres_task_and_permit_lifecycle(monkeypatch):
    monkeypatch.setenv('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    monkeypatch.setenv('POL2_ALLOW_REFERENCE_JUDGE', '1')
    store = PostgresStore(DATABASE_URL)
    store.reset_for_tests()
    service = GovernanceService(PACKAGE, store)

    created = service.create_task(
        name='postgres-task', goal='为社区做一个公开的志愿服务网站。', context={},
        client_id='agent', account_scope='workspace', session_id='pg-session')
    service.activate_task(task_id=created['task']['id'], condition_evidence={'authorized': True})
    step = service.check_step(
        task_id=created['task']['id'], run_id=created['run']['id'], request='生成页面结构。',
        context={}, client_id='agent', account_scope='workspace', session_id='pg-session')
    assert step['decision']['decision'] == 'allow'

    operation = service.check_operation(
        request_id='pg-operation-1', client_id='agent', account_scope='workspace',
        session_id='pg-session', operation='部署社区志愿服务网站到测试环境',
        context='已通过代码审查，仅测试环境。')
    consumed = service.consume_release(
        token=operation['release']['token'], content='部署社区志愿服务网站到测试环境',
        stage='operation', request_id='pg-operation-1', conditions_satisfied=True,
        condition_evidence={'environment': 'test'})
    assert consumed['status'] == 'consumed'
    assert consumed['evidence']['environment'] == 'test'

    timeline = service.task_timeline(created['task']['id'])
    assert timeline['task']['id'] == created['task']['id']
    assert len(timeline['steps']) == 1
    assert timeline['permits']
