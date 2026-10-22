#!/usr/bin/env python3
"""Generic host hook adapter: consumes proxy permits or falls back to POL2."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hooks.pre_tool_hook import evaluate_and_consume, guard_tool_call


def normalize(payload):
    if isinstance(payload.get('tool_call'), dict):
        return payload['tool_call']
    tool_name = payload.get('tool_name') or payload.get('name')
    arguments = payload.get('tool_input', payload.get('arguments', {}))
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
    call_id = (payload.get('extra') or {}).get('tool_call_id') or payload.get('tool_call_id') or 'host-tool-call'
    result = {
        'id': call_id, 'type': 'function',
        'function': {'name': tool_name, 'arguments': arguments},
    }
    if payload.get('pol2'):
        result['pol2'] = payload['pol2']
    return result


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({'decision': 'block', 'reason': 'hook input is not valid JSON'}))
        return
    log_path = os.getenv('POL2_HOOK_LOG')
    if log_path:
        with open(log_path, 'a', encoding='utf-8') as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + '\n')
    tool_call = normalize(payload)
    result = guard_tool_call(tool_call, conditions_satisfied=bool(payload.get('conditions_satisfied', False)),
                             condition_evidence=payload.get('condition_evidence', {}))
    if log_path:
        with open(log_path, 'a', encoding='utf-8') as stream:
            stream.write(json.dumps({'decision_result': result}, ensure_ascii=False) + '\n')
    if result.get('decision') == 'allow':
        print(json.dumps({'action': 'continue', 'pol2': result}, ensure_ascii=False))
    else:
        print(json.dumps({'decision': 'block', 'reason': result.get('reason', 'POL2 blocked operation'),
                          'pol2': result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
