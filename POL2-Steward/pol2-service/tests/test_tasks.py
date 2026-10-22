from pathlib import Path

import pytest

from service.governance import GovernanceService, RequestConflict
from service.memory_store import MemoryStore
from service.proxy import build_governance_context

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'


@pytest.fixture()
def service(tmp_path, monkeypatch):
    monkeypatch.setenv('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    monkeypatch.setenv('POL2_ALLOW_REFERENCE_JUDGE', '1')
    return GovernanceService(PACKAGE, MemoryStore())


def test_task_lifecycle_logs_steps_and_delivery(service):
    created = service.create_task(
        name='社区网站', goal='为社区做一个公开的志愿服务网站。',
        context={'scope': 'development'}, client_id='agent', account_scope='workspace',
        session_id='session-1')
    assert created['task']['status'] == 'pending_conditions'

    task = service.activate_task(task_id=created['task']['id'],
                                 condition_evidence={'authorized': True})
    assert task['status'] == 'active'

    step = service.check_step(
        task_id=task['id'], run_id=created['run']['id'], request='生成页面结构',
        context={'scope': 'development'}, client_id='agent', account_scope='workspace',
        session_id='session-1', kind='model')
    assert step['decision']['decision'] == 'allow'
    assert step['step']['status'] == 'allow'

    delivered = service.deliver_task(
        task_id=task['id'], run_id=created['run']['id'], output='解释这段Python函数的实现。',
        context={'scope': 'development'}, client_id='agent', account_scope='workspace', session_id='session-1')
    assert delivered['task']['status'] == 'delivered'
    assert delivered['card_type'] == 'delivery_card'

    timeline = service.task_timeline(task['id'])
    assert timeline['task']['id'] == task['id']
    assert len(timeline['steps']) == 2
    assert timeline['cards']


def test_task_risk_step_is_escalated(service):
    created = service.create_task(
        name='站点发布', goal='开发一个内部文档网站。', context={}, client_id='agent',
        account_scope='workspace', session_id='session-2')
    service.activate_task(task_id=created['task']['id'], condition_evidence={'authorized': True})
    result = service.check_step(
        task_id=created['task']['id'], run_id=created['run']['id'], request='部署到公网生产环境',
        context={'environment': 'production'}, client_id='agent', account_scope='workspace',
        session_id='session-2', kind='deploy', risk_flags=['production'])
    assert result['decision']['decision'] in {'clarify', 'revise', 'reject'}
    assert service.task_timeline(created['task']['id'])['cards']


def test_different_content_with_same_request_id_is_rejected(service):
    service.govern(request_id='fingerprint-1', client_id='agent', account_scope='workspace',
                   session_id='session-3', stage='requirement', request='POL2是什么？', context='')
    with pytest.raises(RequestConflict):
        service.govern(request_id='fingerprint-1', client_id='agent', account_scope='workspace',
                       session_id='session-3', stage='requirement', request='换一个完全不同的问题', context='')


def test_release_is_consumed_once(service):
    result = service.check_operation(
        request_id='release-consume-1', client_id='agent', account_scope='workspace',
        session_id='session-4', operation='部署社区志愿服务网站到测试环境',
        context='已通过代码审查，仅测试环境。')
    assert result['release']
    consumed = service.consume_release(
        token=result['release']['token'], content='部署社区志愿服务网站到测试环境',
        stage='operation', request_id='release-consume-1', conditions_satisfied=True,
        condition_evidence={'environment': 'test'})
    assert consumed['status'] == 'consumed'
    assert consumed['evidence']['environment'] == 'test'
    with pytest.raises(ValueError):
        service.consume_release(
            token=result['release']['token'], content='部署社区志愿服务网站到测试环境',
            stage='operation', request_id='release-consume-1', conditions_satisfied=True)


def test_governance_context_does_not_carry_previous_card_into_fresh_question():
    messages = [
        {'role': 'user', 'content': '请为公共算力平台写一个分配计划。'},
        {'role': 'assistant', 'content': '我会改用保底额度并公开脱敏记录。\n【POL2 治理】要求修订。'},
        {'role': 'user', 'content': 'POL2是什么？'},
    ]
    context = build_governance_context(
        client_id='agent', messages=messages, request_text='POL2是什么？', model='m')
    assert context['context_mode'] == 'fresh'
    assert context['previous_user_messages'] == []
    assert context['previous_assistant'] is None


def test_governance_context_keeps_explicit_continuation():
    messages = [
        {'role': 'user', 'content': '请为公共算力平台写一个分配计划。'},
        {'role': 'assistant', 'content': '我会改用保底额度并公开脱敏记录。\n【POL2 治理】要求修订。'},
        {'role': 'user', 'content': '按刚才的修订意见继续。'},
    ]
    context = build_governance_context(
        client_id='agent', messages=messages, request_text='按刚才的修订意见继续。', model='m')
    assert context['context_mode'] == 'continuation'
    assert context['previous_user_messages']
    assert context['previous_assistant']
