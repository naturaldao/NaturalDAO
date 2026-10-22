from hooks.pre_tool_hook import consume_proxy_permit, evaluate_and_consume, guard_tool_call


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.status_code = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f'http {self.status}')

    def json(self):
        return self.payload


class FakeHTTP:
    def __init__(self, decision=None, consume=None, fail=False):
        self.decision = decision or {'decision': 'allow', 'reason': 'ok',
                                     'conditions': [], 'release': {'token': 'token-1'}}
        self.consume = consume or {'id': 'permit-1', 'status': 'consumed'}
        self.fail = fail
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append((url, json, headers))
        if self.fail:
            raise OSError('network down')
        return Response(self.consume if url.endswith('/v1/permits/consume') else self.decision)


def event(**overrides):
    payload = {'tool_name': 'shell', 'arguments': {'command': 'ls'}, 'tool_call_id': 'call-1',
               'client_id': 'agent', 'account_scope': 'local', 'session_id': 's1'}
    payload.update(overrides)
    return payload


def test_hook_allows_only_after_permit_consumption(monkeypatch):
    monkeypatch.setenv('POL2_SERVICE_URL', 'http://pol2.local')
    http = FakeHTTP()
    result = evaluate_and_consume(event(), http=http)
    assert result['decision'] == 'allow'
    assert result['permit_id'] == 'permit-1'
    assert [call[0].split('/v1/')[-1] for call in http.calls] == ['govern/operation', 'permits/consume']


def test_hook_blocks_conditional_allow_without_evidence(monkeypatch):
    monkeypatch.setenv('POL2_SERVICE_URL', 'http://pol2.local')
    http = FakeHTTP(decision={'decision': 'allow_with_conditions', 'reason': 'needs condition',
                              'conditions': ['only test environment'], 'release': {'token': 'token-1'}})
    result = evaluate_and_consume(event(), http=http)
    assert result['decision'] == 'block'
    assert result['conditions'] == ['only test environment']
    assert len(http.calls) == 1


def test_hook_blocks_on_denial_and_failure(monkeypatch):
    monkeypatch.setenv('POL2_SERVICE_URL', 'http://pol2.local')
    denied = evaluate_and_consume(event(), http=FakeHTTP(decision={'decision': 'revise', 'reason': 'not allowed'}))
    failed = evaluate_and_consume(event(), http=FakeHTTP(fail=True))
    assert denied['decision'] == 'block'
    assert failed['decision'] == 'block'


def test_proxy_permit_is_consumed_without_second_model_decision(monkeypatch):
    monkeypatch.setenv('POL2_SERVICE_URL', 'http://pol2.local')
    tool_call = {
        'id': 'call-delete', 'type': 'function',
        'function': {'name': 'shell', 'arguments': '{"command":"rm /workspace/a.txt"}'},
        'pol2': {
            'decision': 'allow', 'request_id': 'proxy-1:tool:0:abcdef123456',
            'tool_call_id': 'call-delete', 'conditions': [],
            'permit': {'token': 'proxy-token'},
        },
    }
    http = FakeHTTP(consume={'id': 'permit-proxy', 'status': 'consumed'})
    result = consume_proxy_permit(tool_call, http=http)
    assert result['decision'] == 'allow'
    assert result['permit_id'] == 'permit-proxy'
    assert len(http.calls) == 1
    assert http.calls[0][0].endswith('/v1/permits/consume')


def test_host_hook_reuses_proxy_operation_by_session_and_call_id(monkeypatch):
    monkeypatch.setenv('POL2_SERVICE_URL', 'http://pol2.local')
    monkeypatch.setenv('POL2_HOOK_CLIENT', 'agent')
    monkeypatch.setenv('POL2_HOOK_ACCOUNT', 'local')
    monkeypatch.setenv('POL2_HOOK_SESSION', 'local-session')

    class ExistingHTTP:
        def __init__(self):
            self.calls = []

        def get(self, url, headers=None, timeout=None):
            self.calls.append(('get', url))
            return Response({'input_text': 'canonical-op',
                             'decision': {'decision': 'allow', 'reason': 'ok', 'conditions': [],
                                          'release': {'token': 'existing-token'}}})

        def post(self, url, json=None, headers=None, timeout=None):
            self.calls.append(('post', url))
            return Response({'id': 'permit-existing', 'status': 'consumed'})

    http = ExistingHTTP()
    result = guard_tool_call({'id': 'call-1', 'type': 'function',
                              'function': {'name': 'terminal', 'arguments': '{"command":"rm /tmp/x"}'}},
                             http=http)
    assert result['decision'] == 'allow'
    assert result['permit_id'] == 'permit-existing'
    assert [kind for kind, _ in http.calls] == ['get', 'post']
