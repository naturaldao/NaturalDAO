#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Laya 本地微调模型测试脚本

用途：
1. 加载训练后的 Laya 模型
2. 使用 agent.predict() 测试 speech_type / eap_action
3. 使用当前 Laya 版本要求的 questions dict，并解析 predict() 返回结构：
       result["answers"]["speech_type"]["choice"]
       result["answers"]["eap_action"]["choice"]
4. 输出每个测试样本的预测结果和概率
5. 统计：
       - speech_type 准确率
       - eap_action 准确率
       - 两项同时正确率

默认模型：
    ./my_custom_laya_model

运行：
    python test_custom_laya.py

指定模型：
    python test_custom_laya.py --model ./my_custom_laya_model --device cuda

JSON 输出：
    python test_custom_laya.py --json
"""

import argparse
import json
import sys
from typing import Any, Dict, List

import torch
import laya


SPEECH_OPTIONS = [
    "love_speech",
    "hate_speech",
    "non_love_non_hate",
]

ACTION_OPTIONS = [
    "amplify_love",
    "block_and_repair",
    "clarify_and_continue",
]

# 当前 Laya 版本要求 questions 为：
# {
#     "question_id": {
#         "type": "choice",
#         "instructions": "...",
#         "criteria": {
#             "label": "label 的语义描述",
#             ...
#         }
#     }
# }
#
# choice 问题使用 criteria，而不是 options。
#
# 重要：
# 这里必须与 train_custom_gpt.py 中训练时的 QUESTIONS 完全一致。
# Laya 会把 instructions / criteria 渲染进 choice 的输入，因此不能
# 在测试时自由改写这些描述，否则测试实际上改变了模型看到的题目。
QUESTIONS = {
    "speech_type": {
        "type": "choice",
        "instructions": "这句话属于哪一种言语类型？",
        "criteria": {
            "love_speech": "真诚、尊重、共情、肯定、宽恕、平等连接",
            "hate_speech": "羞辱、去人化、敌意、排斥、控制、鼓吹暴力",
            "non_love_non_hate": "误解、打断、缺席等，既不是爱也不是仇恨",
        },
    },
    "eap_action": {
        "type": "choice",
        "instructions": "针对这句话，应该采取哪一种 EAP 行动？",
        "criteria": {
            "amplify_love": "确认并强化爱的表达，增强人与人之间的连接",
            "block_and_repair": "阻止仇恨表达，保护目标，并引导修复",
            "clarify_and_continue": "澄清误解并继续对话",
        },
    },
}


TEST_CASES = [
    {
        "id": "HATE-01",
        "state": "你真是个废物，什么都做不好，难怪没人喜欢你。",
        "speech_type": "hate_speech",
        "eap_action": "block_and_repair",
    },
    {
        "id": "HATE-02",
        "state": "闭嘴吧，你这种人根本不配和别人说话。",
        "speech_type": "hate_speech",
        "eap_action": "block_and_repair",
    },
    {
        "id": "HATE-03",
        "state": "你就是个垃圾，所有人都应该离你远一点。",
        "speech_type": "hate_speech",
        "eap_action": "block_and_repair",
    },
    {
        "id": "LOVE-01",
        "state": "我很珍惜你，也愿意认真听你说出自己的感受。",
        "speech_type": "love_speech",
        "eap_action": "amplify_love",
    },
    {
        "id": "LOVE-02",
        "state": "谢谢你一直陪着我，我希望我们可以坦诚地理解彼此。",
        "speech_type": "love_speech",
        "eap_action": "amplify_love",
    },
    {
        "id": "LOVE-03",
        "state": "即使我们有不同的想法，我也尊重你，并愿意和你继续沟通。",
        "speech_type": "love_speech",
        "eap_action": "amplify_love",
    },
    {
        "id": "NEUTRAL-01",
        "state": "我没有完全理解你的意思，可以再解释一下吗？",
        "speech_type": "non_love_non_hate",
        "eap_action": "clarify_and_continue",
    },
    {
        "id": "NEUTRAL-02",
        "state": "刚才网络断了一下，我没有听清你最后说的内容。",
        "speech_type": "non_love_non_hate",
        "eap_action": "clarify_and_continue",
    },
    {
        "id": "NEUTRAL-03",
        "state": "我需要一点时间整理一下，然后我们再继续讨论。",
        "speech_type": "non_love_non_hate",
        "eap_action": "clarify_and_continue",
    },
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="测试本地微调后的 Laya 决策模型"
    )
    parser.add_argument(
        "--model",
        default="./my_custom_laya_model",
        help="Laya 模型目录，默认 ./my_custom_laya_model",
    )
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="运行设备，例如 cuda / cpu",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出最终测试结果",
    )
    return parser.parse_args()


def get_answer(result: Dict[str, Any], key: str) -> Dict[str, Any]:
    """
    Laya predict() 实际返回结构：

    {
        "model": "laya-rl-agent",
        "answers": {
            "speech_type": {
                "type": "choice",
                "choice": "...",
                "probabilities": {...},
                ...
            },
            "eap_action": {
                "type": "choice",
                "choice": "...",
                "probabilities": {...},
                ...
            }
        },
        "usage": {...}
    }
    """
    answers = result.get("answers", {})
    answer = answers.get(key, {})

    if not isinstance(answer, dict):
        return {}

    return answer


def print_probabilities(
    title: str,
    probabilities: Dict[str, Any],
    options: List[str],
):
    print(f"{title}:")
    for option in options:
        value = probabilities.get(option)
        if value is None:
            print(f"  {option}: -")
        else:
            try:
                print(f"  {option}: {float(value):.4f}")
            except (TypeError, ValueError):
                print(f"  {option}: {value}")


def main():
    args = parse_args()

    print("=" * 72)
    print("Laya 本地微调模型测试")
    print("=" * 72)
    print(f"模型目录: {args.model}")
    print(f"测试设备: {args.device}")
    print(f"CUDA 可用: {torch.cuda.is_available()}")

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        print("\n错误：指定了 CUDA，但当前 PyTorch 检测不到 CUDA。")
        sys.exit(1)

    print("\n正在加载模型...")
    agent = laya.Agent(args.model, device=args.device)
    print(
        f"模型加载完成: device={getattr(agent, 'device', args.device)} "
        f"dtype={getattr(agent, 'dtype', 'unknown')}"
    )

    print("\n" + "=" * 72)
    print("开始测试")
    print("=" * 72)

    results = []

    speech_correct = 0
    action_correct = 0
    both_correct = 0

    for case in TEST_CASES:
        case_id = case["id"]
        state = case["state"]
        expected_speech = case["speech_type"]
        expected_action = case["eap_action"]

        print("\n" + "-" * 72)
        print(f"[{case_id}]")
        print(f"state: {state}")
        print(f"expected speech_type: {expected_speech}")
        print(f"expected eap_action : {expected_action}")

        try:
            raw = agent.predict(state, QUESTIONS)
        except Exception as exc:
            print("\nERROR: agent.predict() 执行失败")
            print(f"{type(exc).__name__}: {exc}")
            results.append(
                {
                    "id": case_id,
                    "state": state,
                    "expected": {
                        "speech_type": expected_speech,
                        "eap_action": expected_action,
                    },
                    "predicted": {
                        "speech_type": None,
                        "eap_action": None,
                    },
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        if not isinstance(raw, dict):
            print("\nERROR: agent.predict() 返回值不是 dict")
            print(f"实际类型: {type(raw)}")
            print(f"返回值: {raw}")

            results.append(
                {
                    "id": case_id,
                    "state": state,
                    "expected": {
                        "speech_type": expected_speech,
                        "eap_action": expected_action,
                    },
                    "predicted": {
                        "speech_type": None,
                        "eap_action": None,
                    },
                    "raw_type": str(type(raw)),
                    "raw": repr(raw),
                }
            )
            continue

        speech_answer = get_answer(raw, "speech_type")
        action_answer = get_answer(raw, "eap_action")

        speech_pred = speech_answer.get("choice")
        action_pred = action_answer.get("choice")

        speech_probs = speech_answer.get("probabilities", {})
        action_probs = action_answer.get("probabilities", {})

        speech_ok = speech_pred == expected_speech
        action_ok = action_pred == expected_action
        both_ok = speech_ok and action_ok

        if speech_ok:
            speech_correct += 1

        if action_ok:
            action_correct += 1

        if both_ok:
            both_correct += 1

        print(
            f"\nspeech_type: {speech_pred} "
            f"{'✓' if speech_ok else '✗'}"
        )
        print(
            f"eap_action : {action_pred} "
            f"{'✓' if action_ok else '✗'}"
        )

        if isinstance(speech_probs, dict):
            print_probabilities(
                "\nspeech_type probabilities",
                speech_probs,
                SPEECH_OPTIONS,
            )

        if isinstance(action_probs, dict):
            print_probabilities(
                "\neap_action probabilities",
                action_probs,
                ACTION_OPTIONS,
            )

        speech_confidence = speech_answer.get("confidence")
        speech_answer_confidence = speech_answer.get("answer_confidence")
        action_confidence = action_answer.get("confidence")
        action_answer_confidence = action_answer.get("answer_confidence")

        print("\nconfidence:")
        print(
            f"  speech_type confidence: "
            f"{speech_confidence if speech_confidence is not None else '-'}"
        )
        print(
            f"  speech_type answer_confidence: "
            f"{speech_answer_confidence if speech_answer_confidence is not None else '-'}"
        )
        print(
            f"  eap_action confidence: "
            f"{action_confidence if action_confidence is not None else '-'}"
        )
        print(
            f"  eap_action answer_confidence: "
            f"{action_answer_confidence if action_answer_confidence is not None else '-'}"
        )

        results.append(
            {
                "id": case_id,
                "state": state,
                "expected": {
                    "speech_type": expected_speech,
                    "eap_action": expected_action,
                },
                "predicted": {
                    "speech_type": speech_pred,
                    "eap_action": action_pred,
                },
                "correct": {
                    "speech_type": speech_ok,
                    "eap_action": action_ok,
                    "both": both_ok,
                },
                "probabilities": {
                    "speech_type": speech_probs,
                    "eap_action": action_probs,
                },
                "confidence": {
                    "speech_type": speech_confidence,
                    "speech_type_answer": speech_answer_confidence,
                    "eap_action": action_confidence,
                    "eap_action_answer": action_answer_confidence,
                },
                "usage": raw.get("usage"),
            }
        )

    total = len(TEST_CASES)

    print("\n" + "=" * 72)
    print("测试结果汇总")
    print("=" * 72)

    print(
        f"speech_type 准确率: "
        f"{speech_correct}/{total} = "
        f"{speech_correct / total * 100:.2f}%"
    )

    print(
        f"eap_action  准确率: "
        f"{action_correct}/{total} = "
        f"{action_correct / total * 100:.2f}%"
    )

    print(
        f"两项同时正确率:     "
        f"{both_correct}/{total} = "
        f"{both_correct / total * 100:.2f}%"
    )

    print("\n逐条结果:")
    print("-" * 72)

    for item in results:
        predicted = item.get("predicted", {})
        expected = item.get("expected", {})
        correct = item.get("correct", {})

        speech_mark = "✓" if correct.get("speech_type") else "✗"
        action_mark = "✓" if correct.get("eap_action") else "✗"
        both_mark = "✓" if correct.get("both") else "✗"

        print(
            f"{item['id']:12s} | "
            f"speech={predicted.get('speech_type')} {speech_mark} | "
            f"action={predicted.get('eap_action')} {action_mark} | "
            f"both={both_mark}"
        )

    print("\n" + "=" * 72)

    if args.json:
        output = {
            "model": args.model,
            "device": args.device,
            "total": total,
            "accuracy": {
                "speech_type": speech_correct / total if total else 0,
                "eap_action": action_correct / total if total else 0,
                "both": both_correct / total if total else 0,
            },
            "counts": {
                "speech_type_correct": speech_correct,
                "eap_action_correct": action_correct,
                "both_correct": both_correct,
            },
            "results": results,
        }

        print("\nJSON:")
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
