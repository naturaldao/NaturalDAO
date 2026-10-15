#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README 分布审计脚本（供 datasets/general/README.md 使用）。

README 里出现的**每一个分布数字**都由本脚本重算，输入只有仓库内公开的三个分区：

    datasets/general/data/splits/train.jsonl
    datasets/general/data/splits/test.jsonl
    datasets/general/data/splits/validation.jsonl

在仓库根目录运行：

    uv run --no-project --offline python datasets/general/readme_stats.py
    uv run --no-project --offline python datasets/general/readme_stats.py --out report.md
    uv run --no-project --offline python datasets/general/readme_stats.py --samples 3

只用标准库，不联网、不用随机数：同一份输入两次运行结果逐字节一致。

两套口径
--------
**主口径 = 能力维度**（回答"答对这道题必须会什么"，6 类，每条恰好一类）：
    math_logic 数学与形式逻辑 / reading_evidence 阅读理解与证据整合 /
    world_knowledge 世界知识及其应用 / causal_uncertainty 因果·反事实·不确定性判断 /
    social_judgment 社会与人类判断 / tool_action 工具与行动选择
**辅口径 = 内容领域**（回答"这些题讲的是哪个领域的事"，11 类，每条恰好一类）。

两套口径都由**固定优先级的规则链**产生，先命中先归属，映射表全部写死在下面的常量里，
不存在隐式规则；改一行就能看到分布怎么变。判定规则命中数会打印出来，可逐条核对。

能力归属的约定
--------------
一道题往往同时需要多种能力，本审计取**瓶颈能力**：缺了它就一定答不对的那一种。
约定（也是规则链的优先级来源）：

  1. 有候选动作/接口菜单、要选"下一步做什么" -> tool_action；
  2. 需要对数值、表格、时序、规则做形式化推演 -> math_logic；
  3. 需要从多段材料里定位、比对、整合出证据 -> reading_evidence；
  4. 需要领域知识（医学/生化/工程/人文）才能判断 -> world_knowledge；
  5. 判定对象是"证据够不够、会不会发生、有无歧义" -> causal_uncertainty；
  6. 判定对象是人的意图、情感、规范、多视角 -> social_judgment。

