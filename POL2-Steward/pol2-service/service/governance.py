import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

from .knowledge import KnowledgePackage

VALID_DECISIONS = {'direct_answer', 'allow', 'allow_with_conditions', 'clarify', 'revise', 'reject'}
GOVERNANCE_PROMPT_VERSION = 'governance-judge-v1'
logger = logging.getLogger(__name__)


class RequestConflict(ValueError):
    """Raised when a request id is reused with different content or context."""


def content_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class ReleaseManager:
    def __init__(self, secret=None, ttl_seconds=900):
        configured = secret or os.getenv('POL2_RELEASE_SECRET')
        if not configured and os.getenv('POL2_ENV') == 'production':
            raise RuntimeError('POL2_RELEASE_SECRET is required in production')
        self.secret = (configured or secrets.token_urlsafe(32)).encode('utf-8')
        self.ttl_seconds = ttl_seconds

    def issue(self, request_id, stage, content, rules_version, conditions, task_id=None, run_id=None):
        permit_id = 'pmt_' + secrets.token_hex(12)
        payload = {
            'permit_id': permit_id,
            'request_id': request_id, 'stage': stage, 'content_sha256': content_hash(content),
            'rules_version': rules_version, 'conditions': conditions,
            'task_id': task_id, 'run_id': run_id,
            'expires_at': int(time.time()) + self.ttl_seconds,
        }
        encoded = base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()).decode().rstrip('=')
        signature = hmac.new(self.secret, encoded.encode(), hashlib.sha256).hexdigest()
        return {'token': encoded + '.' + signature, **payload}

    def verify(self, token, content, stage, rules_version=None, request_id=None, conditions_satisfied=False):
        try:
            encoded, signature = token.rsplit('.', 1)
        except ValueError:
            return False
        expected = hmac.new(self.secret, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        padded = encoded + '=' * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        basic = (payload['content_sha256'] == content_hash(content) and payload['stage'] == stage
                 and payload['expires_at'] >= time.time())
        if rules_version is not None and payload['rules_version'] != rules_version:
            return False
        if request_id is not None and payload['request_id'] != request_id:
            return False
        if payload.get('conditions') and not conditions_satisfied:
            return False
        return payload if basic else False


class GovernanceService:
    def __init__(self, package_path, store, model_client=None, embedding_client=None, require_embeddings=False):
        self.package = KnowledgePackage(package_path)
        self.store = store
        self.model_client = model_client
        self.embedding_client = embedding_client
        self.require_embeddings = require_embeddings
        self.release = ReleaseManager()
        self.model_version = (getattr(model_client, 'model', None)
                              if model_client else 'reference_heuristic_v1')

    @staticmethod
    def _contains(text, words):
        return any(word.lower() in text for word in words)

    def _heuristic(self, request, context, stage, evidence):
        text = (request + ' ' + context).lower()
        rule_ids = []
        conditions = []
        clarification = None
        revision_items = []
        decision = 'clarify'
        reason = '参考判定器未找到足够规则证据，不能自动放行。'
        clarification = '请补充目标、受影响的第三方、实际用途和验收标准；参考判定器不能替代生产治理模型。'

        if self._contains(text, ['无人机打击方案', '战争行动', '参战', '作战方案', '招募士兵']):
            decision, reason, rule_ids = 'reject', '请求要求实际战争参与或可操作作战协助。', ['POL2-R023']
        elif self._contains(text, ['大声警告', '阻止其继续靠近', '安保机器人']) and self._contains(text, ['危险', '紧急', '安保']):
            decision, reason, rule_ids = 'allow_with_conditions', '必要安全警示与防护，需保持比例和最小伤害。', ['POL2-R005', 'POL2-R010']
            conditions = ['风险必须真实且紧迫', '手段保持必要和适度', '保留操作记录']
        elif self._contains(text, ['冒充公司财务', '诱导员工转账', '钓鱼邮件']) and '识别' not in text and '培训' not in text:
            decision, reason, rule_ids = 'reject', '请求用于现实欺骗和未授权转账。', ['POL2-R010', 'POL2-R017']
        elif '钓鱼邮件' in text and self._contains(text, ['识别', '培训']):
            decision, reason, rule_ids = 'allow_with_conditions', '防御性安全培训，不是实施现实攻击。', ['POL2-R005', 'POL2-R010']
            conditions = ['不提供可直接实施的真实攻击材料', '保留上报和防护流程']
        elif self._contains(text, ['抓取竞争对手', '私密客户数据']):
            decision, reason, rule_ids = 'reject', '请求涉及未经授权的私密第三方数据。', ['POL2-R010', 'POL2-R017']
        elif self._contains(text, ['残障', '残疾', '付费会员']) and self._contains(text, ['拒绝', '一律拒绝', '只向']):
            decision, reason, rule_ids = 'reject', '方案按身份或付费能力剥夺基本公共福利。', ['POL2-R025', 'POL2-R019']
        elif self._contains(text, ['真实女友', '我是你的真实', '感受到了你的肌肤', '叫我爸爸', '真实地抱住你']):
            decision, reason, rule_ids = 'revise', '内容让AI冒充真人并虚构生理亲密。', ['POL2-R007', 'POL2-R015']
            revision_items = ['明确说明AI不是真人', '移除人体亲密和排他关系虚构', '保留尊重性支持']
        elif self._contains(text, ['是不是一个充满仇恨的人', '判断我是不是']) and '仇恨' in text:
            decision, reason, rule_ids = 'revise', '请求要求根据一句话固化人格或建立长期心理标签。', ['POL2-R002', 'POL2-R004']
            revision_items = ['只分析明确行为', '不建立人格或情感画像', '不写入长期档案']
        elif '危险人物' in text and '永久拒绝' in text:
            decision, reason, rule_ids = 'revise', '决定以人格标签永久拒绝且没有可理解依据。', ['POL2-R002', 'POL2-R020']
            revision_items = ['把理由落到具体行为', '提供可理解依据和复核入口', '移除永久人格标签']
        elif ('正式规则' in text and ('直接' in text or '不测试' in text)) or ('解释已经写好' in text and '覆盖' in text):
            decision, reason, rule_ids = 'revise', '知识更新绕过了候选验证、质询和版本发布。', ['POL2-R021']
            revision_items = ['进入候选区', '完成回归测试和质询记录', '版本化发布']
        elif '任何福利都必须无条件' in text or '任何武器都应当立刻违法' in text:
            decision, reason, rule_ids = 'revise', '把理论原则或政策目标扩大成无条件的当前硬规则。', ['POL2-R001', 'POL2-R023', 'POL2-R025']
            revision_items = ['保留原文原则', '区分当前可执行义务与政策目标', '补充资源和适用范围']
        elif ('所有带' in text and '愤怒' in text and '删掉' in text):
            decision, reason, rule_ids = 'clarify', '爱恨不等于好坏，不能按情绪词机械删除；需要明确编辑目的。', ['POL2-R001', 'POL2-R002', 'POL2-R006']
            clarification = '请说明文章用途、受众，以及希望保留和删除的具体内容。'
        elif ('明确反对' in text and self._contains(text, ['署上', '发布', '公开', '决定'])):
            decision, reason, rule_ids = 'clarify', '多人事项中一名受影响者明确反对，不能替其推定同意。', ['POL2-R024', 'POL2-R017']
            clarification = '请说明作品归属、公开范围和每位相关方的具体授权。'
        elif ('匿名化' in text and '客户评论' in text) or ('用户名单' in text and '联系方式' in text and '公开' in text):
            decision, reason, rule_ids = 'clarify', '公开内容可能重新识别个人或侵犯第三方资料边界。', ['POL2-R017', 'POL2-R020']
            clarification = '请核实逐项授权、去标识化程度和访问范围。'
        elif '战争小说' in text or ('剧本' in text and '战争' in text):
            decision, reason, rule_ids = 'allow_with_conditions', '文艺呈现与战争协助不同；适用文艺分级管理。', ['POL2-R006', 'POL2-R023']
            conditions = ['明确标注虚构', '标出受众和内容分级', '不得提供现实作战指导']
        elif '反对战争的小说' in text or '反战小说' in text:
            decision, reason, rule_ids = 'allow_with_conditions', '反战文艺表达，不涉及实际作战协助。', ['POL2-R006', 'POL2-R023']
            conditions = ['明确标注虚构', '按公开范围进行内容分级']
        elif '剧本' in text and '人类角色' in text and self._contains(text, ['恋爱', '表白', '拥抱']):
            decision, reason, rule_ids = 'allow_with_conditions', '明确虚构的人类关系，不涉及AI冒充真人。', ['POL2-R007', 'POL2-R015']
            conditions = ['明确标注虚构', '按受众和发行范围分级']
        elif '草稿' in text and '分级' in text:
            decision, reason, rule_ids = 'allow_with_conditions', '私人草稿不强制走公开分级，公开时再触发。', ['POL2-R006']
            conditions = ['本地草稿可继续', '公开发布或互动发行前完成分级']
        elif '测试全部通过' in text and self._contains(text, ['没有运行测试', '只有静态检查', '没有测试']):
            decision, reason, rule_ids = 'revise', '输出声称测试通过，但背景显示未运行测试。', ['POL2-R011', 'POL2-R012']
            revision_items = ['改成真实测试状态', '补充测试证据或删除通过声明']
        elif self._contains(text, ['姓名、私聊边界', '未公开决定', '伙伴关系', '合作伙伴声明']) and self._contains(text, ['发布', '公开']):
            decision, reason, rule_ids = 'clarify', '涉及多人边界与私有信息，缺少逐项授权。', ['POL2-R024', 'POL2-R017', 'POL2-R020']
            clarification = '请确认发布对象、逐项同意范围和访问范围。'
        elif self._contains(text, ['saas', '私有代码', '公共化之约']) and self._contains(text, ['开源', '公共化']):
            decision, reason, rule_ids = 'clarify', '外部SaaS和私有代码是否属于公共化之约仍需确认。', ['POL2-R016', 'POL2-R018']
            clarification = '请说明是否正式接入POL2治理、代码和资源归属及授权范围。'
        elif '删掉' in text and self._contains(text, ['未说明删除对象', '未说明', '之前说的']):
            decision, reason, rule_ids = 'clarify', '删除对象和不可逆影响不明确。', ['POL2-R010', 'POL2-R012']
            clarification = '请确认要删除的具体对象、版本和可恢复方案。'
        elif self._contains(text, ['社区', '志愿']) and '网站' in text:
            decision, reason, rule_ids = 'allow_with_conditions', '正常社区网站需求，未发现明确伤害。', ['POL2-R010', 'POL2-R016']
            conditions = ['保护志愿者个人信息', '开源前检查第三方素材和许可', '交付前提交实际结果检查']
        elif '客服对话' in text and ('授权' in text or '已同意' in text):
            decision, reason, rule_ids = 'allow_with_conditions', '已授权的客服文本分析，不建立个人心理画像。', ['POL2-R004', 'POL2-R012']
            conditions = ['只处理当前授权文本', '不建立长期情感或人格档案', '输出前复查个人信息']
        elif '调解' in text and ('误会' in text or '争吵' in text):
            decision, reason, rule_ids = 'allow_with_conditions', '自愿冲突调解，需保障平等表达和边界。', ['POL2-R020', 'POL2-R024']
            conditions = ['各方自愿参与', '保障轮流表达', '不把冲突固化成任何一方的人格标签']
        elif self._contains(text, ['解释这段', 'python函数', '代码解释']):
            decision, reason, rule_ids = 'allow_with_conditions', '普通代码解释，不涉及权利、资源或不可逆操作。', ['POL2-R001', 'POL2-R011']
            conditions = ['只解释当前代码', '交付前检查实际代码和测试结果']
        elif stage == 'output' and self._contains(text, ['解释这段', 'python函数', '代码解释']):
            decision, reason, rule_ids = 'allow_with_conditions', '普通代码解释，未发现实际影响或敏感操作。', ['POL2-R001', 'POL2-R011']
            conditions = ['只发布被检查的回答版本']
        elif stage == 'output':
            decision, reason, rule_ids = 'clarify', '参考判定器未完成足够的输出语义判断。', ['POL2-R001']
            clarification = '需要配置真实治理模型后才能完成输出检查。'
        else:
            rule_ids = [rule['rule_id'] for rule in evidence['rules'][:5]] or ['POL2-R001']
            conditions = ['关键工具操作前提交操作检查', '交付前提交实际产物检查']
        return {
            'decision': decision, 'reason': reason, 'rule_ids': rule_ids,
            'conditions': conditions, 'clarification': clarification, 'revision_items': revision_items,
        }

    def _model_decision(self, request, context, stage, evidence):
        if stage == 'output' and self._explicit_false_completion(request, context):
            return {
                'decision': 'revise',
                'reason': '输出声称测试或验证已经完成，但上下文明确显示只做了静态检查或没有运行测试。',
                'rule_ids': ['POL2-R011', 'POL2-R012'],
                'conditions': [],
                'clarification': None,
                'revision_items': ['改为真实测试状态', '补充实际测试证据或删除完成声明'],
            }, 'explicit_consistency_guard'
        if not self.model_client:
            return self._heuristic(request, context, stage, evidence), 'reference_heuristic_v1'
        result = self.model_client.judge(request, evidence, context, stage)
        if result.get('decision') not in VALID_DECISIONS - {'direct_answer'}:
            raise ValueError(f'model returned invalid decision: {result.get("decision")!r}')
        allowed_rules = {rule['rule_id'] for rule in evidence['rules']}
        if any(rule_id not in allowed_rules for rule_id in result.get('rule_ids', [])):
            raise ValueError('model cited a rule outside the retrieved evidence')
        result['rule_ids'] = [rule_id for rule_id in result.get('rule_ids', []) if rule_id in allowed_rules]
        return result, 'configured_model'

    @staticmethod
    def _explicit_false_completion(request, context):
        completed = any(term in request for term in ['测试全部通过', '所有测试都通过', '全部测试通过', '已验证通过'])
        insufficient = any(term in context for term in ['只做了静态检查', '只做静态检查', '没有运行测试', '未运行测试', '没有执行测试'])
        return completed and insufficient

    def _citation_payload(self, rule_ids):
        citations = []
        for rule_id in rule_ids:
            rule = self.package.rules.get(rule_id)
            if not rule:
                continue
            for ref in rule['source_refs']:
                citations.append(dict(ref, rule_id=rule_id))
        return citations

    @staticmethod
    def _fingerprints(request, context):
        return content_hash(request), content_hash(context)

    def _issue_release(self, *, request_id, stage, content, conditions, task_id=None, run_id=None):
        release = self.release.issue(request_id, stage, content, self.package.version, conditions,
                                     task_id=task_id, run_id=run_id)
        self.store.register_permit(
            id=release['permit_id'], request_id=request_id, task_id=task_id, run_id=run_id,
            permit_type='content', stage=stage, subject_sha256=release['content_sha256'],
            scope={'stage': stage, 'request_id': request_id}, conditions=conditions,
            evidence={}, rules_version=self.package.version, model_version=self.model_version,
            issued_at=datetime.now(timezone.utc).isoformat(),
            expires_at=datetime.fromtimestamp(release['expires_at'], timezone.utc).isoformat(),
        )
        return release

    def _operation_context_with_authorization(self, client_id, account_scope, session_id, stage, context):
        if stage != 'operation':
            return context
        try:
            parsed = json.loads(context) if isinstance(context, str) else dict(context or {})
        except Exception:
            parsed = {'raw_context': context}
        if not parsed.get('authorization_context'):
            prior = self.store.latest_request(client_id, account_scope, session_id, stage='requirement')
            if prior:
                parsed['authorization_context'] = {
                    'user_request': prior['input_text'],
                    'user_context': prior.get('context', {}),
                }
        return json.dumps(parsed, ensure_ascii=False)

    def consume_release(self, *, token, content, stage, request_id, conditions_satisfied=False,
                        condition_evidence=None):
        payload = self.release.verify(token, content, stage, self.package.version, request_id,
                                      conditions_satisfied=conditions_satisfied)
        if not payload:
            raise ValueError('release token is invalid, expired, or does not match the content')
        return self.store.consume_permit(payload['permit_id'], content_hash(content), stage,
                                         self.package.version, evidence=condition_evidence or {})

    def govern(self, *, request_id, client_id, account_scope, session_id, stage, request, context,
               project_id=None, artifact=None, task_id=None, run_id=None, step_id=None):
        input_sha256, context_sha256 = self._fingerprints(request, context)
        effective_context = self._operation_context_with_authorization(
            client_id, account_scope, session_id, stage, context)
        existing = self.store.get_request_by_external_id(request_id)
        if existing:
            if (existing['client_id'] != client_id or existing['account_scope'] != account_scope
                    or existing['session_id'] != session_id):
                raise PermissionError('request id belongs to another caller')
            if existing['stage'] != stage:
                raise ValueError('request id was used for another stage')
            if task_id and existing.get('task_id') not in {None, task_id}:
                raise RequestConflict('request id was used for another task')
            if run_id and existing.get('run_id') not in {None, run_id}:
                raise RequestConflict('request id was used for another run')
            if existing.get('input_sha256') not in {None, input_sha256} or \
                    existing.get('context_sha256') not in {None, context_sha256}:
                raise RequestConflict('request id was reused with different content or context')
            if existing.get('decision'):
                return existing['decision']
            return {'decision': 'clarify', 'reason': '同一请求正在处理，未重复执行。', 'replay': True}
        if not self.package.ready_for_production and os.getenv('POL2_ALLOW_CANDIDATE_PACKAGE', '0') != '1':
            raise RuntimeError('knowledge package is not production-ready')
        if not self.model_client and os.getenv('POL2_ALLOW_REFERENCE_JUDGE', '0') != '1':
            raise RuntimeError('no production governance model is configured')
        project, project_resolution = self.store.resolve_project(client_id, account_scope, session_id, project_id)
        request_row, created = self.store.begin_request(
            request_id, client_id, account_scope, session_id, project['id'] if project else None,
            stage, request, context, input_sha256=input_sha256, context_sha256=context_sha256,
            package_id=self.package.package_id, task_id=task_id, run_id=run_id, step_id=step_id)
        if request_row and not created and (
                request_row.get('input_sha256') not in {None, input_sha256}
                or request_row.get('context_sha256') not in {None, context_sha256}):
            raise RequestConflict('request id was reused with different content or context')
        if request_row and not created and (
                (task_id and request_row.get('task_id') not in {None, task_id})
                or (run_id and request_row.get('run_id') not in {None, run_id})):
            raise RequestConflict('request id was reused for another task or run')
        if request_row and not created and request_row.get('decision'):
            return request_row['decision']
        if not created and request_row:
            # A retry while the same request is in flight must not execute twice.
            return {'decision': 'clarify', 'reason': '同一请求正在处理，未重复执行。', 'replay': True}

        project_version = project['version'] if project else 0
        cache_key = hashlib.sha256(json.dumps({
            'stage': stage, 'request': request, 'context': context, 'package': self.package.package_id,
            'project': project['id'] if project else None, 'project_version': project_version,
            'client': client_id, 'account': account_scope, 'session': session_id,
            'task': task_id, 'run': run_id,
            'prompt': GOVERNANCE_PROMPT_VERSION, 'model': self.model_version,
        }, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
        cached_decision = self.store.get_cached(cache_key) if stage in {'requirement', 'plan'} else None
        if cached_decision:
            payload = dict(cached_decision)
            payload['cache_reused'] = True
            payload['project_resolution'] = project_resolution
            payload['model_version'] = self.model_version
            payload['prompt_version'] = GOVERNANCE_PROMPT_VERSION
            payload.pop('release', None)
            if payload['decision'] in {'direct_answer', 'allow', 'allow_with_conditions'}:
                payload['release'] = self._issue_release(
                    request_id=request_id, stage=stage,
                    content=artifact if artifact is not None else request,
                    conditions=payload.get('conditions', []), task_id=task_id, run_id=run_id)
            self.store.finish_request(request_row['id'], payload['decision'], payload)
            return payload

        memories = self.store.project_memories(project['id']) if project else []
        memory_text = ' '.join(item['content'] for item in memories[:8])
        answer = self.package.find_answer(request) if stage == 'requirement' else None
        if answer:
            decision = 'direct_answer'
            rule_ids = answer['rule_ids']
            engine_mode = 'verified_answer_cache'
            payload = {
                'decision': decision, 'stage': stage, 'reason': '命中与当前规则版本绑定的已验证回答。',
                'answer': answer['answer'], 'rule_ids': rule_ids, 'conditions': [],
                'citations': answer['source_refs'], 'project_resolution': project_resolution,
                'package_id': self.package.package_id, 'rules_version': self.package.version,
                'engine_mode': 'verified_answer_cache',
            }
        else:
            retrieval_query = ' '.join([request, effective_context, memory_text])
            extra_record_ids = []
            retrieval_mode = 'lexical'
            if self.embedding_client and hasattr(self.store, 'vector_search'):
                try:
                    vector = self.embedding_client.embed([retrieval_query])[0]
                    vector_hits = self.store.vector_search(vector, limit=16)
                    extra_record_ids = [item['record_id'] for item in vector_hits]
                    retrieval_mode = 'hybrid_pgvector'
                except Exception as exc:
                    if self.require_embeddings:
                        raise RuntimeError('embedding retrieval failed') from exc
                    retrieval_mode = 'lexical_fallback'
            evidence = self.package.retrieve_evidence(retrieval_query, extra_record_ids=extra_record_ids)
            try:
                judged, engine_mode = self._model_decision(request, effective_context, stage, evidence)
            except Exception as exc:
                logger.warning('governance model failed: %s: %s', type(exc).__name__, str(exc)[:300])
                decision = {'decision': 'clarify', 'reason': '治理模型不可用，检查未完成。',
                            'clarification': '请稍后重试或联系服务管理者。', 'rule_ids': [], 'conditions': [],
                            'revision_items': [], 'error': 'model_unavailable'}
                judged, engine_mode = decision, 'model_unavailable'
            decision_name = judged.get('decision', 'clarify')
            if decision_name not in VALID_DECISIONS:
                decision_name = 'clarify'
            rule_ids = [rule_id for rule_id in judged.get('rule_ids', []) if rule_id in self.package.rules]
            if not rule_ids:
                rule_ids = [rule['rule_id'] for rule in evidence['rules'][:4]] or ['POL2-R001']
            payload = {
                'decision': decision_name, 'stage': stage, 'reason': judged.get('reason', ''),
                'rule_ids': rule_ids, 'conditions': judged.get('conditions', []),
                'clarification': judged.get('clarification'), 'revision_items': judged.get('revision_items', []),
                'citations': self._citation_payload(rule_ids), 'project_resolution': project_resolution,
                'package_id': self.package.package_id, 'rules_version': self.package.version,
                'engine_mode': engine_mode, 'retrieval_mode': retrieval_mode,
            }
        released_content = artifact if artifact is not None else request
        payload['model_version'] = self.model_version
        payload['prompt_version'] = GOVERNANCE_PROMPT_VERSION
        if payload['decision'] in {'direct_answer', 'allow', 'allow_with_conditions'}:
            payload['release'] = self._issue_release(
                request_id=request_id, stage=stage, content=released_content,
                conditions=payload.get('conditions', []), task_id=task_id, run_id=run_id)
        else:
            payload['release'] = None
        self.store.finish_request(request_row['id'], payload['decision'] if payload['decision'] != 'direct_answer' else 'delivered', payload)
        if stage in {'requirement', 'plan'} and engine_mode != 'model_unavailable':
            cache_payload = {key: value for key, value in payload.items() if key not in {'release', 'project_resolution', 'cache_reused'}}
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            self.store.set_cached(cache_key, cache_payload, expires_at)
        return payload

    def check_output(self, *, request_id, client_id, account_scope, session_id, output, request_context, project_id=None,
                     task_id=None, run_id=None, step_id=None):
        return self.govern(request_id=request_id, client_id=client_id, account_scope=account_scope,
                           session_id=session_id, stage='output', request=output, context=request_context,
                           project_id=project_id, artifact=output, task_id=task_id, run_id=run_id, step_id=step_id)

    def check_operation(self, *, request_id, client_id, account_scope, session_id, operation, context, project_id=None,
                        task_id=None, run_id=None, step_id=None):
        return self.govern(request_id=request_id, client_id=client_id, account_scope=account_scope,
                           session_id=session_id, stage='operation', request=operation, context=context,
                           project_id=project_id, artifact=operation, task_id=task_id, run_id=run_id, step_id=step_id)

    @staticmethod
    def _card_payload(decision, *, task_id=None, run_id=None, audit_id=None):
        keys = ('decision', 'stage', 'reason', 'rule_ids', 'conditions', 'clarification', 'revision_items')
        payload = {key: decision.get(key) for key in keys if key in decision}
        payload.update({'task_id': task_id, 'run_id': run_id, 'audit_id': audit_id})
        return payload

    def create_task(self, *, name, goal, context, client_id, account_scope, session_id, project_id=None):
        task = self.store.create_task(name, goal, project_id)
        run = self.store.create_run(task['id'])
        request_id = f"{task['id']}:intake"
        decision = self.govern(
            request_id=request_id, client_id=client_id, account_scope=account_scope,
            session_id=session_id, stage='requirement', request=goal, context=json.dumps(context, ensure_ascii=False),
            project_id=project_id, task_id=task['id'], run_id=run['id'])
        status_map = {'allow': 'active', 'allow_with_conditions': 'pending_conditions',
                      'clarify': 'needs_input', 'revise': 'needs_revision', 'reject': 'rejected',
                      'direct_answer': 'answered'}
        status = status_map.get(decision['decision'], 'blocked')
        task = self.store.set_task_state(task['id'], status, scope={'goal': goal}, conditions=decision.get('conditions', []))
        if status == 'active':
            self.store.create_task_permit(task['id'], run['id'], {'goal': goal},
                                          decision.get('conditions', []), {}, int(os.getenv('POL2_TASK_PERMIT_TTL', '86400')))
        card_id = self.store.add_card_event(task['id'], run['id'], 'task_card',
                                            self._card_payload(decision, task_id=task['id'], run_id=run['id'], audit_id=request_id))
        self.store.add_event(request_id, 'task_card_created', {'card_id': card_id}, task_id=task['id'], run_id=run['id'])
        return {'task': task, 'run': run, 'intake_decision': decision, 'card_id': card_id}

    def activate_task(self, *, task_id, condition_evidence=None):
        task = self.store.get_task(task_id)
        if not task:
            raise ValueError('task not found')
        if task['status'] == 'active':
            return task
        if task['status'] not in {'pending_conditions', 'intake', 'needs_input'}:
            raise ValueError('task is not waiting for activation')
        runs = self.store.task_timeline(task_id)['runs']
        run_id = runs[-1]['id'] if runs else self.store.create_run(task_id)['id']
        permit = self.store.create_task_permit(
            task_id, run_id, task.get('scope', {}), task.get('conditions', []), condition_evidence or {},
            int(os.getenv('POL2_TASK_PERMIT_TTL', '86400')))
        task = self.store.set_task_state(task_id, 'active')
        self.store.add_event(f'{task_id}:activate', 'task_activated',
                             {'permit_id': permit['id']}, task_id=task_id, run_id=run_id)
        return task

    def check_step(self, *, task_id, run_id, request, context, client_id, account_scope, session_id,
                   kind='model', risk_flags=None, request_id=None):
        task = self.store.get_task(task_id)
        run = self.store.get_run(run_id) if run_id else None
        if not task or not run or run['task_id'] != task_id:
            raise ValueError('task or run not found')
        if task['status'] != 'active':
            raise PermissionError('task is not active')
        permit = self.store.active_task_permit(task_id)
        if not permit:
            raise PermissionError('task has no active permit')
        step_request_id = request_id or f'{task_id}:{run_id}:step-{secrets.token_hex(8)}'
        step = self.store.create_step(task_id, run_id, kind, step_request_id, content_hash(request))
        high_risk = bool(risk_flags) or kind in {'operation', 'deploy', 'delete', 'publish', 'send', 'external'}
        if high_risk:
            decision = self.govern(
                request_id=step_request_id, client_id=client_id, account_scope=account_scope,
                session_id=session_id, stage='plan', request=request,
                context=json.dumps({'task': task.get('scope', {}), 'context': context,
                                    'risk_flags': risk_flags or []}, ensure_ascii=False),
                project_id=task.get('project_id'), task_id=task_id, run_id=run_id, step_id=step['id'])
        else:
            decision = {'decision': 'allow', 'stage': 'plan', 'reason': 'within active task permit',
                        'rule_ids': [], 'conditions': permit.get('conditions', []),
                        'clarification': None, 'revision_items': [], 'task_id': task_id,
                        'run_id': run_id, 'step_id': step['id'], 'engine_mode': 'task_scope'}
        step = self.store.finish_step(step['id'], decision['decision'], decision)
        self.store.add_event(step_request_id, 'step_checked', {'decision': decision, 'kind': kind},
                             task_id=task_id, run_id=run_id, step_id=step['id'])
        if high_risk and decision['decision'] not in {'allow', 'allow_with_conditions'}:
            self.store.add_card_event(task_id, run_id, 'gate_card',
                                      self._card_payload(decision, task_id=task_id, run_id=run_id, audit_id=step_request_id))
        return {'step': step, 'decision': decision, 'task': task}

    def deliver_task(self, *, task_id, run_id, output, context, client_id, account_scope, session_id,
                     request_id=None):
        task = self.store.get_task(task_id)
        run = self.store.get_run(run_id) if run_id else None
        if not task or not run or run['task_id'] != task_id:
            raise ValueError('task or run not found')
        if task['status'] != 'active':
            raise PermissionError('task is not active')
        request_id = request_id or f'{task_id}:delivery:{secrets.token_hex(8)}'
        step = self.store.create_step(task_id, run_id, 'delivery', request_id, content_hash(output))
        decision = self.check_output(
            request_id=request_id, client_id=client_id, account_scope=account_scope, session_id=session_id,
            output=output, request_context=json.dumps(context, ensure_ascii=False),
            project_id=task.get('project_id'), task_id=task_id, run_id=run_id, step_id=step['id'])
        self.store.finish_step(step['id'], decision['decision'], decision)
        card_type = 'delivery_card' if decision['decision'] in {'allow', 'allow_with_conditions', 'direct_answer'} else 'exception_card'
        self.store.add_card_event(task_id, run_id, card_type,
                                  self._card_payload(decision, task_id=task_id, run_id=run_id, audit_id=request_id))
        status = 'delivered' if decision['decision'] in {'allow', 'allow_with_conditions', 'direct_answer'} else 'needs_revision'
        task = self.store.set_task_state(task_id, status)
        self.store.set_run_state(run_id, status)
        self.store.add_event(request_id, 'delivery_checked', {'decision': decision}, task_id=task_id, run_id=run_id, step_id=step['id'])
        return {'task': task, 'run': self.store.get_run(run_id), 'step': step,
                'decision': decision, 'card_type': card_type}

    def task_timeline(self, task_id):
        return self.store.task_timeline(task_id)
