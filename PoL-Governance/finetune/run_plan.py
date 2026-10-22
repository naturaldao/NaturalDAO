"""为 GPU 阶段生成可执行脚本（命令规划器，纯 CPU / 纯标准库）。

GPU 实验暂停期间不执行任何命令；本工具只把恢复后要跑的命令按阶段拼成一个 bash 脚本，
供 WSL 中直接 bash 执行。阶段可组合，脚本带 set -euo pipefail 与阶段回显。

示例：
    python finetune/run_plan.py --stages base-test,lm-eval --out /tmp/resume.sh
    python finetune/run_plan.py --stages all
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional, Sequence

DEFAULT_REPO_WSL = "/mnt/c/Projects/DAism/NaturalDAO/PoL-Governance"
DEFAULT_HOME = "$HOME/src/polgov"
STAGES = ("env-check", "base-test", "lm-eval", "calibrate", "track-b-smoke", "track-b-full", "seeds")


def header(home: str, repo: str) -> List[str]:
    return [
        "#!/bin/bash",
        "set -euo pipefail",
        'export PATH="$HOME/.local/bin:/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH"',
        f"export POLGOV_HOME=\"{home}\"",
        'source "$POLGOV_HOME/.venv/bin/activate"',
        f"cd \"{repo}\"",
        'mkdir -p "$POLGOV_HOME/evals" "$POLGOV_HOME/runs"',
        "",
    ]


def stage_commands(stage: str, home: str, repo: str, model: str, adapter: str) -> List[str]:
    evals = f"{home}/evals"
    data = f"{home}/data"
    runs = f"{home}/runs"
    lines: List[str] = [f'echo "=== [$(date +%H:%M:%S)] {stage} ==="']

    if stage == "env-check":
        lines += [
            "nvidia-smi --query-gpu=name,temperature.gpu,memory.used --format=csv || true",
            'python - <<\'PY\'',
            "import torch, transformers, peft, importlib.util",
            "print('torch', torch.__version__, 'hip', getattr(torch.version, 'hip', None))",
            "print('transformers', transformers.__version__, 'peft', peft.__version__)",
            "print('lm_eval', importlib.util.find_spec('lm_eval') is not None)",
            "PY",
        ]
    elif stage == "base-test":
        lines += [
            f'python -u finetune/eval_decision.py --eval-view "{data}/general-test-view.jsonl" '
            f'--model "{model}" --batch-size 32 --json > "{evals}/base-test.json"',
        ]
    elif stage == "lm-eval":
        # datasets<4 时需要 --trust_remote_code 才能加载 cmmlu（见 EVAL-PROTOCOL §3.3）
        tasks = "ceval-valid,cmmlu,mmlu,agieval"
        lines += [
            f'lm_eval --model hf --model_args pretrained="{model}",dtype=float16 '
            f'--tasks {tasks} --limit 100 --batch_size 8 --trust_remote_code '
            f'--output_path "{evals}/lm-eval-base"',
            f'lm_eval --model hf --model_args pretrained="{model}",peft="{adapter}",dtype=float16 '
            f'--tasks {tasks} --limit 100 --batch_size 8 --trust_remote_code '
            f'--output_path "{evals}/lm-eval-track-a"',
        ]
    elif stage == "calibrate":
        lines += [
            f'python -u finetune/eval_decision.py --eval-view "{data}/general-validation-view.jsonl" '
            f'--model "{model}" --adapter "{adapter}" --batch-size 32 '
            f'--predictions "{evals}/val-preds.jsonl" > /dev/null',
            f'python finetune/calibrate.py fit --predictions "{evals}/val-preds.jsonl" '
            f'--out "{evals}/temperature.json"',
            f'python finetune/calibrate.py apply --predictions "{evals}/val-preds.jsonl" '
            f'--temperature "$(python -c \'import json,sys;print(json.load(open(sys.argv[1]))["temperature"])\' "{evals}/temperature.json")" '
            f'--half selection --json',
        ]
    elif stage == "track-b-smoke":
        lines += [
            f'python -u finetune/train_decision_scorer.py '
            f'--train-view "{data}/general-train-view.jsonl" '
            f'--eval-view "{data}/general-validation-view.jsonl" --model "{model}" '
            f'--output-dir "{runs}/track-b-smoke" --limit 4000 --max-steps 40 '
            f'--batch-size 8 --grad-accum 4 --seq-len 1024',
        ]
    elif stage == "track-b-full":
        lines += [
            f'python -u finetune/train_decision_scorer.py '
            f'--train-view "{data}/general-train-view.jsonl" '
            f'--eval-view "{data}/general-validation-view.jsonl" --model "{model}" '
            f'--output-dir "{runs}/track-b-e1" --epochs 1 --batch-size 8 --grad-accum 4 '
            f'--seq-len 1024 --eval-limit 500 --eval-every 400',
            f'python -u finetune/eval_decision_scorer.py '
            f'--eval-view "{data}/general-validation-view.jsonl" --model "{model}" '
            f'--adapter-dir "{runs}/track-b-e1/adapter" '
            f'--head-path "{runs}/track-b-e1/scorer_head.pt" '
            f'--batch-size 16 --json > "{evals}/track-b-val.json"',
        ]
    elif stage == "seeds":
        # 预注册种子：20261023 是主 run（已有 track-a-val.json），这里补 24/25 并自动评测 + 聚合
        for seed in (20261024, 20261025):
            lines += [
                f'python -u finetune/train_decision_sft.py '
                f'--train-view "{data}/general-train-view.jsonl" '
                f'--eval-view "{data}/general-validation-view.jsonl" --model "{model}" '
                f'--output-dir "{runs}/track-a-e1-seed{seed}" --epochs 1 --batch-size 8 '
                f'--grad-accum 4 --seq-len 1024 --eval-limit 500 --eval-every 400 --seed {seed}',
                f'python -u finetune/eval_decision.py --eval-view "{data}/general-validation-view.jsonl" '
                f'--model "{model}" --adapter "{runs}/track-a-e1-seed{seed}/adapter" '
                f'--batch-size 32 --json > "{evals}/track-a-val-seed{seed}.json"',
            ]
        # 多种子汇总（seed 20261023 用主 run 的 validation 评测）
        lines += [
            f'python finetune/collect_results.py '
            f'--seed-eval "track-a={evals}/track-a-val.json" '
            f'--seed-eval "track-a={evals}/track-a-val-seed20261024.json" '
            f'--seed-eval "track-a={evals}/track-a-val-seed20261025.json" '
            f'--out "{evals}/multiseed-track-a.md"',
        ]
    else:
        raise ValueError(f"unknown stage: {stage}")
    lines.append("")
    return lines


def build_script(stages: Sequence[str], home: str, repo: str, model: str, adapter: str) -> str:
    lines = header(home, repo)
    for stage in stages:
        lines += stage_commands(stage, home, repo, model, adapter)
    lines += ['echo "ALL_STAGES_DONE"', ""]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stages", default="env-check",
                        help="逗号分隔的阶段：" + ",".join(STAGES) + "（默认 env-check）")
    parser.add_argument("--project-home", default=DEFAULT_HOME)
    parser.add_argument("--repo-wsl", default=DEFAULT_REPO_WSL)
    parser.add_argument("--model", default=DEFAULT_HOME + "/models/Qwen3-1.7B")
    parser.add_argument("--adapter", default=DEFAULT_HOME + "/runs/track-a-e1-rocm/adapter")
    parser.add_argument("--out", help="输出脚本路径；省略则打印到 stdout")
    args = parser.parse_args(argv)
    stages = [stage.strip() for stage in args.stages.split(",") if stage.strip()]
    if not stages:
        print("no stages selected", file=sys.stderr)
        return 2
    if "all" in stages:
        stages = list(STAGES)
    unknown = [stage for stage in stages if stage not in STAGES]
    if unknown:
        print(f"unknown stages: {unknown}", file=sys.stderr)
        return 2
    script = build_script(stages, args.project_home, args.repo_wsl, args.model, args.adapter)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(script)
        print(f"written: {args.out}")
    else:
        print(script)
    return 0


if __name__ == "__main__":
    sys.exit(main())
