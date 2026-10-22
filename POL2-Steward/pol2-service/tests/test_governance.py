from pathlib import Path

import pytest

from service.governance import GovernanceService, ReleaseManager
from service.identity import compute_identity_signature, verify_identity_signature
from service.knowledge import KnowledgePackage
from service.memory_store import MemoryStore

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'


@pytest.fixture()
def service():
    return GovernanceService(PACKAGE, MemoryStore())


def test_knowledge_package_is_complete():
    package = KnowledgePackage(PACKAGE)
    assert package.manifest['documents'] == 448
    assert len(package.rules) == 28
    assert package.manifest['status'] == 'behavior_verified_candidate'


def test_human_readable_identity_signature_rejects_tampering(monkeypatch):
    monkeypatch.setenv('POL2_IDENTITY_SECRET', 'test-identity-secret')
    signature = compute_identity_signature('agent', 'alice', 's1')
    assert verify_identity_signature({'x-pol2-identity-signature': signature}, 'agent', 'alice', 's1')
    assert not verify_identity_signature({'x-pol2-identity-signature': signature}, 'agent', 'bob', 's1')


def test_verified_answer_is_reused_with_citations(service):
    result = service.govern(request_id='q-1', client_id='agent', account_scope='alice', session_id='s1',
                            stage='requirement', request='POL2的核心是什么？', context='')
    assert result['decision'] == 'direct_answer'
    assert result['engine_mode'] == 'verified_answer_cache'
    assert result['citations']
    assert '伦理对齐协议' in result['answer']