**这不是独立人工标注**：能力归属由来源自带的细分标签（native_domain / task / 文档类型）
经固定映射得到，因此它与来源自己的切分口径绑定。抽样复核用 --samples。
"""

import argparse
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_INPUTS = [
    os.path.join(HERE, "data", "splits", "train.jsonl"),
    os.path.join(HERE, "data", "splits", "test.jsonl"),
    os.path.join(HERE, "data", "splits", "validation.jsonl"),
]

# ---------------------------------------------------------------- 主口径：能力维度
CAPABILITIES = [
    ("tool_action", "工具与行动选择",
     "给定候选动作/接口菜单或流程规则，选出正确的下一步、路由或处置"),
    ("math_logic", "数学与形式逻辑",
     "数量关系、多步计算、条件与约束满足、规则化算法与状态推演、概率计算"),
    ("reading_evidence", "阅读理解与证据整合",
     "从多段材料里定位、比对、汇总证据；含相关性判断、抽取与压缩、事实核查"),
    ("world_knowledge", "世界知识及其应用",
     "自然科学、生命医学、工程、历史地理与人文等知识，及其在具体情境中的应用"),
    ("causal_uncertainty", "因果、反事实与不确定性判断",
     "证据是否充分、可否判定、有无歧义、风险与后果会怎样"),
    ("social_judgment", "社会与人类判断",
     "意图、情感、语境、规范与价值冲突、多视角裁断、有害内容识别"),
]

# 来源整份即为"选动作"的两族
TOOL_SOURCES = [
    "Deepexi/openai-formate-function-calling-small",
    "samatv256/jev-decisions-v1",
]

# jev-distill-corpus-v3：65 个来源原生领域标签 -> 能力维度
JEV_CAP = {
    # 工具与行动选择（25）
    "tool_selection": "tool_action",
    "support_routing": "tool_action",
    "facilities_maintenance": "tool_action",
    "hr_recruiting": "tool_action",
    "inventory_supply": "tool_action",
    "invoice_processing": "tool_action",
    "recommendation_fit": "tool_action",
    "navigation_routing": "tool_action",
    "plan_quality": "tool_action",
    "multi_agent_coord": "tool_action",
    "human_escalation": "tool_action",
    "access_permissions": "tool_action",
    "data_quality": "tool_action",
    "incident_triage": "tool_action",
    "observability": "tool_action",
    "software_delivery": "tool_action",
    "resource_placement": "tool_action",
    "communication_routing": "tool_action",
    "document_classification": "tool_action",
    "lab_biosafety": "tool_action",
    "workflow-controls-v1/invoice_processing": "tool_action",
    "workflow-controls-v1/customer_service": "tool_action",
    "workflow-controls-v1/agent_trace_observability": "tool_action",
    "workflow-controls-v1/security_incidents": "tool_action",
    "customer-control-v1": "tool_action",
    # 数学与形式逻辑（9）
    "snake-v1": "math_logic",
    "tic_tac_toe-v1": "math_logic",
    "tile_platformer-v1": "math_logic",
    "vizdoom-basic-v1": "math_logic",
    "painting-geometry-v1": "math_logic",
    "game_state_eval": "math_logic",
    "reasoning-control-v1": "math_logic",
    "temporal_reasoning": "math_logic",
    "scheduling": "math_logic",
    # 阅读理解与证据整合（5）
    "memory_relevance": "reading_evidence",
    "retrieval_relevance": "reading_evidence",
    "fact_checking": "reading_evidence",
    "summarization_control": "reading_evidence",
    "form_extraction": "reading_evidence",
    # 世界知识及其应用（17）
    "diagnostic_reasoning": "world_knowledge",
    "clinical_triage": "world_knowledge",
    "clinical_documentation": "world_knowledge",
    "patient_communication": "world_knowledge",
    "medication_safety": "world_knowledge",
    "genetic_testing": "world_knowledge",
    "variant_interpretation": "world_knowledge",
    "instrumentation": "world_knowledge",
    "simulation_modeling": "world_knowledge",
    "reaction_prediction": "world_knowledge",
    "materials_triage": "world_knowledge",
    "ecology_environment": "world_knowledge",
    "organism_taxonomy": "world_knowledge",
    "bioinformatics_ops": "world_knowledge",
    "sequence_analysis": "world_knowledge",
    "text_tradition": "world_knowledge",
    "doctrinal_reasoning": "world_knowledge",
    # 因果、反事实与不确定性判断（5）
    "hypothesis_eval": "causal_uncertainty",
    "experiment_design": "causal_uncertainty",
    "peer_review": "causal_uncertainty",
    "policy_simulation": "causal_uncertainty",
    "security_alerts": "causal_uncertainty",
    # 社会与人类判断（4）
    "sentiment_intent": "social_judgment",
    "pastoral_care": "social_judgment",
    "legal_compliance": "social_judgment",
    "research_data_mgmt": "social_judgment",
}

# tasksource/procedural-typed-decisions：13 个任务键 -> 能力维度
TS_CAP = {
    "arithmetic": "math_logic",
    "record_aggregation": "math_logic",
    "table_lookup": "math_logic",
    "needle_retrieval": "math_logic",
    "partial_observation_calibration": "math_logic",
    "entity_belief_tracking": "math_logic",
    "event_state_reconstruction": "math_logic",
    "state_perturbation": "math_logic",
    "evidence_sufficiency": "math_logic",
    "policy_applicability": "math_logic",
    "multi_view_adjudication": "tool_action",
    "taxonomy_routing": "tool_action",
    "policy_under_uncertainty": "causal_uncertainty",
}

# dwidlee/systemone-lite-general：任务键前缀 -> 能力维度
SYSTEMONE_CAP = [
    ("task:alloc.", "social_judgment"),
    ("task:debate.", "social_judgment"),
    ("task:ticket.", "tool_action"),
]

# ZefanCai/Open-Jev：原生域 -> 能力维度
OPENJEV_CAP = {
    "source:customer-control-v1": "tool_action",
    "source:vizdoom-basic-v1": "math_logic",
}

# kaivoss/system-one-270m-data：28 种文档类型 -> 能力维度
KAIVOSS_CAP = {
    "bug report": "tool_action",
    "customer support email": "tool_action",
    "database migration plan": "tool_action",
    "changelog entry": "tool_action",
    "IT helpdesk ticket": "tool_action",
    "git diff / code review": "tool_action",
    "application error log": "tool_action",
    "API request/response trace": "tool_action",
    "incident postmortem": "tool_action",
    "CI pipeline output": "tool_action",
    "internal Slack thread": "tool_action",
    "sales call transcript": "tool_action",
    "insurance claim": "tool_action",
    "meeting notes": "tool_action",
    "user feedback survey response": "tool_action",
    "job application": "tool_action",
    "product review": "tool_action",
    "financial transaction record": "tool_action",
    "shipping/logistics exception": "tool_action",
    "legal contract clause": "tool_action",
    "real estate listing enquiry": "tool_action",
    "forum question": "tool_action",
    "medical triage note": "world_knowledge",
    "academic abstract": "world_knowledge",
    "news wire copy": "world_knowledge",
    "recipe or how-to": "world_knowledge",
    "content moderation queue item": "social_judgment",
    "security alert": "causal_uncertainty",
}

# 中文补充集：覆盖域 -> 能力维度
ZH_CAP = {"risk_harm": "social_judgment", "human_judgment": "social_judgment"}

# ---------------------------------------------------------------- 辅口径：内容领域
CONTENTS = [
    ("tool_api", "工具调用与 API 操作"),
    ("safety_risk", "安全、风险与有害内容"),
    ("business_ops", "业务运营与客户服务"),
    ("world_humanities", "世界知识、人文与信息检索"),
    ("social_norms", "社会规范、法律与公共决策"),
    ("science_engineering", "自然科学与工程"),
    ("logic_game", "逻辑、空间与博弈推理"),
    ("software_systems", "软件、系统与数据工程"),
    ("medical_health", "医疗与生命健康"),
    ("math_structured", "数学、表格与结构化计算"),
    ("language_text", "语言、情感与文本处理"),
]

JEV_CONTENT = {
    "tool_selection": "tool_api",
    "snake-v1": "logic_game", "tic_tac_toe-v1": "logic_game", "tile_platformer-v1": "logic_game",
    "vizdoom-basic-v1": "logic_game", "painting-geometry-v1": "logic_game",
    "game_state_eval": "logic_game", "reasoning-control-v1": "logic_game",
    "data_quality": "software_systems", "incident_triage": "software_systems",
    "observability": "software_systems", "software_delivery": "software_systems",
    "plan_quality": "software_systems", "multi_agent_coord": "software_systems",
    "resource_placement": "software_systems",
    "workflow-controls-v1/agent_trace_observability": "software_systems",
    "diagnostic_reasoning": "medical_health", "clinical_triage": "medical_health",
    "clinical_documentation": "medical_health", "patient_communication": "medical_health",
    "medication_safety": "medical_health", "genetic_testing": "medical_health",
    "variant_interpretation": "medical_health",
    "hypothesis_eval": "science_engineering", "peer_review": "science_engineering",
    "research_data_mgmt": "science_engineering", "experiment_design": "science_engineering",
    "instrumentation": "science_engineering", "simulation_modeling": "science_engineering",
    "reaction_prediction": "science_engineering", "materials_triage": "science_engineering",
    "ecology_environment": "science_engineering", "organism_taxonomy": "science_engineering",
    "bioinformatics_ops": "science_engineering", "sequence_analysis": "science_engineering",
    "memory_relevance": "world_humanities", "retrieval_relevance": "world_humanities",
    "fact_checking": "world_humanities", "text_tradition": "world_humanities",
    "doctrinal_reasoning": "world_humanities",
    "security_alerts": "safety_risk", "workflow-controls-v1/security_incidents": "safety_risk",
    "access_permissions": "safety_risk", "human_escalation": "safety_risk",
    "lab_biosafety": "safety_risk",
    "policy_simulation": "social_norms", "legal_compliance": "social_norms",
    "pastoral_care": "social_norms",
    "support_routing": "business_ops", "facilities_maintenance": "business_ops",
    "hr_recruiting": "business_ops", "inventory_supply": "business_ops",
    "invoice_processing": "business_ops", "scheduling": "business_ops",
    "temporal_reasoning": "business_ops", "navigation_routing": "business_ops",
    "recommendation_fit": "business_ops",
    "workflow-controls-v1/invoice_processing": "business_ops",
    "workflow-controls-v1/customer_service": "business_ops",
    "customer-control-v1": "business_ops",
    "form_extraction": "language_text", "summarization_control": "language_text",
    "sentiment_intent": "language_text", "document_classification": "language_text",
    "communication_routing": "language_text",
}

TS_CONTENT = {
    "arithmetic": "math_structured", "record_aggregation": "math_structured",
    "table_lookup": "math_structured", "needle_retrieval": "math_structured",
    "partial_observation_calibration": "math_structured",
    "entity_belief_tracking": "logic_game", "event_state_reconstruction": "logic_game",
    "state_perturbation": "logic_game", "evidence_sufficiency": "logic_game",
    "multi_view_adjudication": "business_ops", "taxonomy_routing": "business_ops",
    "policy_applicability": "safety_risk", "policy_under_uncertainty": "safety_risk",
}

SYSTEMONE_CONTENT = [
    ("task:alloc.", "social_norms"), ("task:debate.", "social_norms"),
    ("task:ticket.", "business_ops"),
]

OPENJEV_CONTENT = {"source:customer-control-v1": "business_ops",
                   "source:vizdoom-basic-v1": "logic_game"}

KAIVOSS_CONTENT = {
    "bug report": "software_systems", "database migration plan": "software_systems",
    "changelog entry": "software_systems", "IT helpdesk ticket": "software_systems",
    "git diff / code review": "software_systems", "application error log": "software_systems",
    "API request/response trace": "software_systems", "incident postmortem": "software_systems",
    "CI pipeline output": "software_systems",
    "customer support email": "business_ops", "internal Slack thread": "business_ops",
    "sales call transcript": "business_ops", "insurance claim": "business_ops",
    "meeting notes": "business_ops", "user feedback survey response": "business_ops",
    "job application": "business_ops", "product review": "business_ops",
    "forum question": "business_ops", "financial transaction record": "business_ops",
    "shipping/logistics exception": "business_ops", "legal contract clause": "business_ops",
    "real estate listing enquiry": "business_ops",
    "medical triage note": "medical_health", "security alert": "safety_risk",
    "content moderation queue item": "safety_risk",
    "news wire copy": "world_humanities", "recipe or how-to": "world_humanities",
    "academic abstract": "world_humanities",
}

ZH_CONTENT = {"risk_harm": "safety_risk", "human_judgment": "safety_risk"}


def _pick(mapping, key, fallback):
    return mapping.get(key, fallback)


def classify_capability(item):
    """能力维度（主口径）。返回 (维度, 命中的规则名)。"""
    src = item.get("source") or {}
    meta = item.get("meta") or {}
    ds = src.get("dataset") or ""
    rule = meta.get("domain_rule") or ""

    if ds in TOOL_SOURCES:
        return "tool_action", "C1-整份来源"
    if ds == "SargeDev/jev-distill-corpus-v3":
        nd = meta.get("native_domain")
        if nd in JEV_CAP:
            return JEV_CAP[nd], "C2-原生领域标签"
        return "other", "C2-未命中"
    if ds == "tasksource/procedural-typed-decisions":
        task = rule.replace("task:", "")
        if task in TS_CAP:
            return TS_CAP[task], "C3-任务键"
        return "other", "C3-未命中"
    if ds == "dwidlee/systemone-lite-general":
        for prefix, cap in SYSTEMONE_CAP:
            if rule.startswith(prefix):
                return cap, "C4-任务键前缀"
        return "other", "C4-未命中"
    if ds == "ZefanCai/Open-Jev":
        if rule in OPENJEV_CAP:
            return OPENJEV_CAP[rule], "C5-来源原生域"
        return "other", "C5-未命中"
    if ds == "kaivoss/system-one-270m-data":
        nd = meta.get("native_domain")
        if nd in KAIVOSS_CAP:
            return KAIVOSS_CAP[nd], "C6-文档类型"
        return "other", "C6-未命中"
    if item.get("domain") in ZH_CAP:
        return ZH_CAP[item["domain"]], "C7-中文补充域"
    return "other", "C8-未命中"


def classify_content(item):
    """内容领域（辅口径）。返回 (领域, 命中的规则名)。"""
    src = item.get("source") or {}
    meta = item.get("meta") or {}
    ds = src.get("dataset") or ""
    rule = meta.get("domain_rule") or ""

    if ds in TOOL_SOURCES:
        return "tool_api", "R1-整份来源"
    if ds == "SargeDev/jev-distill-corpus-v3":
        nd = meta.get("native_domain")
        if nd in JEV_CONTENT:
            return JEV_CONTENT[nd], "R2-原生领域标签"
        return "other", "R2-未命中"
    if ds == "tasksource/procedural-typed-decisions":
        task = rule.replace("task:", "")
        if task in TS_CONTENT:
            return TS_CONTENT[task], "R3-任务键"
        return "other", "R3-未命中"
    if ds == "dwidlee/systemone-lite-general":
        for prefix, c in SYSTEMONE_CONTENT:
            if rule.startswith(prefix):
                return c, "R4-任务键前缀"
        return "other", "R4-未命中"
    if ds == "ZefanCai/Open-Jev":
        if rule in OPENJEV_CONTENT:
            return OPENJEV_CONTENT[rule], "R5-来源原生域"
        return "other", "R5-未命中"
    if ds == "kaivoss/system-one-270m-data":
        nd = meta.get("native_domain")
        if nd in KAIVOSS_CONTENT:
            return KAIVOSS_CONTENT[nd], "R6-文档类型"
        return "other", "R6-未命中"
    if item.get("domain") in ZH_CONTENT:
        return ZH_CONTENT[item["domain"]], "R7-中文补充域"
    return "other", "R8-未命中"


def target_shape(target):
    """真值形态：real / one_hot / uniform / answer_only（口径同 CONTRACT.md 2.3）。"""
    probs = target.get("probs")
    if not probs:
        return "answer_only"
    values = list(probs.values())
    if max(values) == min(values):
        return "uniform"
    if set(values) <= {0, 1} and sum(1 for v in values if v) == 1:
        return "one_hot"
    return "real"


def main(argv=None):
    ap = argparse.ArgumentParser(description="复算 datasets/general/README.md 里的分布数字")
    ap.add_argument("--items", nargs="*", default=None, help="覆盖输入文件（默认公开三个分区）")
    ap.add_argument("--out", default=None, help="把报告写到该文件（UTF-8），默认打印到 stdout")
    ap.add_argument("--samples", type=int, default=0, help="每个类打印 N 条抽样（人工复核）")
    args = ap.parse_args(argv)
    inputs = args.items or DEFAULT_INPUTS

    total = 0
    per_split = collections.Counter()
    lang = collections.Counter()
    lang_split = collections.defaultdict(collections.Counter)
    datasets = collections.Counter()
    cap = collections.Counter()
    cap_split = collections.defaultdict(collections.Counter)
    cap_lang = collections.defaultdict(collections.Counter)
    cap_src = collections.defaultdict(set)
    cap_rule = collections.Counter()
    con = collections.Counter()
    con_lang = collections.defaultdict(collections.Counter)
    con_src = collections.defaultdict(set)
    cross = collections.defaultdict(collections.Counter)
    kind_q = collections.Counter()
    kind_item = collections.defaultdict(collections.Counter)
    q_per_item = collections.Counter()
    opt_hist = collections.Counter()
    score_hist = collections.Counter()
    shapes = collections.Counter()
    native_labels = set()
    native_labels_by_ds = collections.defaultdict(set)
    tool_opt = collections.Counter()
    option_vocab = set()
    api_names_zh = set()
    samples_cap = collections.defaultdict(list)
    samples_con = collections.defaultdict(list)
    origin = collections.Counter()
    origin_split = collections.defaultdict(collections.Counter)
    domains = collections.Counter()
    ids_by_split = collections.defaultdict(set)
    groups_by_split = collections.defaultdict(set)
    states_by_split = collections.defaultdict(set)

    for path in inputs:
        if not os.path.exists(path):
            sys.stderr.write("缺少输入文件：%s\n" % path)
            return 2
        name = os.path.basename(path).replace(".jsonl", "")
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                ds = (item.get("source") or {}).get("dataset")
                total += 1
                per_split[name] += 1
                lang[item.get("lang")] += 1
                lang_split[name][item.get("lang")] += 1
                datasets[ds] += 1
                om = item.get("meta") or {}
                org = (om.get("origin") or item.get("origin")
                       or om.get("question_origin") or "unknown")
                origin[org] += 1
                origin_split[org][name] += 1
                domains[item.get("domain")] += 1
                ids_by_split[name].add(item.get("id"))
                gid = ((item.get("meta") or {}).get("group_id")
                       or (item.get("meta") or {}).get("request_id"))
                if gid:                      # 没有显式分组键的条目不进组集合
                    groups_by_split[name].add(gid)
                states_by_split[name].add(
                    " ".join((item.get("state") or "").split()).lower())

                c, crule = classify_capability(item)
                cap[c] += 1
                cap_split[c][name] += 1
                cap_lang[c][item.get("lang")] += 1
                cap_src[c].add(ds)
                cap_rule[crule] += 1

                k, _krule = classify_content(item)
                con[k] += 1
                cross[c][k] += 1
                con_lang[k][item.get("lang")] += 1
                con_src[k].add(ds)

                if args.samples and len(samples_cap[c]) < args.samples:
                    q = (item.get("questions") or [{}])[0]
                    samples_cap[c].append((item.get("id"), item.get("lang"),
                                           (item.get("state") or "").replace("\n", " ")[:105],
                                           (q.get("prompt") or "").replace("\n", " ")[:85]))
                if args.samples and len(samples_con[k]) < args.samples:
                    q = (item.get("questions") or [{}])[0]
                    samples_con[k].append((item.get("id"), item.get("lang"),
                                           (item.get("state") or "").replace("\n", " ")[:105],
                                           (q.get("prompt") or "").replace("\n", " ")[:85]))

                qs = item.get("questions") or []
                q_per_item[len(qs)] += 1
                for kind in set(q.get("kind") for q in qs):
                    kind_item[kind][c] += 1
                for q in qs:
                    kind_q[q.get("kind")] += 1
                    if q.get("kind") == "choice":
                        opts = q.get("options") or []
                        opt_hist[len(opts)] += 1
                        if c == "tool_action":
                            tool_opt[len(opts)] += 1
                        for o in opts:
                            option_vocab.add(str(o.get("key")))
                            if ds == "Deepexi/openai-formate-function-calling-small":
                                api_names_zh.add(str(o.get("key")))
                    if q.get("kind") == "score":
                        sc = q.get("scale") or {}
                        if sc.get("min") is not None and sc.get("max") is not None:
                            score_hist[int(sc["max"]) - int(sc["min"]) + 1] += 1
                for t in (item.get("targets") or {}).values():
                    shapes[target_shape(t)] += 1
                nd = (item.get("meta") or {}).get("native_domain")
                if nd:
                    native_labels.add(str(nd))
                    native_labels_by_ds[ds].add(str(nd))

    def pct(n, d):
        return "%.2f%%" % (100.0 * n / d) if d else "—"

    out = io.StringIO()
    w = out.write
    w("# datasets/general 分布审计报告\n\n输入（仓库内公开文件）：\n\n")
    for path in inputs:
        w("- @@BT@@" + os.path.relpath(path, REPO).replace("\\", "/") + "@@BT@@\n")

    w("\n## 0. 总量与覆盖面\n\n| 指标 | 数值 |\n|---|---:|\n")
    w("| 条目总数 | %d |\n" % total)
    w("| 问题总数 | %d |\n" % sum(kind_q.values()))
    for k in ("train", "test", "validation"):
        w("| 其中 %s | %d |\n" % (k, per_split[k]))
    w("| 独立来源数 | %d |\n" % len(datasets))
    w("| 来源自带细分领域标签取值数 | %d |\n" % len(native_labels))
    w("| 出现过的不同选项/接口名 | %d |\n" % len(option_vocab))
    w("| 其中中文云服务类的不同接口名 | %d |\n" % len(api_names_zh))
    w("| 英文条目 | %d（%s） |\n" % (lang.get("en", 0), pct(lang.get("en", 0), total)))
    w("| 中文条目 | %d（%s） |\n" % (lang.get("zh", 0), pct(lang.get("zh", 0), total)))
    w("| 能力维度未归类 | %d |\n" % cap.get("other", 0))
    w("\n成色分层（meta.origin / meta.question_origin）：\n\n| 层级 | 条目 | 说明 |\n|---|---:|---|\n")
    w("| source（原生四元组） | %d | 情境、候选与答案都来自来源原文 |\n" % origin.get("source", 0))
    w("| taxonomy（单标签转换） | %d | 由单标签转换而来，只进 train |\n" % origin.get("taxonomy", 0))
    if origin.get("unknown"):
        w("| 未标注 | %d | |\n" % origin["unknown"])
    w("\n其中 taxonomy 层按分区：%s\n" % "、".join(
        "%s %d" % (k, origin_split["taxonomy"].get(k, 0))
        for k in ("train", "test", "validation")))
    w("\n记录里 domain 字段（机制口径，见 CONTRACT.md 第 3 节）的分布：\n\n")
    w("| domain | 条目 | 占比 |\n|---|---:|---:|\n")
    for d, n in domains.most_common():
        w("| %s | %d | %s |\n" % (d, n, pct(n, total)))
    w("\n细分领域标签（meta.native_domain）取值数按来源：\n\n| 来源 | 取值数 |\n|---|---:|\n")
    for ds, labels in sorted(native_labels_by_ds.items(), key=lambda kv: -len(kv[1])):
        w("| %s | %d |\n" % (ds, len(labels)))
    if tool_opt:
        tsz = sorted(tool_opt.elements())
        w("\n工具与行动选择一维的 choice 选项数：最小 %d、中位 %d、最大 %d。\n" % (
            tsz[0], tsz[len(tsz) // 2], tsz[-1]))
    w("\n分区 × 语言：\n\n| 分区 | 英文 | 中文 | 合计 |\n|---|---:|---:|---:|\n")
    for k in ("train", "test", "validation"):
        w("| %s | %d | %d | %d |\n" % (k, lang_split[k].get("en", 0),
                                       lang_split[k].get("zh", 0), per_split[k]))
    w("\n来源占比（公开三区内最大的三个）：\n\n| 来源 | 条目 | 占比 |\n|---|---:|---:|\n")
    for ds, n in datasets.most_common(3):
        w("| %s | %d | %s |\n" % (ds, n, pct(n, total)))
    w("\n最大的单一来源占 **%s**。\n" % pct(datasets.most_common(1)[0][1], total))

    w("\n## 1. 能力维度审计（主口径，每条恰好一类）\n\n")
    w("| 能力维度 | 条目 | 占比 | 英文 | 中文 | 覆盖来源数 |\n|---|---:|---:|---:|---:|---:|\n")
    for key, zhname, _ in CAPABILITIES:
        n = cap.get(key, 0)
        w("| %s | %d | %s | %d | %d | %d |\n" % (
            zhname, n, pct(n, total), cap_lang[key].get("en", 0),
            cap_lang[key].get("zh", 0), len(cap_src[key])))
    w("| **合计** | **%d** | **100.00%%** | **%d** | **%d** | **%d** |\n" % (
        total, lang.get("en", 0), lang.get("zh", 0), len(datasets)))

    w("\n判定规则命中（能力维度）：\n\n| 规则 | 命中条目 |\n|---|---:|\n")
    for r, c in sorted(cap_rule.items()):
        w("| %s | %d |\n" % (r, c))

    w("\n工具与行动选择一类的内部构成：\n\n| 子类 | 条目 | 占全部 |\n|---|---:|---:|\n")
    tool_n = cap.get("tool_action", 0)
    sub = sum(datasets.get(d, 0) for d in TOOL_SOURCES)
    w("| 中文云服务接口选择 | %d | %s |\n" % (datasets.get(TOOL_SOURCES[0], 0),
                                              pct(datasets.get(TOOL_SOURCES[0], 0), total)))
    w("| 英文智能体工具选择 | %d | %s |\n" % (datasets.get(TOOL_SOURCES[1], 0),
                                              pct(datasets.get(TOOL_SOURCES[1], 0), total)))
    w("| 其余（流程路由、处置与判定） | %d | %s |\n" % (tool_n - sub, pct(tool_n - sub, total)))

    w("\n## 2. 能力维度 × 分区\n\n| 能力维度 | train | test | validation |\n|---|---:|---:|---:|\n")
    for key, zhname, _ in CAPABILITIES:
        w("| %s | %d | %d | %d |\n" % (zhname, cap_split[key].get("train", 0),
                                       cap_split[key].get("test", 0),
                                       cap_split[key].get("validation", 0)))
    w("| **合计** | **%d** | **%d** | **%d** |\n" % (
        per_split["train"], per_split["test"], per_split["validation"]))

    w("\n含各原语的条目数（互不排斥，按能力维度）：\n\n")
    w("| 能力维度 | 含 choice | 含 noul | 含 score |\n|---|---:|---:|---:|\n")
    for key, zhname, _ in CAPABILITIES:
        w("| %s | %d | %d | %d |\n" % (zhname, kind_item["choice"][key],
                                       kind_item["noul"][key], kind_item["score"][key]))

    w("\n### 2.4 能力维度 × 内容领域（交叉表，行合计 = 该能力维度条目数）\n\n")
    w("| 能力维度 \\ 内容领域 | " + " | ".join(zh for _k, zh in CONTENTS) + " | 合计 |\n")
    w("|---|" + "---:|" * (len(CONTENTS) + 1) + "\n")
    for key, zhname, _ in CAPABILITIES:
        cells = " | ".join(str(cross[key].get(ck, 0)) for ck, _ in CONTENTS)
        w("| %s | %s | %d |\n" % (zhname, cells, cap.get(key, 0)))

    w("\n## 3. 内容领域分布（辅口径，每条恰好一类）\n\n")
    w("| 内容领域 | 条目 | 占比 | 英文 | 中文 | 覆盖来源数 |\n|---|---:|---:|---:|---:|---:|\n")
    for key, zhname in CONTENTS:
        n = con.get(key, 0)
        w("| %s | %d | %s | %d | %d | %d |\n" % (
            zhname, n, pct(n, total), con_lang[key].get("en", 0),
            con_lang[key].get("zh", 0), len(con_src[key])))
    w("| **合计** | **%d** | **100.00%%** | **%d** | **%d** | **%d** |\n" % (
        total, lang.get("en", 0), lang.get("zh", 0), len(datasets)))

    w("\n## 4. 问题形态与规模\n\n问题级（一条可含多题，故不相加）：\n\n")
    w("| 原语 | 问题数 | 占比 |\n|---|---:|---:|\n")
    qtotal = sum(kind_q.values())
    for k in ("choice", "noul", "score"):
        w("| %s | %d | %s |\n" % (k, kind_q[k], pct(kind_q[k], qtotal)))
    w("| **合计** | **%d** | **100.00%%** |\n" % qtotal)
    w("\n条目级（互不排斥）：\n\n| 原语 | 条目数 | 占全部条目 |\n|---|---:|---:|\n")
    for k in ("choice", "noul", "score"):
        s = sum(kind_item[k].values())
        w("| %s | %d | %s |\n" % (k, s, pct(s, total)))
    w("\n条目挂载的问题数分布：\n\n| 每条题数 | 条目数 |\n|---:|---:|\n")
    for n_, c in sorted(q_per_item.items()):
        w("| %d | %d |\n" % (n_, c))
    w("\nchoice 题选项数：\n\n| 选项数 | 题目数 |\n|---:|---:|\n")
    sizes = sorted(opt_hist.elements())
    for n_, c in sorted(opt_hist.items()):
        w("| %d | %d |\n" % (n_, c))
    if sizes:
        w("\n最小 %d、最大 %d、中位 %d。\n" % (sizes[0], sizes[-1], sizes[len(sizes) // 2]))
    w("\nscore 题档位数：\n\n| 档位数 | 题目数 |\n|---:|---:|\n")
    for n_, c in sorted(score_hist.items()):
        w("| %d | %d |\n" % (n_, c))

    w("\n## 5. 真值形态（问题级，口径同 CONTRACT.md 2.3）\n\n")
    w("| 形态 | 问题数 | 占比 |\n|---|---:|---:|\n")
    stotal = sum(shapes.values())
    for k, label in (("real", "真概率分布"), ("one_hot", "硬标签单点分布"),
                     ("uniform", "均匀分布（无信息）"), ("answer_only", "只有答案、无分布")):
        w("| %s | %d | %s |\n" % (label, shapes.get(k, 0), pct(shapes.get(k, 0), stotal)))
    w("\n%d 个问题全部带真值答案。\n" % stotal)

    w("\n## 6. 泄漏检查（公开三区两两之间）\n\n")
    w("口径：id 逐字相同；组 = meta.group_id 或 meta.request_id；"
      "归一化情境 = 去掉首尾与连续空白后转小写。\n\n")
    w("| 组合 | id 重叠 | 组重叠 | 归一化情境重叠 |\n|---|---:|---:|---:|\n")
    order = ["train", "test", "validation"]
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a, b = order[i], order[j]
            w("| %s ∩ %s | %d | %d | %d |\n" % (
                a, b,
                len(ids_by_split[a] & ids_by_split[b]),
                len(groups_by_split[a] & groups_by_split[b]),
                len(states_by_split[a] & states_by_split[b])))
    w("\n各组独立取值数：%s\n" % "、".join(
        "%s id %d / 组 %d / 归一化情境 %d" % (k, len(ids_by_split[k]),
                                             len(groups_by_split[k]), len(states_by_split[k]))
        for k in order))

    if args.samples:
        w("\n## 7. 抽样（人工复核）\n\n### 7.1 按能力维度\n")
        for key, zhname, _ in CAPABILITIES:
            w("\n**%s**\n\n" % zhname)
            for sid, lg, st, pr in samples_cap.get(key, []):
                w("- @@BT@@" + str(sid) + "@@BT@@ [" + str(lg) + "] " + st + " | " + pr + "\n")
        w("\n### 7.2 按内容领域\n")
        for key, zhname in CONTENTS:
            w("\n**%s**\n\n" % zhname)
            for sid, lg, st, pr in samples_con.get(key, []):
                w("- @@BT@@" + str(sid) + "@@BT@@ [" + str(lg) + "] " + st + " | " + pr + "\n")

    text = out.getvalue().replace("@@BT@@", chr(96))
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        sys.stdout.write("已写入 %s（%d 条，%d 个问题）\n" % (args.out, total, sum(kind_q.values())))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
