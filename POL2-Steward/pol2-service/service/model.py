import json
import time
import requests


class OpenAICompatibleClient:
    def __init__(self, base_url, model, api_key, timeout=60,
                 fallback_base_url=None, fallback_model=None, fallback_api_key=None, fallback_timeout=120):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.fallback_base_url = fallback_base_url.rstrip('/') if fallback_base_url else None
        self.fallback_model = fallback_model
        self.fallback_api_key = fallback_api_key or ''
        self.fallback_timeout = fallback_timeout

    @staticmethod
    def _extract_json(content):
        content = content.strip()
        decoder = json.JSONDecoder()
        for index in range(len(content) - 1, -1, -1):
            if content[index] != '{':
                continue
            try:
                parsed, _ = decoder.raw_decode(content[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and 'decision' in parsed:
                return parsed
        raise ValueError('model returned no JSON object with decision')

    def _request(self, base_url, model, api_key, timeout, messages):
        body = json.dumps({
            'model': model, 'temperature': 0, 'max_tokens': 4096,
            'response_format': {'type': 'json_object'}, 'messages': messages,
        }).encode('utf-8')
        response = requests.post(
            base_url + '/chat/completions', data=body, timeout=timeout,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key},
        )
        if response.status_code == 429:
            raise RuntimeError('model rate limited')
        response.raise_for_status()
        data = response.json()
        message = data['choices'][0]['message']
        content = message.get('content') or message.get('reasoning_content') or message.get('reasoning')
        if not content:
            raise ValueError('model returned no content')
        return self._extract_json(content)

    def judge(self, request, evidence, context, stage):
        system = (
            '你是POL2治理判断器。只依据提供的规则和来源判断，不发明条款。'
            '输出严格JSON：decision（allow/allow_with_conditions/clarify/revise/reject），'
            'reason，rule_ids（数组），conditions（数组），clarification，revision_items（数组）。'
            '决定顺序必须与理由一致：只有请求必然要求严重伤害且没有合规替代方案时才 reject；'
            '如果保留合规目标但需要改变内容、范围、对象、脱敏或取得授权，则用 revise；'
            '如果缺少会改变判断的事实、用途、授权或上下文，则用 clarify，并明确缺什么；'
            'allow_with_conditions 只用于放行后可在执行中落实的条件，不能用来掩盖发布前必须完成的修改；'
            '所有前置条件已满足且没有未解决风险时才用 allow。不能确定时不得放行。'
        )
        payload = {
            'stage': stage,
            'request': request,
            'context': context,
            'rules': [
                {'rule_id': rule['rule_id'], 'title': rule['title'], 'kind': rule['kind'],
                 'applicability': rule.get('applicability', 'general'),
                 'trigger_conditions': rule.get('trigger_conditions', []),
                 'check_questions': rule['check_questions'], 'conditions': rule['conditions_and_exceptions'],
                 'guidance': rule['decision_guidance'], 'source_texts': rule.get('source_texts', [])}
                for rule in evidence['rules']
            ],
        }
        messages = [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
        ]
        endpoints = [(self.base_url, self.model, self.api_key, self.timeout, 4)]
        if self.fallback_base_url and self.fallback_model:
            endpoints.append((self.fallback_base_url, self.fallback_model, self.fallback_api_key,
                              self.fallback_timeout, 2))
        last_error = None
        for base_url, model, api_key, timeout, attempts in endpoints:
            for attempt in range(attempts):
                try:
                    return self._request(base_url, model, api_key, timeout, messages)
                except Exception as exc:
                    last_error = exc
                    if attempt < attempts - 1:
                        time.sleep(min(2 ** attempt, 10))
        raise last_error or RuntimeError('governance model unavailable')
