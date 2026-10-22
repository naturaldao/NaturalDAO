import json
import time
import uuid
import requests
from .tool_contract import canonical_tool_operation, tool_call_id as get_tool_call_id, tool_request_id


CONTINUATION_MARKERS = (
    "刚才", "上一条", "上一个", "继续", "接着", "基于前面", "按刚才", "修改上面",
    "上述", "这个文件", "continue", "previous", "above",
)


def build_governance_context(*, client_id, messages, request_text, model, task_id=None):
    previous_users = [item.get('content', '') for item in messages
                      if item.get('role') == 'user'][:-1]
    continuation = any(marker in request_text.lower() for marker in CONTINUATION_MARKERS)
    previous_assistant = None
    if continuation:
        previous_assistant = next((item.get('content', '') for item in reversed(messages)
                                   if item.get('role') == 'assistant'), None)
        if previous_assistant:
            previous_assistant = '\n'.join(
                line for line in previous_assistant.splitlines()
                if not line.strip().startswith('【POL2') and not line.strip().startswith('审计：')
            )[-4000:]
    return {
        'client': client_id,
        'model': model,
        'task_id': task_id,
        'context_mode': 'continuation' if continuation else 'fresh',
        'previous_user_messages': previous_users[-3:] if continuation else [],
        'previous_assistant': previous_assistant,
    }


def build_operation_context(*, messages, request_text, tool_call, task_id, input_decision):
    turns = []
    for item in messages[-12:]:
        if item.get('role') not in {'user', 'assistant'}:
            continue
        content = item.get('content') or ''
        if item.get('role') == 'assistant':
            content = '\n'.join(line for line in content.splitlines()
                                if not line.strip().startswith('【POL2') and not line.strip().startswith('审计：'))
        turns.append({'role': item.get('role'), 'content': content[-4000:]})
    return {
        'task_id': task_id,
        'request': request_text,
        'conversation': turns,
        'tool_call': {key: value for key, value in tool_call.items() if key != 'pol2'},
        'input_decision': input_decision.get('decision'),
    }


class UpstreamChatClient:
    def __init__(self, base_url, api_key, timeout=120, default_model=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.default_model = default_model

    def forward(self, payload):
        if self.default_model:
            payload = dict(payload)
            payload['model'] = self.default_model
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        last_error = None
        for attempt in range(4):
            try:
                response = requests.post(
                    self.base_url + '/chat/completions', data=body, timeout=self.timeout,
                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.api_key})
                if response.status_code == 429:
                    wait = response.headers.get('Retry-After')
                    time.sleep(min(int(wait), 30) if wait and wait.isdigit() else 10)
                    last_error = RuntimeError('upstream rate limited')
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(min(2 ** attempt, 10))
        raise last_error


def governed_response(model, text, decision, finish_reason='content_filter'):
    return {
        'id': 'pol2-' + uuid.uuid4().hex, 'object': 'chat.completion', 'model': model,
        'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': text},
                     'finish_reason': finish_reason}],
        'pol2': {'decision': decision['decision'], 'reason': decision.get('reason'),
                 'rule_ids': decision.get('rule_ids', []), 'citations': decision.get('citations', [])},
    }


