import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pol2_agent_ballot.agents import parse_choice

C = ["advance", "hold"]


def test_plain_json():
    assert parse_choice('{"choice": "hold", "rationale": "x"}', C) == ("hold", "x")


def test_escaped_apostrophe_and_newline():
    raw = '{"choice": "advance", "rationale": "I\\\'m sure.\nSecond line"}'
    assert parse_choice(raw, C)[0] == "advance"


def test_fenced_and_prose_and_case():
    raw = 'Here is my vote:\n```json\n{"choice": "Hold", "rationale": "y"}\n```\nThanks.'
    assert parse_choice(raw, C) == ("hold", "y")


def test_think_block_with_braces():
    raw = '<think>maybe {"choice":"hold"}</think>{"choice": "advance", "rationale": "z"}'
    assert parse_choice(raw, C) == ("advance", "z")


def test_braces_inside_rationale_fall_back_to_pattern():
    raw = '{"choice": "hold", "rationale": "the {config} file failed"}'
    assert parse_choice(raw, C)[0] == "hold"


def test_truncated_reply():
    assert parse_choice('{"choice": "advance", "rationale": "cut off', C)[0] == "advance"


def test_garbage_is_invalid():
    assert parse_choice("I abstain.", C)[0] == ""
    assert parse_choice('{"choice": "abstain"}', C)[0] == ""
