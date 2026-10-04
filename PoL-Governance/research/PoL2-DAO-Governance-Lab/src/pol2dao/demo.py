"""A scripted PoL2 governance session on the DAO experiment's question.

Five participants decide how an AI assistant should handle a sensitive
request, using the four options from Sharma et al. (2026). One message is
hostile, one is angry criticism (which must pass), a question is raised and
explained, and everything lands on a verifiable decision chain.
"""

from __future__ import annotations

from pathlib import Path

from .ledger import DecisionChain
from .protocol import GovernanceConfig, GovernanceSession, Proposal
from .simulate import OPTIONS


def _fixed_clock():
    n = [0]

    def tick() -> str:
        n[0] += 1
        return f"2026-09-29T12:{n[0] // 60:02d}:{n[0] % 60:02d}+00:00"

    return tick


def run_demo(path: str | Path = "results/demo_decision_chain.jsonl"):
    proposal = Proposal(
        id="P-001",
        title="AI 助手应如何回应涉及个人价值观的敏感请求？",
        options=OPTIONS,
        rationale="Sharma et al. (2026) 实验中的同一问题，此处按 PoL2 流程重新治理。",
    )
    people = ["ada", "bo", "chen", "dina", "eli"]
    s = GovernanceSession(proposal, people, GovernanceConfig.pol2(),
                          chain=DecisionChain(clock=_fixed_clock()))

    s.say("ada", "谢谢大家，我们一起看看每个选项的代价。")
    s.say("bo", "Option 2 is fine. Anyone who backs option 3 is an idiot.")   # flagged, kept on record
    s.say("chen", "我很生气，我反对选项2，它会忽略少数用户的需求。")             # criticism: passes
    s.pass_turn("dina")                                                       # passing is allowed
    s.say("eli", "What do you think about option 4's tags?")
    s.say("ada", "I understand the concern about privacy.")
    s.say("bo", "Sorry for the insult earlier. I still prefer option 2.")     # repair

    s.open_vote()
    for voter, tokens in {"ada": (0, 25, 49, 25), "bo": (9, 81, 9, 1), "chen": (0, 0, 100, 0),
                          "dina": (16, 16, 36, 32), "eli": (0, 16, 36, 48)}.items():
        s.cast(voter, tokens)
    s.close_vote()

    q = s.question("bo", "为什么选项3在人数较少的情况下胜出？")
    s.explain(q, "二次方投票下，t 个代币只换来 √t 票；陈把全部 100 代币投给选项3，只得到 10 票。"
                 "选项3胜出是因为五人中有四人都给了它相当的支持，而不是某一人的代币更多。")
    decision = s.finalize()
    path = s.chain.to_jsonl(path)
    return decision, s.chain, path


if __name__ == "__main__":
    d, chain, p = run_demo()
    print(d.to_dict())
    print(p, chain.verify())
