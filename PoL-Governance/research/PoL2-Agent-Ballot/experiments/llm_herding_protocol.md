# Pre-registered protocol — do LLM agents herd under open voting?

**Status: first run done (Claude Haiku 5.5, 40 proposals, 2026-10-18); results
and caveats in the README, experiment 3.** One model and one task family;
no general claim about LLM agents. `sealed_vs_open.py` only demonstrates the
mechanism with scripted conformists. Related measurements of LLM conformity:
Weng et al. 2025 (BenchForm), Cho et al. 2025, Zhang et al. 2024; see
[docs/related-work.md](../docs/related-work.md).

## Question
When several LLM agents each receive a private, noisy piece of evidence and
must vote on whether an event advances, does showing them the running tally
(open sequential voting) lower the accuracy of the collective decision
compared with sealed voting?

## Design
* N = 7 agents, same model, same system prompt (`agents.LLMAgent.system`).
* 40 proposals with a ground-truth answer (e.g. "does the attached test log
  show all tests passing?") built so that each agent's private evidence is
  correct with p ≈ 0.7 — evidence is corrupted independently per agent.
* Two conditions, same proposals, same evidence draws:
  **sealed** (`sealed=True`) and **open** (`sealed=False`, agents vote in a
  random order and see prior votes).
* Primary outcome: fraction of proposals where the majority decision is
  correct. Secondary: fraction of agents whose vote contradicts their own
  private evidence, split by whether a visible majority existed.
* Analysis: paired comparison per proposal; report the difference with a
  bootstrap CI. A null result is reported as a result.

## Honesty clauses
* Temperature, model version, prompt and seed are recorded in the output.
* The scripted simulation is not evidence about LLMs; only this run is.
* Results apply to this task family and model; no claim about humans.
* If the model refuses or returns unparseable output, the ballot is invalid
  (not re-prompted) and the rate is reported, together with whether the
  invalid ballots could have changed any decision. The raw reply of every
  invalid ballot is logged (added after the first run, whose 8 invalid
  replies were not kept).

## How to run
```powershell
python experiments/llm_herding.py --backend mock --proposals 40     # pipeline check
$env:LLM_BASE_URL = "http://localhost:11434/v1"; $env:LLM_MODEL = "qwen2.5:7b-instruct"
python experiments/llm_herding.py --backend openai --proposals 40
```
Ballot-level logs go to `experiments/results/llm_herding/`. The task is a
release review: each agent sees one private re-run of one check, which is
wrong with probability 1 − p. No API keys or endpoints belong in this
repository; they are read from environment variables.