def gate_and_forward(*, payload, identity, service, upstream, request_id=None):
    messages = payload.get('messages') or []
    user_messages = [item.get('content', '') for item in messages if item.get('role') == 'user']
    if not user_messages:
        raise ValueError('at least one user message is required')
    request_text = user_messages[-1]
    context = build_governance_context(
        client_id=identity['client_id'], messages=messages, request_text=request_text,
        model=payload.get('model'), task_id=identity.get('task_id'))
    request_id = request_id or 'chat-' + uuid.uuid4().hex
    task_id = identity.get('task_id')
    run_id = identity.get('run_id')
    step_id = identity.get('step_id')
    if task_id:
        if not run_id:
            raise ValueError('x-pol2-run is required when x-pol2-task is supplied')
        step_result = service.check_step(
            task_id=task_id, run_id=run_id, request=request_text, context=context,
            client_id=identity['client_id'], account_scope=identity['account_scope'],
            session_id=identity['session_id'], kind='model', request_id=request_id)
        decision = step_result['decision']
        step_id = step_result['step']['id']
    else:
        decision = service.govern(
            request_id=request_id, client_id=identity['client_id'], account_scope=identity['account_scope'],
            session_id=identity['session_id'], stage='requirement', request=request_text,
            context=json.dumps(context, ensure_ascii=False), project_id=identity.get('project_id'))
    if decision['decision'] == 'direct_answer':
        response = governed_response(payload.get('model', 'unknown'), decision['answer'], decision, 'stop')
        return response
    if decision['decision'] not in {'allow', 'allow_with_conditions'}:
        text = decision.get('clarification') or decision.get('reason') or '请求未通过POL2治理检查。'
        response = governed_response(payload.get('model', 'unknown'), text, decision)
        return response

    upstream_payload = dict(payload)
    upstream_payload['stream'] = False
    upstream_payload.pop('stream_options', None)
    response = upstream.forward(upstream_payload)
    choices = response.get('choices')
    if not isinstance(choices, list) or not choices:
        raise ValueError('upstream returned an unsupported response shape')
    reviewed_outputs = []
    tool_reviews = []
    for index, choice in enumerate(choices):
        message = choice.get('message') or {}
        content = message.get('content')
        tool_calls = message.get('tool_calls') or []
        if content:
            reviewed_outputs.append(content)
        for tool_index, tool_call in enumerate(tool_calls):
            operation = canonical_tool_operation(tool_call)
            call_id = get_tool_call_id(tool_call, tool_index)
            operation_request_id = tool_request_id(identity['session_id'], call_id)
            operation_context = build_operation_context(
                messages=messages, request_text=request_text, tool_call=tool_call,
                task_id=task_id, input_decision=decision)
            operation_decision = service.check_operation(
                request_id=operation_request_id, client_id=identity['client_id'],
                account_scope=identity['account_scope'], session_id=identity['session_id'],
                operation=operation,
                context=json.dumps(operation_context, ensure_ascii=False),
                project_id=identity.get('project_id'), task_id=task_id, run_id=run_id, step_id=step_id)
            tool_reviews.append({'decision': operation_decision, 'tool_call_id': call_id,
                                 'tool_name': (tool_call.get('function') or {}).get('name') or tool_call.get('name'),
                                 'request_id': operation_request_id})
            if operation_decision['decision'] not in {'allow', 'allow_with_conditions'}:
                text = operation_decision.get('reason') or '工具调用未通过POL2治理检查。'
                response = governed_response(payload.get('model', 'unknown'), text, operation_decision)
                return response
            if operation_decision.get('release'):
                tool_call['pol2'] = {
                    'decision': operation_decision['decision'],
                    'reason': operation_decision.get('reason'),
                    'conditions': operation_decision.get('conditions', []),
                    'request_id': operation_request_id,
                    'tool_call_id': call_id,
                    'permit': operation_decision['release'],
                }
    if not reviewed_outputs and not tool_reviews:
        raise ValueError('upstream response contains no reviewable content or tool call')
    output_decisions = []
    for index, content in enumerate(reviewed_outputs):
        output_decision = service.check_output(
            request_id=f'{request_id}:output:{index}', client_id=identity['client_id'],
            account_scope=identity['account_scope'], session_id=identity['session_id'],
            output=content, request_context=json.dumps({'request': request_text, 'input_decision': decision['decision']},
                                                        ensure_ascii=False), project_id=identity.get('project_id'),
            task_id=task_id, run_id=run_id, step_id=step_id)
        output_decisions.append(output_decision)
        if output_decision['decision'] not in {'allow', 'allow_with_conditions', 'direct_answer'}:
            text = output_decision.get('reason') or '输出未通过POL2治理检查。'
            response = governed_response(payload.get('model', 'unknown'), text, output_decision)
            return response
    response.setdefault('pol2', {})['output_decisions'] = [
        {'decision': item['decision'], 'release': item.get('release')} for item in output_decisions]
    response['pol2']['release'] = output_decisions[0].get('release') if output_decisions else None
    response['pol2']['tool_decisions'] = [
        {'tool_call_id': item['tool_call_id'], 'tool_name': item['tool_name'],
         'request_id': item['request_id'], 'decision': item['decision']['decision'],
         'conditions': item['decision'].get('conditions', []),
         'release': item['decision'].get('release')} for item in tool_reviews]
    response.setdefault('pol2', {})['input_decision'] = decision
    return response


def to_sse_chunks(response):
    for choice in response.get('choices', []):
        message = choice.get('message') or {}
        delta = {'role': 'assistant'}
        if message.get('content'):
            delta['content'] = message['content']
        if message.get('tool_calls'):
            delta['tool_calls'] = message['tool_calls']
        chunk = {
            'id': response.get('id', 'pol2-stream'), 'object': 'chat.completion.chunk',
            'created': response.get('created'), 'model': response.get('model'),
            'choices': [{'index': choice.get('index', 0), 'delta': delta, 'finish_reason': None}],
        }
        yield 'data: ' + json.dumps(chunk, ensure_ascii=False) + '\n\n'
        final = {
            'id': response.get('id', 'pol2-stream'), 'object': 'chat.completion.chunk',
            'created': response.get('created'), 'model': response.get('model'),
            'choices': [{'index': choice.get('index', 0), 'delta': {}, 'finish_reason': choice.get('finish_reason', 'stop')}],
            'pol2': response.get('pol2', {}),
        }
        yield 'data: ' + json.dumps(final, ensure_ascii=False) + '\n\n'
    yield 'data: [DONE]\n\n'
