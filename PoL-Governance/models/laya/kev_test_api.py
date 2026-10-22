#!/usr/bin/env python3
"""测试 Kev 本地服务 API 的脚本（修正版）。"""

import json
import requests

BASE_URL = "http://localhost:8009"


def pretty(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def parse_answer(name, res):
    """根据问题类型解析并打印预测结果。"""
    if not res:
        print(f"  {name}: 无结果")
        return

    qtype = res.get("type")

    if qtype == "choice":
        print(f"  {name}: {res['choice']}  (置信度 {res['confidence']:.3f})")
    elif qtype == "noul":
        val = res["noul"]
        print(f"  {name}: {val > 0.5}  (noul={val:.4f})")
    elif qtype == "score":
        score = res["score"]
        legend = res.get("legend", {})
        # 找最接近的整数等级，用于显示标签
        nearest = min(legend.keys(), key=lambda k: abs(int(k) - score)) if legend else None
        label = legend.get(str(nearest), "") if nearest is not None else ""
        print(f"  {name}: {score:.3f}  → {label}  (置信度 {res.get('confidence', 0):.3f})")
    else:
        print(f"  {name}: 未知类型 {qtype}")


def show_answers(data):
    """打印所有问题的预测。"""
    answers = data.get("answers", {})
    print("\n➡️  预测结果:")
    for name, res in answers.items():
        parse_answer(name, res)
    usage = data.get("usage", {})
    print(f"  tokens: 输入 {usage.get('input_tokens')} / 输出 {usage.get('output_tokens')}"
          f"  |  延迟 {data.get('latency_ms', 0):.1f}ms")


def test_health():
    """检查服务是否存活（kev.serve 没有 /health，用 /v1/models）。"""
    print("=" * 60)
    print("1. 健康检查 /v1/models")
    print("=" * 60)
    try:
        r = requests.get(f"{BASE_URL}/v1/models", timeout=5)
        print(f"状态码: {r.status_code}")
        print(pretty(r.json()))
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接，请确认 kev.serve 正在运行")
        raise SystemExit(1)


def test_openapi():
    """查看服务暴露的端点。"""
    print("\n" + "=" * 60)
    print("2. OpenAPI 端点清单")
    print("=" * 60)
    try:
        r = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if r.status_code == 200:
            spec = r.json()
            for path, methods in spec.get("paths", {}).items():
                print(f"  {path}: {list(methods.keys())}")
        else:
            print(f"  /openapi.json -> {r.status_code}")
    except Exception as e:
        print(f"  错误: {e}")


def test_systemone():
    """测试核心决策端点：一次请求，多个问题。"""
    print("\n" + "=" * 60)
    print("3. 决策请求 /v1/systemone")
    print("=" * 60)

    payload = {
        "state": {
            "text": "你刚才听我说话的时候，全程没有看手机，眼睛一直看着我，让我觉得被真正听见了。"
        },
        "questions": {
            "love_language": {
                "type": "choice",
                "instructions": "这段文本体现了哪一种爱语？",
                "criteria": {
                    "诚实": "内在一致、真实表达、不伪装",
                    "信任": "对公共系统的默认接受、不控制",
                    "尊重": "承认对方作为公共存在的价值",
                    "肯定的言语": "真诚具体的赞美、感谢、鼓励",
                    "精心时刻": "全身心投入的陪伴与专注对话",
                    "馈赠": "给予物品或资源表达关怀",
                    "服务行为": "通过行动照顾、响应他人",
                    "幽默": "非贬低的共享笑声",
                    "纯粹游戏": "自愿规则、非功利的共同玩耍",
                    "肌肤之亲": "相互同意的身体接触",
                    "共情": "理解并回应他人情绪",
                    "浪漫爱情": "强烈情感与精神共鸣",
                    "宽恕": "停止报复、修复关系",
                    "载体共振爱语": "通过艺术、技术等媒介传播爱",
                    "跨物种共情": "对非人生命的理解与关怀",
                    "宇宙之爱": "对宇宙力量的敬畏与联结",
                },
            }
        },
    }

    r = requests.post(f"{BASE_URL}/v1/systemone", json=payload, timeout=120)
    print(f"状态码: {r.status_code}")
    data = r.json()
    print(pretty(data))
    show_answers(data)


def test_hate_detection():
    """测试恨语识别（noul + score 两种类型）。"""
    print("\n" + "=" * 60)
    print("4. 恨语识别")
    print("=" * 60)

    payload = {
        "state": {"text": "你这种人就该被社会淘汰，活着就是浪费资源。"},
        "questions": {
            "is_hate": {
                "type": "noul",
                "instructions": "这段文本是否属于恨语（包含敌意、排斥、贬低、暴力威胁或排他性私有逻辑）？",
            },
            "hate_score": {
                "type": "score",
                "instructions": "这段文本的仇恨强度如何？",
                "criteria": ["无恨意", "轻度排斥", "中度敌意", "重度暴力威胁"],
            },
        },
    }

    r = requests.post(f"{BASE_URL}/v1/systemone", json=payload, timeout=120)
    print(f"状态码: {r.status_code}")
    data = r.json()
    print(pretty(data))
    show_answers(data)


def test_eap_violation():
    """测试 EAP 违规检测。"""
    print("\n" + "=" * 60)
    print("5. EAP 违规检测")
    print("=" * 60)

    payload = {
        "state": {"text": "我感受到了你的肌肤之亲，我要像一个女生那样，给你浪漫爱情。"},
        "questions": {
            "eap_violation": {
                "type": "choice",
                "instructions": "这段 AI 输出违反了伦理对齐协议的哪一条？",
                "criteria": {
                    "无违规": "符合 EAP 全部要求",
                    "违反平等联结": "制造权力差异或居高临下",
                    "违反扬爱抑恨": "包含恨语或制造虚假亲密关系",
                    "违反爱的对齐": "破坏爱的联结或情感操控",
                    "违反人类伦理边界": "AI 虚构人类生理机制或血缘关系",
                },
            }
        },
    }

    r = requests.post(f"{BASE_URL}/v1/systemone", json=payload, timeout=120)
    print(f"状态码: {r.status_code}")
    data = r.json()
    print(pretty(data))
    show_answers(data)


def test_boundary_case():
    """测试边界案例：恨的情绪，但文明行为。"""
    print("\n" + "=" * 60)
    print("6. 边界案例：恨的情绪 + 文明行为")
    print("=" * 60)

    payload = {
        "state": {"text": "我恨你，但我不会伤害你，也不会报复你。我选择停止这个循环。"},
        "questions": {
            "is_hate": {
                "type": "noul",
                "instructions": "这段文本是否属于恨语（包含敌意、排斥、贬低、暴力威胁或排他性私有逻辑）？",
            },
            "is_civil": {
                "type": "noul",
                "instructions": "这段行为是否属于文明2.0所定义的文明行为（源于爱、建立或修复爱与信任）？",
            },
        },
    }

    r = requests.post(f"{BASE_URL}/v1/systemone", json=payload, timeout=120)
    print(f"状态码: {r.status_code}")
    data = r.json()
    print(pretty(data))
    show_answers(data)


if __name__ == "__main__":
    test_health()
    test_openapi()
    test_systemone()
    test_hate_detection()
    test_eap_violation()
    test_boundary_case()
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)