import json
import hashlib
from typing import Any


def canonical_tool_operation(tool_call: dict[str, Any]) -> str:
    """Canonical bytes used by both the proxy and pre-tool hook."""
    value = dict(tool_call)
    value.pop('pol2', None)
    value.pop('index', None)
    function = value.get('function')
    if isinstance(function, dict):
        function = dict(function)
        arguments = function.get('arguments')
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                pass
        if not isinstance(arguments, str):
            function['arguments'] = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
        value['function'] = function
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def tool_call_id(tool_call: dict[str, Any], fallback_index: int = 0) -> str:
    return str(tool_call.get('id') or tool_call.get('tool_call_id') or f'index-{fallback_index}')


def tool_request_id(session_id: str, call_id: str) -> str:
    """Stable id shared by proxy and execution hook for one tool call."""
    digest = hashlib.sha256(f'{session_id}|{call_id}'.encode()).hexdigest()[:32]
    return 'tool-' + digest
