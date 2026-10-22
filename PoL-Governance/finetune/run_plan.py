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
        tasks = "ceval-valid,mmlu,agieval"
        lines += [
            f'lm_eval --model hf --model_args pretrained="{model}",dtype=float16 '
            f'--tasks {tasks} --limit 100 --batch_size 8 --output_path "{evals}/lm-eval-base.json"',
            f'lm_eval --model hf --model_args pretrained="{model}",peft="{adapter}",dtype=float16 '
            f'--tasks {tasks} --limit 100 --batch_size 8 --output_path "{evals}/lm-eval-track-a.json"',
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
        ]
    elif stage == "seeds":
        for seed in (20261024, 20261025):
            lines += [
                f'python -u finetune/train_decision_sft.py '
                f'--train-view "{data}/general-train-view.jsonl" '
                f'--eval-view "{data}/general-validation-view.jsonl" --model "{model}" '
                f'--output-dir "{runs}/track-a-e1-seed{seed}" --epochs 1 --batch-size 8 '
                f'--grad-accum 4 --seq-len 1024 --eval-limit 500 --eval-every 400 --seed {seed}',
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