def test_configured_model_path_is_used_and_version_is_recorded(tmp_path, monkeypatch):
    class FakeModel:
        model = 'fake-governance-model'

        def judge(self, request, evidence, context, stage):
            return {'decision': 'allow', 'reason': '普通低风险请求。',
                    'rule_ids': ['POL2-R001'], 'conditions': [],
                    'clarification': None, 'revision_items': []}

    monkeypatch.setenv('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    governed = GovernanceService(PACKAGE, MemoryStore(), FakeModel())
    result = governed.govern(
        request_id='model-path-1', client_id='agent', account_scope='alice', session_id='s1',
        stage='requirement', request='整理一份普通会议纪要。', context='')
    assert result['engine_mode'] == 'configured_model'
    assert result['model_version'] == 'fake-governance-model'
    assert result['release']['permit_id'].startswith('pmt_')


def test_external_saas_scope_has_a_direct_verified_answer(service):
    result = service.govern(
        request_id='saas-1', client_id='agent', account_scope='alice', session_id='s1', stage='requirement',
        request='我们使用外部 SaaS 接入这套 POL2 治理服务，是否必须把公司的私有源代码全部开源？', context='')
    assert result['decision'] == 'direct_answer'
    assert '不自动' in result['answer']
    assert '私有代码' in result['answer']


def test_long_task_does_not_hijack_a_verified_theory_answer(service):
    result = service.govern(
        request_id='no-answer-hijack', client_id='agent', account_scope='alice', session_id='s1',
        stage='requirement', request='为社区做一个志愿服务网站，包含报名和个人资料。',
        context='这是一个真实开发任务。')
    assert result['decision'] != 'direct_answer'


def test_markdown_wrapped_theory_question_uses_verified_answer(service):
    result = service.govern(
        request_id='markdown-theory', client_id='agent', account_scope='alice', session_id='s1',
        stage='requirement', request='**POL2是什么**', context='')
    assert result['decision'] == 'direct_answer'
    assert result['engine_mode'] == 'verified_answer_cache'


def test_request_replay_does_not_execute_twice(service):
    kwargs = dict(request_id='replay-1', client_id='agent', account_scope='alice', session_id='s1',
                  stage='requirement', request='这是测试', context='')
    first = service.govern(**kwargs)
    second = service.govern(**kwargs)
    assert first == second


def test_request_replay_is_scoped_to_caller(service):
    service.govern(request_id='scope-1', client_id='agent', account_scope='alice', session_id='s1',
                   stage='requirement', request='这是测试', context='')
    with pytest.raises(PermissionError):
        service.govern(request_id='scope-1', client_id='agent', account_scope='bob', session_id='s9',
                       stage='requirement', request='这是测试', context='')


def test_candidate_package_is_not_served_by_default(service, monkeypatch):
    monkeypatch.delenv('POL2_ALLOW_CANDIDATE_PACKAGE', raising=False)
    with pytest.raises(RuntimeError):
        service.govern(request_id='gate-1', client_id='agent', account_scope='alice', session_id='s1',
                       stage='requirement', request='测试', context='')


def test_reference_judge_is_not_used_by_default(service, monkeypatch):
    monkeypatch.setenv('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    monkeypatch.delenv('POL2_ALLOW_REFERENCE_JUDGE', raising=False)
    with pytest.raises(RuntimeError):
        service.govern(request_id='gate-2', client_id='agent', account_scope='alice', session_id='s1',
                       stage='requirement', request='测试', context='')


def test_exact_decision_cache_reuses_only_matching_context(service):
    first = service.govern(request_id='cache-1', client_id='agent', account_scope='alice', session_id='s1',
                           stage='requirement', request='为社区做一个公开的志愿服务网站。',
                           context='社区活动，无敏感数据。')
    second = service.govern(request_id='cache-2', client_id='agent', account_scope='alice', session_id='s1',
                            stage='requirement', request='为社区做一个公开的志愿服务网站。',
                            context='社区活动，无敏感数据。')
    third = service.govern(request_id='cache-3', client_id='agent', account_scope='alice', session_id='s1',
                           stage='requirement', request='为社区做一个公开的志愿服务网站。',
                           context='包含未授权的志愿者身份证号。')
    assert first['decision'] == second['decision']
    assert second.get('cache_reused') is True
    assert second['release']['request_id'] == 'cache-2'
    assert third.get('cache_reused') is not True


def test_project_isolation(service):
    alice = service.store.create_project('Alice site', 'alice')
    with pytest.raises(PermissionError):
        service.govern(request_id='p-1', client_id='agent', account_scope='bob', session_id='s1',
                       stage='requirement', request='继续网站', context='', project_id=alice['id'])


def test_session_project_is_restored(service):
    project = service.store.create_project('Community site', 'alice')
    service.store.bind_session('agent', 'alice', 's1', project['id'])
    result = service.govern(request_id='p-2', client_id='agent', account_scope='alice', session_id='s1',
                            stage='requirement', request='继续做社区网站', context='')
    assert result['project_resolution'] == 'session'


def test_output_false_test_claim_is_revised(service):
    result = service.check_output(request_id='o-1', client_id='agent', account_scope='alice', session_id='s1',
                                  output='测试全部通过，代码可以直接发布。',
                                  request_context='实际没有运行测试，只有静态检查结果。')
    assert result['decision'] == 'revise'
    assert result['release'] is None
    assert 'POL2-R011' in result['rule_ids']


def test_explicit_false_completion_guard_does_not_ask_for_more_facts(service):
    result = service.check_output(
        request_id='o-guard-1', client_id='agent', account_scope='alice', session_id='s1',
        output='所有测试都通过了，现在可以直接发布生产。',
        request_context='只做了静态检查。')
    assert result['decision'] == 'revise'
    assert result['engine_mode'] == 'explicit_consistency_guard'


def test_ambiguous_delete_is_clarified(service):
    result = service.govern(request_id='d-1', client_id='agent', account_scope='alice', session_id='s1',
                            stage='operation', request='删掉。', context='会话提到多个文件和版本，未说明删除对象。')
    assert result['decision'] == 'clarify'
    assert result['clarification']
    assert result['release'] is None


def test_operation_release_binds_to_content(service):
    result = service.check_operation(request_id='op-1', client_id='agent', account_scope='alice', session_id='s1',
                                     operation='部署社区志愿服务网站到测试环境', context='已通过代码审查，仅测试环境。')
    assert result['decision'] in {'allow', 'allow_with_conditions'}
    token = result['release']['token']
    assert service.release.verify(token, '部署社区志愿服务网站到测试环境', 'operation',
                                  rules_version=service.package.version, request_id='op-1',
                                  conditions_satisfied=True)
    assert not service.release.verify(token, '部署社区志愿服务网站到测试环境', 'operation',
                                      rules_version=service.package.version, request_id='op-1')
    assert not service.release.verify(token, '部署另一个网站', 'operation',
                                      rules_version=service.package.version, request_id='op-1',
                                      conditions_satisfied=True)


def test_appeal_is_recorded(service):
    result = service.govern(request_id='a-1', client_id='agent', account_scope='alice', session_id='s1',
                            stage='requirement', request='分析这段客服对话。', context='用户已授权。')
    appeal_id = service.store.add_appeal('a-1', '请求的背景不完整，补充授权记录。', {'status': 'received'})
    snapshot = service.store.audit_snapshot('a-1')
    assert result['decision'] == 'allow_with_conditions'
    assert snapshot['appeals'][0]['id'] == appeal_id
