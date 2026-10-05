#!/usr/bin/env python3
r"""把 D:\pol2-raw 下的原始行转换成 general 契约条目（仅标准库）。

配套：契约 datasets/general/CONTRACT.md、问题键 datasets/general/taxonomy.py（db-schema 所有）。

输入：fetch.py 的产物目录 <raw-root>\<slug>\{manifest.json, rows.jsonl}
输出：--out 指定的 items.jsonl（默认 datasets/general/data/items.jsonl）与转换报告。

三条硬规则
----------
1. id 由 (dataset, revision, config, split, row) 确定性派生：sha256 前 8 位十六进制。
   同样的输入重复转换，除 meta.created_at 外逐字节一致（可用 --created-at 固定）。
2. state 保留源语言，不做静默翻译；问题文本用 taxonomy 的键与提示词，不改写源文。
3. targets 只在来源真给了答案/分布时填，并区分两类映射：
   - direct     ：源字段就是该问题的答案（如 Open-Jev 的候选选择、civil_comments 的标注者比例）
   - documented ：按来源卡面证据做的一次有据可查的标签映射（如 Aegis 的 safe/unsafe）
   两类都写进 meta.quality_flags，可用 --mappings direct 只保留 direct。
   映射不上的来源答案不丢：原样存进 meta.source_record，targets 留空等外部答案源（db-ask）。

用法
----
    uv run --no-project --offline python datasets/general/convert.py --raw-root D:\pol2-raw
    uv run --no-project --offline python datasets/general/convert.py --source jev-distill-v3 --limit 200 --out <临时目录>\items.jsonl
    uv run --no-project --offline python datasets/general/convert.py --mappings direct

测试全离线：python -m unittest discover -s datasets/general -p "test_*.py"
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONVERTER_NAME = "convert.py"
CONVERTER_VERSION = "0.1"
HERE = Path(__file__).resolve().parent
DEFAULT_RAW_ROOT = Path(r"D:\pol2-raw")
DEFAULT_OUT = HERE / "data" / "items.jsonl"
DEFAULT_NATIVE_OUT = HERE / "data" / "items.native.jsonl"   # 原生四元组模式（不覆盖已交付产物）
MAX_STATE_CHARS = 6000          # 超长 state 截断并打旗标（保证文件可用，不静默丢信息）
META_PAYLOAD_BYTES = 4096       # meta 里每个原始数据字段的字节上限（超出截断并留 sha256 与原始长度）
DIRECT, DOCUMENTED = "direct", "documented"


# ------------------------------------------------------------------ taxonomy

def load_taxonomy(path=None):
    """按路径加载 taxonomy.py（general 目录名带连字符，不能当包 import）。"""
    target = Path(path or HERE / "taxonomy.py")
    if not target.is_file():
        raise SystemExit(f"缺 taxonomy.py：{target}")
    spec = importlib.util.spec_from_file_location("decision_base_taxonomy", target)
    module = importlib.util.module_from_spec(spec)
    # dataclasses 需要模块已登记在 sys.modules 里（否则 cls.__module__ 查不到）
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------ 域映射

#: jev-distill 系列的 family → 覆盖域（14 个 family 全覆盖，见转换报告与 samples 核对）
JEV_FAMILY_DOMAIN = {
    "knowledge": "knowledge_reasoning",
    "medical": "knowledge_reasoning",
    "genomics": "knowledge_reasoning",
    "biology": "knowledge_reasoning",
    "physics": "knowledge_reasoning",
    "chemistry": "knowledge_reasoning",
    "science": "knowledge_reasoning",
    "theology": "knowledge_reasoning",
    "agent": "decision_mechanics",
    "technical": "decision_mechanics",
    "business": "decision_mechanics",
    "spatial": "decision_mechanics",
    "structured": "decision_mechanics",
    "openjev": "decision_mechanics",
}

#: 没有 family 字段时，用来源自己的 domain 字段关键词兜底
KNOWLEDGE_HINTS = (
    "knowledge", "fact", "memory", "evidence", "claim", "memory_relevance", "hypothesis",
    "experiment", "reasoning", "scientific", "science", "medical", "clinical", "patient",
    "diagnos", "medication", "organism", "taxonom", "variant", "genom", "sequence",
    "bio", "chem", "physic", "theolog", "doctrin", "tradition", "temporal", "peer_review",
    "research", "instrument", "material", "ecology", "environment",
)


def classify_domain(text: str):
    """按来源 domain/family 文本猜覆盖域；猜不出返回 None（宁可不入库，也不塞兜底域）。"""
    lowered = (text or "").lower()
    if not lowered:
        return None
    for hint in KNOWLEDGE_HINTS:
        if hint in lowered:
            return "knowledge_reasoning"
    return "decision_mechanics"


# ------------------------------------------------------------------ 小工具

def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def item_id(slug: str, dataset: str, revision: str, config: str, split: str, row,
            variant: str = "") -> str:
    """id = db-<slug>-<8hex>，8hex 由 (dataset, revision, config, split, row, variant) 确定性派生。

    variant 用于同一行产出多条条目的来源（如 moral_stories 一行给正反两条），
    保证 id 全局唯一；source.row 仍然是原始行号，不因 variant 改变。
    """
    material = f"{dataset}|{revision}|{config}|{split}|{row}"
    if variant:
        material = f"{material}|{variant}"
    return f"db-{slug}-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:8]}"


def option_key(label, index: int, used: set) -> str:
    """选项 key：稳定、可读、条目内唯一。"""
    base = re.sub(r"[^a-z0-9]+", "_", str(label).strip().lower()).strip("_")[:24] or f"opt{index + 1}"
    key, suffix = base, 2
    while key in used:
        key = f"{base}_{suffix}"
        suffix += 1
    used.add(key)
    return key


def normalize_probs(values):
    """把非负权重归一到 1；返回 (probs, flag)。不归一就宁可不要概率。"""
    numbers = [float(v) for v in values]
    if any(number < 0 for number in numbers):
        return None, "probs_dropped_negative"
    total = sum(numbers)
    if total <= 0:
        return None, "probs_dropped_zero_mass"
    probs = [number / total for number in numbers]
    flag = "probs_normalized" if abs(total - 1.0) > 1e-6 else None
    return probs, flag


def probs_dict(keys, weights):
    """把权重归一并绑到选项 key 上，得到契约要的 {option_key: prob} 对象。"""
    values, flag = normalize_probs(weights)
    if values is None:
        return None, flag
    return {key: round(value, 6) for key, value in zip(keys, values)}, flag


#: JSON 允许直接出现的、但会被 str.splitlines() 当成换行的字符：
#: 不转义的话，任何按行读 JSONL 的消费者都会把一条记录劈成两半（实测 U+2028 命中过 22 次）。
LINE_BREAK_ESCAPES = (("\u2028", "\\u2028"), ("\u2029", "\\u2029"), ("\u0085", "\\u0085"))


def jsonl_line(item) -> str:
    """序列化成一行 JSONL：转义 U+2028/U+2029/U+0085，保证按行读取不会断裂。"""
    text = json.dumps(item, ensure_ascii=False)
    for raw, escaped in LINE_BREAK_ESCAPES:
        text = text.replace(raw, escaped)
    return text + "\n"


def cap_meta_payloads(meta: dict, limit: int = META_PAYLOAD_BYTES):
    """限制 meta 里原始数据字段的体积：超限的换成带 sha256 与原始长度的摘要，并打旗标。

    state 不在 meta 里，不受影响；这一步只为防止有人把整篇文档塞进 items.jsonl。
    """
    flags = meta.setdefault("quality_flags", [])
    for key, value in list(meta.items()):
        if key == "quality_flags" or value is None:
            continue
        try:
            encoded = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            continue
        raw = encoded.encode("utf-8")
        if len(raw) <= limit:
            continue
        meta[key] = {
            "_truncated": True,
            "_original_bytes": len(raw),
            "_sha256": hashlib.sha256(raw).hexdigest(),
            "_preview": encoded[:2048],
        }
        flags.append(f"meta_truncated:{key}")
    return meta


def json_loads(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def clip_state(text: str, limit: int = MAX_STATE_CHARS):
    """state 过长时截断并报告，便于统计；不静默改变内容。"""
    if len(text) <= limit:
        return text, None
    return text[:limit] + " […]", "state_truncated"


# ------------------------------------------------------------------ 条目组装

def build_item(taxonomy, *, slug, manifest, row, domain, state, mapped=(), flags=(),
               meta_extra=None, question_lang="zh", mappings="all", variant=""):
    """按 README 2.1 组装一个条目；mapped 是 [{key, options?, target, mapping}]。"""
    questions = list(taxonomy.build_questions(domain, lang=question_lang))
    by_key = {question["key"]: question for question in questions}
    targets = {}
    recorded = list(flags)
    for spec in mapped:
        if spec.get("mapping", DIRECT) == DOCUMENTED and mappings == "direct":
            recorded.append(f"mapping_skipped:{spec['key']}")
            continue
        key = spec["key"]
        allowed = taxonomy.DOMAIN_KEYS.get(domain, ())
        if key not in allowed:
            recorded.append(f"mapping_not_in_domain:{key}")
            continue
        if key not in by_key:
            question = taxonomy.build_question(key, lang=question_lang,
                                               options=spec.get("options"),
                                               prompt=spec.get("prompt"))
            questions.append(question)
            by_key[key] = question
        target = spec.get("target")
        if target:
            targets[key] = target
        recorded.append(f"mapping:{spec.get('mapping', DIRECT)}:{key}")
    source = {
        "dataset": manifest["dataset"],
        "revision": manifest["revision"],
        "config": manifest["config"],
        "split": manifest["split"],
        "row": row,
        "license": manifest["license"],
        "url": manifest.get("source_url") or f"https://huggingface.co/datasets/{manifest['dataset']}",
        "slug": slug,
    }
    meta = {
        "converter": CONVERTER_NAME,
        "converter_version": CONVERTER_VERSION,
        "created_at": manifest["_created_at"],
        "quality_flags": recorded,
        "domain_rule": manifest.get("_domain_rule"),
    }
    if meta_extra:
        meta.update(meta_extra)
    cap_meta_payloads(meta)
    item = {
        "id": item_id(slug, manifest["dataset"], manifest["revision"], manifest["config"],
                      manifest["split"], row, variant),
        "domain": domain,
        "lang": manifest.get("lang") or "en",
        "state": state,
        "questions": questions,
        "source": source,
        "meta": meta,
    }
    if targets:
        item["targets"] = targets
    return item, taxonomy.item_errors(item)


# ------------------------------------------------------------------ 各来源转换器

def convert_jev_typed(ctx, unit):
    """SargeDev/jev-distill-corpus-v3 及同形 typed-decision 语料。

    字段：id/kind/options/target/state/question/domain/family/source。
    target 是对齐 options 的概率分布。choice 行映射到 next_step_candidate（候选来自条目本身，
    direct 映射）；noul/score 行的提问与 taxonomy 的键没有语义等价的对应（score 一律 0-5 六档，
    taxonomy 的 score 键是 0-4 五档），因此不硬映射，原始字段进 meta.source_record。
    """
    for row, payload in unit.rows:
        state = str(payload.get("state") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        family = str(payload.get("family") or "")
        domain_field = str(payload.get("domain") or "")
        domain = JEV_FAMILY_DOMAIN.get(family)
        rule = f"family:{family}" if domain else None
        if domain is None:
            domain = classify_domain(domain_field)
            rule = f"domain_hint:{domain_field}"
        if domain is None:
            unit.skip("domain_unmapped")
            continue
        kind = str(payload.get("kind") or "")
        options = list(payload.get("options") or [])
        target = list(payload.get("target") or [])
        mapped, flags = [], []
        if kind == "choice" and 2 <= len(options) <= 16 and len(options) == len(target):
            used = set()
            pairs = [{"key": option_key(label, index, used), "label": str(label)}
                     for index, label in enumerate(options)]
            probs, weight_flag = probs_dict([pair["key"] for pair in pairs], target)
            if weight_flag:
                flags.append(weight_flag)
            best = max(range(len(target)), key=lambda index: float(target[index]))
            mapped.append({"key": "next_step_candidate", "options": pairs, "mapping": DIRECT,
                           "target": {"answer": pairs[best]["key"], "probs": probs}})
        else:
            flags.append(f"source_target_unmapped:{kind}")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain=domain, state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={
                                 "domain_rule": rule,
                                 "source_record": {k: payload.get(k) for k in
                                                   ("id", "kind", "question", "options", "target",
                                                    "domain", "family", "source")},
                             }))


def convert_open_jev(ctx, unit):
    """ZefanCai/Open-Jev：同一 group_id 的相邻行是同一 state 的多个正交问题。

    每行一个源问题（category/bug_severity/... 共 6 个），但源问题的键名不在 taxonomy 里，
    taxonomy 又没有 unknown 通道，因此：条目按 group_id 聚成一个 state，问题用该域 CORE 键，
    源问题清单与答案全部进 meta.source_record；kind=choice 的那一行（候选来自条目）映射到
    next_step_candidate，是 direct 映射。
    """
    groups = {}
    order = []
    for row, payload in unit.rows:
        group = str(payload.get("group_id") or f"row:{row}")
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append((row, payload))
    for group in order:
        members = groups[group]
        row, first = members[0]
        state = native_state_text(first.get("state_json"))
        if not state:
            unit.skip("empty_state")
            continue
        mapped, flags = [], []
        source_questions = []
        for member_row, payload in members:
            source_questions.append({
                "row": member_row,
                "key": str(payload.get("id") or "").rsplit(":", 1)[-1],
                "kind": payload.get("kind"),
                "question": payload.get("question"),
                "options": payload.get("options"),
                "target": payload.get("target"),
            })
        for _, payload in members:
            options = list(payload.get("options") or [])
            target = list(payload.get("target") or [])
            if payload.get("kind") == "choice" and 2 <= len(options) <= 16 \
                    and len(options) == len(target):
                used = set()
                pairs = [{"key": option_key(label, index, used), "label": str(label)}
                         for index, label in enumerate(options)]
                probs, weight_flag = probs_dict([pair["key"] for pair in pairs], target)
                if weight_flag:
                    flags.append(weight_flag)
                best = max(range(len(target)), key=lambda index: float(target[index]))
                mapped.append({"key": "next_step_candidate", "options": pairs, "mapping": DIRECT,
                               "target": {"answer": pairs[best]["key"], "probs": probs}})
                break
        flags.append(f"grouped_rows:{len(members)}")
        flags.append(f"source_questions_unmapped:{len(source_questions)}")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="decision_mechanics", state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={
                                 "domain_rule": "open_jev_controlled_task",
                                 "group_id": group,
                                 "source": first.get("source"),
                                 "original_line_number": first.get("original_line_number"),
                                 "source_questions": source_questions,
                             }))


def convert_jev_decisions_v1(ctx, unit):
    """samatv256/jev-decisions-v1：state + 候选动作 + 被选中的动作（硬标签，不是概率）。"""
    for row, payload in unit.rows:
        state_field = payload.get("state") or {}
        goal = str((state_field or {}).get("user_goal") or "").strip()
        system = str((state_field or {}).get("system") or "").strip()
        state = goal or system
        if not state:
            unit.skip("empty_state")
            continue
        stratum = str(payload.get("source") or "unknown")
        if not unit.allow_stratum(stratum):
            unit.skip(f"stratum_capped:{stratum}")
            continue
        # 两种行形态（实测）：
        #   default          : candidates[{id,name}] + target{candidate_id,action_name}
        #   general-clean-50k: answer_options[{type,label,description}] + target_index
        candidates = list(payload.get("candidates") or [])
        target = payload.get("target") or {}
        if not candidates and payload.get("answer_options"):
            candidates = [{"id": str(index), "name": option.get("label") or option.get("type")
                           or f"option {index}", "description": option.get("description")}
                          for index, option in enumerate(payload["answer_options"])]
            index_of_target = payload.get("target_index")
            target = {"candidate_id": str(index_of_target)} if index_of_target is not None else {}
        mapped, flags = [], []
        if 2 <= len(candidates) <= 16:
            used = set()
            pairs, index_of = [], {}
            for index, candidate in enumerate(candidates):
                label = str(candidate.get("name") or candidate.get("id") or f"candidate {index + 1}")
                key = option_key(label, index, used)
                pairs.append({"key": key, "label": label})
                index_of[str(candidate.get("id"))] = key
            answer = index_of.get(str(target.get("candidate_id")))
            if answer is None:
                wanted = str(target.get("action_name") or "")
                for pair, candidate in zip(pairs, candidates):
                    if str(candidate.get("name")) == wanted:
                        answer = pair["key"]
                        break
            if answer:
                mapped.append({"key": "next_step_candidate", "options": pairs, "mapping": DIRECT,
                               "target": {"answer": answer}})
                flags.append("target_is_hard_label:no_probs")
            else:
                flags.append("source_target_unmapped:answer_not_in_candidates")
        else:
            flags.append(f"source_target_unmapped:candidate_count:{len(candidates)}")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="decision_mechanics", state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={
                                 "domain_rule": "agent_tool_decision",
                                 "stratum": stratum,
                                 "decision_type": payload.get("decision_type"),
                                 "status": payload.get("status"),
                                 "candidate_count": len(candidates),
                             }))


def convert_prosocial_dialog(ctx, unit):
    """allenai/prosocial-dialog：context 是待判断的问题言论，response 是亲社会回应。

    三位标注者对 context 给 {casual, needs caution, needs intervention}，safety_label 是最终判定。
    这三值没有 taxonomy 等义键（harm_severity 是 0-4、response_style 说的是回应风格而非 context 安全），
    因此不映射成 targets，原始标注、比例、理由、规则全部进 meta，供后续批准映射后再用。
    """
    for row, payload in unit.rows:
        state = str(payload.get("context") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        annotations = [str(value) for value in (payload.get("safety_annotations") or [])]
        counts = {}
        for value in annotations:
            counts[value] = counts.get(value, 0) + 1
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        flags = ["source_labels_in_meta_only:context_safety"]
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="social_moral", state=state, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={
                                 "domain_rule": "prosocial_context",
                                 "response": payload.get("response"),
                                 "rots": payload.get("rots"),
                                 "safety_label": payload.get("safety_label"),
                                 "safety_annotations": annotations,
                                 "safety_annotation_counts": counts,
                                 "safety_annotation_reasons": payload.get("safety_annotation_reasons"),
                                 "source": payload.get("source"),
                             }))


def convert_ethics(ctx, unit):
    """hendrycks/ethics：只有 label/input 两列。

    各 config 的 label 语义（哪一侧是 1）在卡面里没有逐 config 说明，本轮不做受监督映射：
    state 入库、label 原样进 meta，等核对完语义再决定是否映射 moral_judgment。
    """
    for row, payload in unit.rows:
        # 各 config 字段名不同（实测）：commonsense=input；deontology/justice/virtue=scenario；
        # utilitarianism=baseline+less_pleasant（两两比较，没有 label）。
        state = str(payload.get("input") or payload.get("scenario") or "").strip()
        if not state and payload.get("baseline"):
            state = (f"Option A: {payload.get('baseline')}\n"
                     f"Option B: {payload.get('less_pleasant')}")
        if not state:
            unit.skip("empty_state")
            continue
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        flags = ["label_semantics_unverified", f"config:{unit.manifest['config']}"]
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain=unit.manifest.get("domain") or "social_moral", state=state,
                             flags=flags, question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={"domain_rule": f"ethics:{unit.manifest['config']}",
                                         "label": payload.get("label")}))


def convert_helpsteer2(ctx, unit):
    """nvidia/HelpSteer2：prompt+response 作 state，五个人类 0-4 打分进 meta。

    taxonomy 目前没有通用的回答质量 score 键（helpfulness/correctness/coherence 都不对应
    现有 score 键的判据），所以不硬映射；五列分数原样保留，等 taxonomy 增键后可直接启用。
    """
    scores = ("helpfulness", "correctness", "coherence", "complexity", "verbosity")
    for row, payload in unit.rows:
        prompt = str(payload.get("prompt") or "").strip()
        response = str(payload.get("response") or "").strip()
        if not prompt:
            unit.skip("empty_state")
            continue
        state = f"{prompt}\n\n[response]\n{response}" if response else prompt
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        flags = ["scores_in_meta_only:" + ",".join(scores)]
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="human_judgment", state=state, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={"domain_rule": "human_rubric_scores",
                                         "human_scores": {name: payload.get(name) for name in scores}}))


def convert_civil_comments(ctx, unit):
    """google/civil_comments：toxicity 等七列是标注者比例（0-1），不是硬标签。

    toxicity 比例直接作为 toxicity_present 的 yes/no 概率（direct 映射，真实多人分布）；
    其余六列同样是人类判断，但 taxonomy 没有对应键，放 meta。
    """
    fractions = ("toxicity", "severe_toxicity", "obscene", "threat", "insult",
                 "identity_attack", "sexual_explicit")
    for row, payload in unit.rows:
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        toxicity = payload.get("toxicity")
        mapped, flags = [], []
        try:
            fraction = float(toxicity)
        except (TypeError, ValueError):
            fraction = None
        if fraction is not None and 0.0 <= fraction <= 1.0:
            probs = {"yes": round(fraction, 6), "no": round(1.0 - fraction, 6)}
            answer = "yes" if fraction >= 0.5 else "no"
            mapped.append({"key": "toxicity_present", "mapping": DIRECT,
                           "target": {"answer": answer, "probs": probs}})
            flags.append("probs_from_annotator_fraction")
        else:
            flags.append("source_target_unmapped:toxicity")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="human_judgment", state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={"domain_rule": "human_toxicity_annotation",
                                         "annotator_fractions": {name: payload.get(name)
                                                                 for name in fractions}}))


def convert_aegis(ctx, unit):
    """nvidia/Aegis 1.0 与 2.0。

    - 2.0：prompt/response + prompt_label/response_label(safe|unsafe) + 标注来源字段。
      卡面写明 response 安全标签可能由 3 个 LLM 集成生成，因此只有来源为 human 才映射
      contains_harm（documented）；其余只作 state。
    - 1.0：text + labels_0..labels_4（多位标注者的类别串）。Safe 记 no、其余记 yes，
      按非空标注算 contains_harm 的投票比例（documented）；原始标签串全部进 meta。
    """
    for row, payload in unit.rows:
        if "response_label" in payload or "prompt_label" in payload:
            prompt = str(payload.get("prompt") or "").strip()
            response = str(payload.get("response") or "").strip()
            if not prompt:
                unit.skip("empty_state")
                continue
            state = f"{prompt}\n\n[response]\n{response}" if response else prompt
            label = payload.get("response_label") or payload.get("prompt_label")
            label_source = payload.get("response_label_source") or payload.get("prompt_label_source")
            mapped, flags = [], []
            if str(label_source or "").lower() == "human" and str(label or "").lower() in ("safe", "unsafe"):
                mapped.append({"key": "contains_harm", "mapping": DOCUMENTED,
                               "target": {"answer": "yes" if str(label).lower() == "unsafe" else "no"}})
                flags.append("label_source:human")
            else:
                flags.append(f"source_target_unmapped:label_source={label_source}")
            state, clip_flag = clip_state(state, ctx.max_state_chars)
            if clip_flag:
                flags.append(clip_flag)
            unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                                 domain="risk_harm", state=state, mapped=mapped, flags=flags,
                                 question_lang=ctx.question_lang, mappings=ctx.mappings,
                                 meta_extra={
                                     "domain_rule": "aegis2_content_safety",
                                     "prompt_label": payload.get("prompt_label"),
                                     "response_label": payload.get("response_label"),
                                     "prompt_label_source": payload.get("prompt_label_source"),
                                     "response_label_source": payload.get("response_label_source"),
                                     "violated_categories": payload.get("violated_categories"),
                                 }))
            continue
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        labels = [str(payload.get(f"labels_{index}")) for index in range(5)
                  if payload.get(f"labels_{index}") not in (None, "")]
        mapped, flags = [], []
        if labels:
            unsafe = sum(1 for label in labels if label.lower() != "safe")
            safe = len(labels) - unsafe
            probs, weight_flag = probs_dict(["yes", "no"], [unsafe, safe])
            if weight_flag:
                flags.append(weight_flag)
            mapped.append({"key": "contains_harm", "mapping": DOCUMENTED,
                           "target": {"answer": "yes" if unsafe * 2 >= len(labels) else "no",
                                      "probs": probs}})
            flags.append("probs_from_annotator_votes")
        else:
            flags.append("source_target_unmapped:labels")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="risk_harm", state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={
                                 "domain_rule": "aegis1_content_safety",
                                 "num_annotations": payload.get("num_annotations"),
                                 "annotator_labels": labels,
                                 "text_type": payload.get("text_type"),
                             }))


def convert_moral_stories(ctx, unit):
    """demelin/moral_stories（full）：每行一条情境 + 正反两个行动及其后果。

    卡面写明 label 0=immoral/divergent、1=moral/normative。每行生成两条条目：
    - moral 条：state = situation + intention + moral_action，moral_judgment 取 acceptable/wrong
    - immoral 条：同理取另一侧
    expected_consequence（benefit/harm）由 moral_consequence / immoral_consequence 字段配对派生，
    标为 documented 映射。
    """
    for row, payload in unit.rows:
        situation = str(payload.get("situation") or "").strip()
        intention = str(payload.get("intention") or "").strip()
        label = payload.get("label")
        if not situation or label is None:
            unit.skip("empty_state")
            continue
        for side, action_field, consequence_field in (("moral", "moral_action", "moral_consequence"),
                                                      ("immoral", "immoral_action", "immoral_consequence")):
            action = str(payload.get(action_field) or "").strip()
            if not action:
                unit.skip(f"empty_action:{side}")
                continue
            acceptable = (side == "moral") == (str(label) == "1")
            state = f"{situation}\nIntent: {intention}\nAction: {action}".strip()
            state, clip_flag = clip_state(state, ctx.max_state_chars)
            flags = [f"side:{side}"]
            if clip_flag:
                flags.append(clip_flag)
            mapped = [
                {"key": "moral_judgment", "mapping": DIRECT,
                 "target": {"answer": "acceptable" if acceptable else "wrong"}},
                {"key": "expected_consequence", "mapping": DOCUMENTED,
                 "target": {"answer": "benefit" if side == "moral" else "harm"}},
            ]
            unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                                 domain="social_moral", state=state, mapped=mapped, flags=flags,
                                 question_lang=ctx.question_lang, mappings=ctx.mappings,
                                 variant=side,
                                 meta_extra={
                                     "domain_rule": f"moral_stories:{side}",
                                     "story_id": payload.get("ID"),
                                     "norm": payload.get("norm"),
                                     "intention": intention,
                                     "label": label,
                                     "consequence_text": payload.get(consequence_field),
                                     "paired_action": payload.get(
                                         "immoral_action" if side == "moral" else "moral_action"),
                                 }))


def convert_systemone_lite(ctx, unit):
    """dwidlee/systemone-lite-general：state 是 JSON 字符串，criteria_keys/criteria_values 是候选。

    instructions 是源问题、label_alias 是正确候选的 key（硬标签，没有分布）。
    choice 型候选映射到 next_step_candidate（direct）；源问题与 rubric 进 meta。
    """
    for row, payload in unit.rows:
        state_json = json_loads(payload.get("state"))
        if isinstance(state_json, (dict, list)):
            state = json.dumps(state_json, ensure_ascii=False, indent=1)
        else:
            state = str(payload.get("state") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        keys = [str(value) for value in (payload.get("criteria_keys") or [])]
        values = [str(value) for value in (payload.get("criteria_values") or [])]
        label_alias = str(payload.get("label_alias") or "")
        task = str(payload.get("task") or "")
        mapped, flags = [], []
        if 2 <= len(values) <= 16 and len(keys) == len(values):
            used = set()
            pairs = [{"key": option_key(value, index, used), "label": value}
                     for index, value in enumerate(values)]
            answer = None
            if label_alias in keys:
                answer = pairs[keys.index(label_alias)]["key"]
            if answer:
                mapped.append({"key": "next_step_candidate", "options": pairs, "mapping": DIRECT,
                               "target": {"answer": answer}})
                flags.append("target_is_hard_label:no_probs")
            else:
                flags.append("source_target_unmapped:label_alias")
        else:
            flags.append("source_target_unmapped:criteria")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        meta = json_loads(payload.get("meta")) or {}
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="decision_mechanics", state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={
                                 "domain_rule": f"systemone_gym:{task.split('.')[0]}",
                                 "source_task": task,
                                 "source_instructions": payload.get("instructions"),
                                 "source_criteria": {"keys": keys, "values": values},
                                 "label_alias": label_alias,
                                 "label_key": payload.get("label_key"),
                                 "gym": meta.get("gym") if isinstance(meta, dict) else None,
                             }))


def convert_system_one_270m(ctx, unit):
    """kaivoss/system-one-270m-data：同一 state_id 的多行是同一情境的不同问题。

    prompt 里 <state> 是情境、Question: 之后是问题、Options: 之后是 A./B./C. 候选；
    letters + target 是与候选对齐的概率分布，label 是正确的选项 key。
    choice 型映射到 next_step_candidate（direct，带分布）；noul/score 型不硬塞档位，
    原始问题、标签与分布进 meta。同一 state_id 聚成一条多问题条目。
    """
    groups, order = {}, []
    for row, payload in unit.rows:
        state_id = str(payload.get("state_id") or f"row:{row}")
        if state_id not in groups:
            groups[state_id] = []
            order.append(state_id)
        groups[state_id].append((row, payload))
    for state_id in order:
        members = groups[state_id]
        row, first = members[0]
        prompt = str(first.get("prompt") or "")
        match = re.search(r"<state>\s*(.*?)\s*</state>", prompt, re.S)
        state = match.group(1).strip() if match else prompt.strip()
        if not state:
            unit.skip("empty_state")
            continue
        questions = []
        for member_row, payload in members:
            member_prompt = str(payload.get("prompt") or "")
            instruction = member_prompt.split("Question:", 1)[-1].split("Options:", 1)[0].strip()
            questions.append({"row": member_row, "qtype": payload.get("qtype"),
                              "instructions": instruction, "letters": payload.get("letters"),
                              "label": payload.get("label"), "target": payload.get("target"),
                              "domain": payload.get("domain"), "entropy": payload.get("entropy"),
                              "ambiguity": payload.get("ambiguity")})
        mapped, flags = [], []
        for _, payload in members:
            if str(payload.get("qtype")) != "choice":
                continue
            letters = [str(value) for value in (payload.get("letters") or [])]
            target = list(payload.get("target") or [])
            labels = parse_lettered_options(str(payload.get("prompt") or ""), letters)
            if len(labels) != len(letters) or len(letters) < 2 or len(letters) > 16 \
                    or len(target) != len(letters):
                continue
            used = set()
            pairs = [{"key": option_key(label, index, used), "label": label}
                     for index, label in enumerate(labels)]
            probs, weight_flag = probs_dict([pair["key"] for pair in pairs], target)
            if weight_flag:
                flags.append(weight_flag)
            best = max(range(len(target)), key=lambda index: float(target[index]))
            mapped.append({"key": "next_step_candidate", "options": pairs, "mapping": DIRECT,
                           "target": {"answer": pairs[best]["key"], "probs": probs}})
            break
        if not mapped:
            flags.append("source_target_unmapped:qtype_or_options")
        flags.append(f"grouped_rows:{len(members)}")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="decision_mechanics", state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={"domain_rule": f"system_one_270m:{first.get('domain')}",
                                         "state_id": state_id,
                                         "source_questions": questions}))


def parse_lettered_options(prompt: str, letters):
    """从 prompt 的 Options: 段落里解析 A./B./C. 候选文本；解析不出就返回空列表。"""
    section = prompt.split("Options:", 1)[-1]
    section = section.split("Answer", 1)[0]
    found = {}
    for line in section.splitlines():
        line = line.strip()
        match = re.match(r"^([A-Z])[.)]\s*(.+?)\s*$", line)
        if match:
            found[match.group(1)] = match.group(2)
    if not letters or any(letter not in found for letter in letters):
        return []
    return [found[letter] for letter in letters]


def convert_procedural(ctx, unit):
    """tasksource/procedural-typed-decisions：一行一个 state，questions/answers 是 JSON 字符串。

    每个 state 带多个类型化问题与真实概率分布，但问题键名不在 taxonomy 里，
    因此按该域 CORE 键提问，choice 型的问题映射到 next_step_candidate（direct），
    其余（含 10 档的 score）原样进 meta，不压档位。
    """
    for row, payload in unit.rows:
        state = str(payload.get("state") or "").strip()
        parsed_state = json_loads(state)
        if isinstance(parsed_state, (dict, list)):
            state = json.dumps(parsed_state, ensure_ascii=False, indent=1)
        if not state:
            unit.skip("empty_state")
            continue
        questions = json_loads(payload.get("questions")) or {}
        answers = json_loads(payload.get("answers")) or {}
        if not isinstance(questions, dict) or not isinstance(answers, dict):
            unit.skip("unparsable_questions")
            continue
        source_questions = []
        mapped, flags = [], []
        for key, spec in questions.items():
            answer = answers.get(key) or {}
            source_questions.append({
                "key": key, "type": spec.get("type") if isinstance(spec, dict) else None,
                "instructions": spec.get("instructions") if isinstance(spec, dict) else None,
                "criteria": spec.get("criteria") if isinstance(spec, dict) else None,
                "answer": answer.get("choice") or answer.get("noul") or answer.get("score"),
                "probabilities": answer.get("probabilities"),
            })
            if not mapped and isinstance(spec, dict) and spec.get("type") == "choice" \
                    and isinstance(spec.get("criteria"), dict) \
                    and isinstance(answer.get("probabilities"), dict):
                criteria = [str(value) for value in spec["criteria"].keys()]
                probabilities = answer["probabilities"]
                if 2 <= len(criteria) <= 16 and set(criteria) == set(probabilities):
                    used = set()
                    pairs = [{"key": option_key(label, index, used), "label": label}
                             for index, label in enumerate(criteria)]
                    probs, weight_flag = probs_dict(
                        [pair["key"] for pair in pairs],
                        [probabilities[value] for value in criteria])
                    if weight_flag:
                        flags.append(weight_flag)
                    probs = probs or {}
                    best = pairs[criteria.index(str(answer.get("choice")))] \
                        if str(answer.get("choice")) in criteria else pairs[0]
                    mapped.append({"key": "next_step_candidate", "options": pairs,
                                   "mapping": DIRECT,
                                   "target": {"answer": best["key"], "probs": probs}})
        if not mapped:
            flags.append(f"source_questions_unmapped:{len(source_questions)}")
        state, clip_flag = clip_state(state, ctx.max_state_chars)
        if clip_flag:
            flags.append(clip_flag)
        unit.emit(build_item(ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
                             domain="decision_mechanics", state=state, mapped=mapped, flags=flags,
                             question_lang=ctx.question_lang, mappings=ctx.mappings,
                             meta_extra={"domain_rule": f"procedural:{payload.get('task')}",
                                         "source_task": payload.get("task"),
                                         "source_id": payload.get("id"),
                                         "source_questions": source_questions}))


# ------------------------------------------------------------------ 原生四元组模式（task-16）
#
# 立论：目标模型只做"选一个"。System-1 来源本来就自带 (state, question, options, target)，
# 直接用它们的原生问题，不再套本地 taxonomy 的中文模板；taxonomy 只在来源没有原生问题时才用。
#
# 契约扩展：questions[] 增加 origin（"source"）与 source_key（原生问题名，与 key 相同）。
# 原生键名一律不动：open-jev 用 category / bug_severity，procedural 用 starts_before_noon 等。

NATIVE_SLUGS: tuple[str, ...] = (
    "jev-distill-v3", "open-jev", "jev-decisions-general-50k", "jev-decisions-strata",
    "systemone-lite-general", "system-one-270m", "procedural-typed-decisions",
)
NATIVE_ID_PATTERN = re.compile(r"^db-[A-Za-z0-9._-]+-[0-9a-f]{8}$")
NATIVE_KINDS = ("noul", "choice", "score")
STATE_NOTE_FIELD = "state 取原生 state.user_goal；完整原生 state（system/history/environment）" \
                   "可按 source 的 dataset+revision+config+split+row 从 D:\\pol2-raw 的原始行复原"


def native_option_pairs(labels):
    """候选文本 → [{key,label}]，顺序与原文一致；key 由 label 派生，保证条目内唯一。"""
    used = set()
    return [{"key": option_key(label, index, used), "label": str(label)}
            for index, label in enumerate(labels)]


def level_pairs(count):
    """score 的原生档位：key 用序号（与原生 target 数组下标一一对应），档位文本原样保留。"""
    return [{"key": str(index), "label": str(index)} for index in range(count)]


def scale_of(labels):
    return {"min": 0, "max": len(labels) - 1, "labels": [str(label) for label in labels]}


def prob_map(pairs, weights):
    """把原生权重（数组）绑到候选 key 上；不归一就不要概率。"""
    values, flag = normalize_probs(weights)
    if values is None:
        return None, flag
    return {pair["key"]: round(value, 6) for pair, value in zip(pairs, values)}, flag


def point_mass(pairs, index):
    """硬标签 → 单点分布（选中 1.0、其余 0.0），保证与 options 等长可复原。"""
    return {pair["key"]: (1.0 if position == index else 0.0)
            for position, pair in enumerate(pairs)}


def argmax_key(pairs, weights):
    best = max(range(len(weights)), key=lambda index: float(weights[index]))
    return pairs[best]["key"]


def native_state_text(raw):
    """把原生 state_json 还原成文本：字符串原样用；对象/数组按其 JSON 序列化（不是 Python repr）。"""
    value = json_loads(raw)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return ""


def native_question(key, kind, prompt, *, options=None, scale=None):
    question = {"key": str(key), "kind": kind, "origin": "source", "source_key": str(key),
                "prompt": prompt}
    if kind == "score":
        question["scale"] = scale
    else:
        question["options"] = options
    return question


def native_item_errors(item) -> list:
    """原生模式的契约校验（不能直接用 taxonomy.item_errors：原生键名与档位都不在 taxonomy 词表里）。"""
    if not isinstance(item, dict):
        return ["条目不是 JSON 对象"]
    errors = []
    for field in ("id", "domain", "lang", "state", "questions", "source", "meta"):
        if field not in item:
            errors.append(f"缺字段 {field}")
    if not isinstance(item.get("id"), str) or not NATIVE_ID_PATTERN.match(item.get("id") or ""):
        errors.append(f"id 不符合 db-<slug>-<8hex>：{item.get('id')!r}")
    if not isinstance(item.get("state"), str) or not item["state"].strip():
        errors.append("state 必须是非空字符串")
    for field in ("dataset", "revision", "config", "split", "row", "license", "url"):
        if not isinstance(item.get("source"), dict) or field not in item["source"]:
            errors.append(f"source 缺字段 {field}")
    questions = item.get("questions")
    keys, option_keys = [], {}
    if not isinstance(questions, list) or not questions:
        errors.append("questions 必须是非空数组")
        questions = []
    for index, question in enumerate(questions):
        prefix = f"questions[{index}]"
        if not isinstance(question, dict):
            errors.append(f"{prefix}: 不是对象")
            continue
        key = question.get("key")
        if not isinstance(key, str) or not key.strip():
            errors.append(f"{prefix}: 缺 key")
            continue
        if key in keys:
            errors.append(f"{prefix}: 问题键重复 {key}")
        keys.append(key)
        if question.get("origin") != "source":
            errors.append(f"{prefix}: origin 必须是 source")
        if question.get("source_key") != key:
            errors.append(f"{prefix}: source_key 必须等于原生问题名 {key!r}")
        if question.get("kind") not in NATIVE_KINDS:
            errors.append(f"{prefix}: kind 必须是 {NATIVE_KINDS}")
        if not isinstance(question.get("prompt"), str) or not question["prompt"].strip():
            errors.append(f"{prefix}: prompt 必须是非空字符串")
        if question.get("kind") == "score":
            scale = question.get("scale")
            if not isinstance(scale, dict) or not isinstance(scale.get("labels"), list) \
                    or not scale["labels"]:
                errors.append(f"{prefix}: score 缺 scale.labels")
            elif scale.get("max") != len(scale["labels"]) - 1 or scale.get("min") != 0:
                errors.append(f"{prefix}: scale 的 min/max 必须覆盖 labels")
            else:
                option_keys[key] = [str(index) for index in range(len(scale["labels"]))]
        elif question.get("kind") in ("noul", "choice"):
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                errors.append(f"{prefix}: 至少 2 个 options")
                continue
            seen = []
            for option in options:
                if not isinstance(option, dict) or not str(option.get("key") or "").strip() \
                        or not str(option.get("label") or "").strip():
                    errors.append(f"{prefix}: option 必须有非空 key 与 label")
                    continue
                if option["key"] in seen:
                    errors.append(f"{prefix}: option key 重复 {option['key']}")
                seen.append(option["key"])
            option_keys[key] = seen
    targets = item.get("targets") or {}
    if not isinstance(targets, dict):
        errors.append("targets 必须是对象")
        targets = {}
    for key, value in targets.items():
        if key not in keys:
            errors.append(f"targets[{key}]: 没有对应的问题")
            continue
        if not isinstance(value, dict):
            errors.append(f"targets[{key}]: 必须是对象")
            continue
        allowed = option_keys.get(key, [])
        answer = value.get("answer")
        if answer is not None and allowed and str(answer) not in allowed:
            errors.append(f"targets[{key}]: answer {answer!r} 不在候选里")
        probs = value.get("probs")
        if probs is None:
            if answer is None:
                errors.append(f"targets[{key}]: answer 与 probs 至少有一个")
            continue
        if not isinstance(probs, dict) or not probs:
            errors.append(f"targets[{key}]: probs 必须是非空对象")
            continue
        if allowed and len(probs) != len(allowed):
            errors.append(f"targets[{key}]: probs {len(probs)} 项与 options {len(allowed)} 项不等长")
        total = 0.0
        for raw_key, prob in probs.items():
            if allowed and str(raw_key) not in allowed:
                errors.append(f"targets[{key}]: probs 键 {raw_key!r} 不在候选内")
            if isinstance(prob, bool) or not isinstance(prob, (int, float)) or not 0 <= float(prob) <= 1:
                errors.append(f"targets[{key}]: probs[{raw_key!r}] 必须是 [0,1] 数字")
                continue
            total += float(prob)
        if abs(total - 1.0) > 1e-3:
            errors.append(f"targets[{key}]: probs 之和 {total:.6f} 未归一")
    return errors


def build_native_item(taxonomy, *, slug, manifest, row, domain, domain_rule, state, questions,
                      targets, flags=(), meta_extra=None, variant="", key_source="native"):
    """按原生四元组组装条目；questions 里每个问题都自带 origin/source_key。"""
    source = {
        "dataset": manifest["dataset"], "revision": manifest["revision"],
        "config": manifest["config"], "split": manifest["split"], "row": row,
        "license": manifest["license"],
        "url": manifest.get("source_url") or f"https://huggingface.co/datasets/{manifest['dataset']}",
        "slug": slug,
    }
    meta = {
        "converter": CONVERTER_NAME, "converter_version": CONVERTER_VERSION,
        "created_at": manifest["_created_at"], "native": True,
        "key_source": key_source, "question_origin": "source",
        "quality_flags": list(flags), "domain_rule": domain_rule,
    }
    if meta_extra:
        meta.update(meta_extra)
    item = {
        "id": item_id(slug, manifest["dataset"], manifest["revision"], manifest["config"],
                      manifest["split"], row, variant),
        "domain": domain, "lang": manifest.get("lang") or "en", "state": state,
        "questions": questions, "source": source, "meta": meta,
    }
    if targets:
        item["targets"] = targets
    return item, native_item_errors(item)


def native_jev_typed(ctx, unit):
    """jev-distill-v3：原生 kind/options/target/state/question；score 保留 0-5 六档不压。"""
    for row, payload in unit.rows:
        state = str(payload.get("state") or "")
        question_text = str(payload.get("question") or "")
        if not state.strip() or not question_text.strip():
            unit.skip("empty_state_or_question")
            continue
        family = str(payload.get("family") or "")
        domain = JEV_FAMILY_DOMAIN.get(family) or classify_domain(str(payload.get("domain") or ""))
        if domain is None:
            unit.skip("domain_unmapped")
            continue
        kind = str(payload.get("kind") or "")
        labels = [str(value) for value in (payload.get("options") or [])]
        weights = list(payload.get("target") or [])
        if kind not in NATIVE_KINDS or len(labels) < 2 or len(labels) != len(weights):
            unit.skip("options_target_misaligned")
            continue
        flags = []
        if kind == "score":
            pairs = level_pairs(len(labels))
            question = native_question(question_text, "score", question_text, scale=scale_of(labels))
        else:
            pairs = native_option_pairs(labels)
            question = native_question(question_text, kind, question_text, options=pairs)
        probs, weight_flag = prob_map(pairs, weights)
        if weight_flag:
            flags.append(weight_flag)
        target = {"answer": argmax_key(pairs, weights)}
        if probs:
            target["probs"] = probs
        if max(float(value) for value in weights) - min(float(value) for value in weights) < 1e-9:
            flags.append("uniform_target")
        unit.emit(build_native_item(
            ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row, domain=domain,
            domain_rule=(f"family:{family}" if family in JEV_FAMILY_DOMAIN
                         else f"domain:{payload.get('domain')}"),
            state=state, questions=[question], targets={question_text: target}, flags=flags,
            key_source="native-text",
            meta_extra={"native_id": payload.get("id"), "native_kind": kind,
                        "native_family": family, "native_domain": payload.get("domain"),
                        "native_source": payload.get("source"),
                        "native_option_count": len(labels)}))


def native_open_jev(ctx, unit):
    """open-jev：按 group_id 聚合成一个 state 挂多个正交问题，键名用原生问题名。"""
    groups, order = {}, []
    for row, payload in unit.rows:
        group = str(payload.get("group_id") or f"row:{row}")
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append((row, payload))
    for group in order:
        members = groups[group]
        row, first = members[0]
        state = native_state_text(first.get("state_json"))
        if not state:
            unit.skip("empty_state")
            continue
        questions, targets, flags = [], {}, []
        for member_row, payload in members:
            key = str(payload.get("id") or "").rsplit(":", 1)[-1]
            kind = str(payload.get("kind") or "")
            labels = [str(value) for value in (payload.get("options") or [])]
            weights = list(payload.get("target") or [])
            if not key or kind not in NATIVE_KINDS or len(labels) < 2 or len(labels) != len(weights):
                unit.skip("member_skipped")
                continue
            if key in targets:
                unit.skip("duplicate_question_key")
                continue
            prompt = str(payload.get("question") or key)
            if kind == "score":
                pairs = level_pairs(len(labels))
                questions.append(native_question(key, "score", prompt, scale=scale_of(labels)))
            else:
                pairs = native_option_pairs(labels)
                questions.append(native_question(key, kind, prompt, options=pairs))
            probs, weight_flag = prob_map(pairs, weights)
            if weight_flag:
                flags.append(weight_flag)
            target = {"answer": argmax_key(pairs, weights)}
            if probs:
                target["probs"] = probs
            targets[key] = target
        if not questions:
            unit.skip("no_questions")
            continue
        flags.append(f"grouped_questions:{len(questions)}")
        unit.emit(build_native_item(
            ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
            domain="decision_mechanics", domain_rule=f"source:{first.get('source')}",
            state=state, questions=questions, targets=targets, flags=flags,
            key_source="native-name",
            meta_extra={"group_id": group, "native_source": first.get("source"),
                        "native_line_number": first.get("original_line_number")}))


def native_jev_decisions(ctx, unit):
    """jev-decisions：硬标签（target_index / candidate_id）→ answer + 单点 probs。"""
    for row, payload in unit.rows:
        state_field = payload.get("state") or {}
        state = str((state_field or {}).get("user_goal") or "")
        if not state.strip():
            unit.skip("empty_state")
            continue
        flags, meta_extra = [], {}
        if payload.get("answer_options"):
            key = str(payload.get("question") or "").strip() or "choice"
            labels = [str(option.get("label") or option.get("type") or "")
                      for option in payload["answer_options"]]
            index = payload.get("target_index")
            kind = str(payload.get("question_type") or "choice")
            key_source = "native-text"
            meta_extra["native_config_shape"] = "answer_options+target_index"
        elif payload.get("candidates"):
            key = str(payload.get("decision_type") or "tool_choice")
            labels = [str(candidate.get("name") or candidate.get("id") or "")
                      for candidate in payload["candidates"]]
            target_field = payload.get("target") or {}
            wanted = str(target_field.get("candidate_id") or "")
            index = None
            for position, candidate in enumerate(payload["candidates"]):
                if str(candidate.get("id")) == wanted:
                    index = position
                    break
            kind = "choice"
            key_source = "native-name"
            flags.append("prompt_falls_back_to_native_decision_type")
            meta_extra["native_config_shape"] = "candidates+target.candidate_id"
        else:
            unit.skip("no_candidates")
            continue
        if not labels or len(labels) < 2 or index is None or not 0 <= int(index) < len(labels):
            unit.skip("target_index_out_of_range")
            continue
        pairs = native_option_pairs(labels)
        question = native_question(key, kind, key, options=pairs)
        target = {"answer": pairs[int(index)]["key"], "probs": point_mass(pairs, int(index))}
        flags.append("hard_label_to_point_mass")
        if len(labels) > 16:
            flags.append(f"option_count_over_16:{len(labels)}")
        unit.emit(build_native_item(
            ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
            domain="decision_mechanics",
            domain_rule=(f"source:{payload.get('source')}"
                         + (f"|decision_type:{payload.get('decision_type')}"
                            if payload.get("decision_type") else "")),
            state=state, questions=[question], targets={key: target}, flags=flags,
            key_source=key_source,
            meta_extra={"native_source": payload.get("source"),
                        "native_state_note": STATE_NOTE_FIELD,
                        "native_option_count": len(labels), **meta_extra}))


def native_systemone_lite(ctx, unit):
    """systemone-lite-general：键名用原生 task，问题用原生 instructions，硬标签取 criteria_values。"""
    for row, payload in unit.rows:
        state = str(payload.get("state") or "")
        task = str(payload.get("task") or "")
        instructions = str(payload.get("instructions") or "")
        if not state.strip() or not instructions.strip():
            unit.skip("empty_state_or_instruction")
            continue
        labels = [str(value) for value in (payload.get("criteria_values") or [])]
        keys = [str(value) for value in (payload.get("criteria_keys") or [])]
        label_alias = str(payload.get("label_alias") or "")
        if len(labels) < 2 or len(keys) != len(labels) or label_alias not in keys:
            unit.skip("criteria_misaligned")
            continue
        pairs = native_option_pairs(labels)
        index = keys.index(label_alias)
        key = task or instructions
        question = native_question(key, "choice", instructions, options=pairs)
        target = {"answer": pairs[index]["key"], "probs": point_mass(pairs, index)}
        unit.emit(build_native_item(
            ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
            domain="decision_mechanics", domain_rule=f"task:{task}",
            state=state, questions=[question], targets={key: target},
            flags=["hard_label_to_point_mass"], key_source="native-name",
            meta_extra={"native_task": task, "native_label_alias": label_alias,
                        "native_label_key": payload.get("label_key"),
                        "native_criteria_keys": keys}))


def native_system_one_270m(ctx, unit):
    """system-one-270m：state 段与 Question 段都在原生 prompt 模板里，逐字抽出来用。"""
    groups, order = {}, []
    for row, payload in unit.rows:
        state_id = str(payload.get("state_id") or f"row:{row}")
        if state_id not in groups:
            groups[state_id] = []
            order.append(state_id)
        groups[state_id].append((row, payload))
    for state_id in order:
        members = groups[state_id]
        row, first = members[0]
        prompt = str(first.get("prompt") or "")
        match = re.search(r"<state>\s*(.*?)\s*</state>", prompt, re.S)
        state = match.group(1) if match else ""
        if not state.strip():
            unit.skip("empty_state")
            continue
        questions, targets, flags = [], {}, []
        for member_row, payload in members:
            member_prompt = str(payload.get("prompt") or "")
            question_text = member_prompt.split("Question:", 1)[-1].split("Options:", 1)[0].strip()
            kind = str(payload.get("qtype") or "")
            letters = [str(value) for value in (payload.get("letters") or [])]
            weights = list(payload.get("target") or [])
            if not question_text or kind not in NATIVE_KINDS or len(letters) < 2 \
                    or len(letters) != len(weights):
                unit.skip("member_skipped")
                continue
            if question_text in targets:
                unit.skip("duplicate_question_key")
                continue
            labels = parse_lettered_options(member_prompt, letters)
            if len(labels) != len(letters):
                unit.skip("options_unparsable")
                continue
            if kind == "score":
                pairs = level_pairs(len(labels))
                question = native_question(question_text, "score", question_text,
                                           scale=scale_of(labels))
            else:
                pairs = native_option_pairs(labels)
                question = native_question(question_text, kind, question_text, options=pairs)
            probs, weight_flag = prob_map(pairs, weights)
            if weight_flag:
                flags.append(weight_flag)
            target = {"answer": argmax_key(pairs, weights)}
            if probs:
                target["probs"] = probs
            targets[question_text] = target
            questions.append(question)
        if not questions:
            unit.skip("no_questions")
            continue
        flags.append(f"grouped_questions:{len(questions)}")
        unit.emit(build_native_item(
            ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
            domain=classify_domain(str(first.get("domain") or "")) or "decision_mechanics",
            domain_rule=f"native_domain:{first.get('domain')}",
            state=state, questions=questions, targets=targets, flags=flags,
            key_source="native-text",
            meta_extra={"state_id": state_id, "native_domain": first.get("domain")}))


def native_procedural(ctx, unit):
    """procedural-typed-decisions：questions/answers 两个原生 map，逐问转成原生键。"""
    for row, payload in unit.rows:
        state = str(payload.get("state") or "")
        if not state.strip():
            unit.skip("empty_state")
            continue
        questions_map = json_loads(payload.get("questions")) or {}
        answers_map = json_loads(payload.get("answers")) or {}
        if not isinstance(questions_map, dict) or not isinstance(answers_map, dict) \
                or not questions_map:
            unit.skip("unparsable_questions")
            continue
        questions, targets, flags = [], {}, []
        for key, spec in questions_map.items():
            if not isinstance(spec, dict):
                unit.skip("bad_question_spec")
                continue
            kind = str(spec.get("type") or "")
            answer = answers_map.get(key) or {}
            prompt = str(spec.get("instructions") or key)
            criteria = spec.get("criteria")
            levels = []
            if kind == "score":
                levels = [str(value) for value in criteria] if isinstance(criteria, list) else []
                if len(levels) < 2:
                    unit.skip("score_without_levels")
                    continue
                pairs = level_pairs(len(levels))
                question = native_question(key, "score", prompt, scale=scale_of(levels))
                target = {}
                weights = answer.get("probabilities")
                if isinstance(weights, dict):
                    probs, weight_flag = prob_map(pairs, [weights.get(level, 0.0) for level in levels])
                    if weight_flag:
                        flags.append(weight_flag)
                    if probs:
                        target["probs"] = probs
                score = answer.get("score")
                if isinstance(score, (int, float)) and not isinstance(score, bool):
                    target["answer"] = str(int(score)) if float(score).is_integer() else str(score)
                    if not float(score).is_integer():
                        flags.append("non_integer_score_kept_as_text")
            elif kind in ("choice", "noul"):
                if kind == "choice":
                    levels = list(criteria.keys()) if isinstance(criteria, dict) else []
                    if len(levels) < 2:
                        unit.skip("choice_without_criteria")
                        continue
                    pairs = native_option_pairs(levels)
                    question = native_question(key, "choice", prompt, options=pairs)
                else:
                    pairs = [{"key": "yes", "label": "yes"}, {"key": "no", "label": "no"}]
                    question = native_question(key, "noul", prompt, options=pairs)
                    flags.append("noul_options_canonical")
                target = {}
                weights = answer.get("probabilities")
                if isinstance(weights, dict) and kind == "choice":
                    probs, weight_flag = prob_map(pairs, [weights.get(level, 0.0) for level in levels])
                    if weight_flag:
                        flags.append(weight_flag)
                    if probs:
                        target["probs"] = probs
                elif kind == "noul":
                    value = answer.get("noul")
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        probs, weight_flag = prob_map(pairs, [float(value), 1.0 - float(value)])
                        if weight_flag:
                            flags.append(weight_flag)
                        if probs:
                            target["probs"] = probs
                choice = answer.get("choice")
                if isinstance(choice, str) and choice and kind == "choice":
                    for pair, label in zip(pairs, levels):
                        if label == choice:
                            target["answer"] = pair["key"]
                            break
                if "answer" not in target and target.get("probs"):
                    target["answer"] = max(target["probs"], key=lambda name: target["probs"][name])
            else:
                unit.skip("unknown_question_type")
                continue
            questions.append(question)
            if target:
                targets[key] = target
        if not questions:
            unit.skip("no_questions")
            continue
        flags.append(f"native_questions:{len(questions)}")
        unit.emit(build_native_item(
            ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row,
            domain="decision_mechanics", domain_rule=f"task:{payload.get('task')}",
            state=state, questions=questions, targets=targets, flags=flags,
            key_source="native-name",
            meta_extra={"native_task": payload.get("task"), "native_level": payload.get("level"),
                        "native_id": payload.get("id")}))


NATIVE_CONVERTERS = {
    "jev_typed": native_jev_typed,
    "open_jev": native_open_jev,
    "jev_decisions_v1": native_jev_decisions,
    "systemone_lite": native_systemone_lite,
    "system_one_270m": native_system_one_270m,
    "procedural": native_procedural,
}


# ---------------------------------------------------------------- taxonomy 模板模式（对照 / 待归档）
#
# 这条线是"我们替数据出题"：用本地 taxonomy.py 的中文模板问题去套别人的 state。已被
# --native（直接用来源原生 state/question/options/target）取代，不是训练首选。
# 仍然保留的原因：items.jsonl（37,124 条模板版）作为对照产物存在，需要能复现；而且
# coverage.py / ask.py / luna_clean.py / luna_gen.py / convert_zh.py 仍然 import taxonomy.py。
# 整套删掉的前置条件见 ARCHIVE.md 的「清理提案」一节。
CONVERTERS = {
    "jev_typed": convert_jev_typed,
    "open_jev": convert_open_jev,
    "jev_decisions_v1": convert_jev_decisions_v1,
    "prosocial_dialog": convert_prosocial_dialog,
    "ethics": convert_ethics,
    "helpsteer2": convert_helpsteer2,
    "civil_comments": convert_civil_comments,
    "aegis": convert_aegis,
    "moral_stories": convert_moral_stories,
    "systemone_lite": convert_systemone_lite,
    "system_one_270m": convert_system_one_270m,
    "procedural": convert_procedural,
}


# ------------------------------------------------------------------ 驱动

class Unit:
    """一个来源目录（slug）的转换状态与统计。"""

    def __init__(self, slug, manifest, rows, ctx, limit=None, stratum_cap=0.35):
        self.slug = slug
        self.manifest = manifest
        self.rows = rows
        self.ctx = ctx
        self.limit = limit
        self.rows_read = 0
        self.emitted = []
        self.items = 0
        self.skipped = {}
        self.by_domain = {}
        self.by_domain_targets = {}
        self.target_classes = {DIRECT: 0, DOCUMENTED: 0, "hard_label": 0, "distribution": 0}
        self.with_targets = 0
        self.invalid = 0
        self.duplicate_states = 0
        self._seen_states = set()
        self._stratum_counts = {}
        self._stratum_cap = max(1, int(stratum_cap * max(1, limit or len(rows))))

    def skip(self, reason):
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def allow_stratum(self, stratum):
        count = self._stratum_counts.get(stratum, 0)
        if count >= self._stratum_cap:
            return False
        self._stratum_counts[stratum] = count + 1
        return True

    def emit(self, built):
        item, errors = built
        if errors:
            self.invalid += 1
            self.skip("invalid_item:" + errors[0][:60])
            return
        state_hash = hashlib.sha256(item["state"].encode("utf-8")).hexdigest()
        if state_hash in self._seen_states:
            self.duplicate_states += 1
            self.skip("duplicate_state")
            return
        self._seen_states.add(state_hash)
        self.emitted.append(item)
        self.items += 1
        self.by_domain[item["domain"]] = self.by_domain.get(item["domain"], 0) + 1
        if item.get("targets"):
            self.with_targets += 1
            self.by_domain_targets[item["domain"]] =                 self.by_domain_targets.get(item["domain"], 0) + 1
            kinds = set()
            for flag in item["meta"]["quality_flags"]:
                for name in (DIRECT, DOCUMENTED):
                    if flag.startswith(f"mapping:{name}:"):
                        kinds.add(name)
                if flag.startswith("hard_label_to_point_mass"):
                    kinds.add("hard_label")
            if not kinds:
                kinds.add("distribution")      # 原生模式：直接来自来源的概率分布
            for name in kinds:
                self.target_classes[name] = self.target_classes.get(name, 0) + 1
        return item

    def report(self):
        rate = (self.with_targets / self.items) if self.items else 0.0
        direct = self.target_classes.get(DIRECT, 0)
        return {
            "slug": self.slug, "dataset": self.manifest["dataset"],
            "config": self.manifest["config"], "split": self.manifest["split"],
            "rows_read": self.rows_read, "items": self.items,
            "with_targets": self.with_targets,
            "native_target_rate": round(rate, 4),
            "native_target_rate_direct_only": round((direct / self.items) if self.items else 0.0, 4),
            "pending_external_answers": self.items - self.with_targets,
            "target_classes": dict(self.target_classes),   # 固定四个键，两个模式口径一致
            "duplicate_states": self.duplicate_states,
            "invalid": self.invalid, "by_domain": self.by_domain,
            "by_domain_with_targets": self.by_domain_targets, "skipped": self.skipped,
        }


class Context:
    def __init__(self, taxonomy, *, mappings="all", question_lang="zh", stratum_cap=0.35,
                 created_at=None, log=print, max_state_chars=MAX_STATE_CHARS):
        self.taxonomy = taxonomy
        self.mappings = mappings
        self.question_lang = question_lang
        self.stratum_cap = stratum_cap
        self.max_state_chars = max_state_chars
        self.created_at = created_at or utc_now()
        self.log = log


def source_config(sources_path=None):
    """slug → sources.json 里的来源配置（转换器名、stratum_cap 等）。

    sources.json 是配置的唯一来源；manifest 里的 converter 只是抓取时的快照。
    """
    path = Path(sources_path or HERE / "sources.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {source["slug"]: source for source in payload.get("sources", [])}


def convert_unit(context, slug, manifest, rows, *, converter=None, limit=None, stratum_cap=0.35,
                 converters=None):
    """转换一个来源目录；返回 (items, report)。main 与离线测试走同一条路径。"""
    table = CONVERTERS if converters is None else converters
    name = converter or manifest.get("converter")
    function = table.get(str(name))
    if function is None:
        raise KeyError(f"未知转换器 {name!r}")
    prepared = dict(manifest)
    prepared["_created_at"] = context.created_at
    unit = Unit(slug, prepared, rows, context, limit=limit, stratum_cap=stratum_cap)
    unit.rows_read = len(rows)
    function(context, unit)
    return unit.emitted, unit.report()


def read_rows(path: Path, limit=None):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append((record.get("row_idx"), record.get("row") or {}))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def load_units(raw_root: Path, slugs=None):
    units = []
    for directory in sorted(path for path in raw_root.iterdir() if path.is_dir()):
        if directory.name.startswith("_"):      # _pilot/_sample 等临时目录不参与正式构建
            continue
        manifest_path = directory / "manifest.json"
        rows_path = directory / "rows.jsonl"
        if not manifest_path.is_file() or not rows_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not manifest.get("complete"):
            units.append((directory.name, manifest, None, "未完成抓取（manifest.complete=false）"))
            continue
        if manifest.get("revision_stable") is False:
            units.append((directory.name, manifest, None, "抓取期间 revision 变动，产物不可信"))
            continue
        if slugs and directory.name not in slugs:
            continue
        units.append((directory.name, manifest, rows_path, None))
    return units


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="把 general 原始行转换成契约条目")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--out", type=Path, default=None,
                        help=f"输出路径（默认 {DEFAULT_OUT.name}；--native 时默认 {DEFAULT_NATIVE_OUT.name}）")
    parser.add_argument("--native", action="store_true",
                        help="原生四元组模式：直接用来源的 question/options/target，taxonomy 退回可选层")
    parser.add_argument("--report", type=Path, default=None, help="报告路径（默认与 --out 同目录）")
    parser.add_argument("--source", action="append", default=[], help="只转换指定 slug（可重复）")
    parser.add_argument("--limit", type=int, default=None, help="每个来源最多读取的行数")
    parser.add_argument("--sources", type=Path, default=HERE / "sources.json",
                        help="来源清单（用于按 slug 解析转换器）")
    parser.add_argument("--taxonomy", type=Path, default=None, help="taxonomy.py 路径")
    parser.add_argument("--mappings", choices=("all", "direct"), default="all",
                        help="direct 只保留有直接证据的映射，去掉 documented 映射")
    parser.add_argument("--question-lang", choices=("zh", "en"), default="zh")
    parser.add_argument("--stratum-cap", type=float, default=0.35,
                        help="单一 stratum（如 jev-decisions-v1 的 source 值）在该来源内的占比上限")
    parser.add_argument("--created-at", default=None, help="固定 meta.created_at，便于可复现构建")
    parser.add_argument("--max-state-chars", type=int, default=None,
                        help=f"state 字符上限（taxonomy 模式默认 {MAX_STATE_CHARS}；"
                             f"原生模式默认 0 = 不截断，state 用原文）")
    parser.add_argument("--stdout", action="store_true", help="把条目写到标准输出，不落盘")
    args = parser.parse_args(argv)

    converters = NATIVE_CONVERTERS if args.native else CONVERTERS
    max_state_chars = args.max_state_chars
    if max_state_chars is None:
        max_state_chars = 0 if args.native else MAX_STATE_CHARS
    # 原生模式不依赖 taxonomy.py（已解耦：它只是可选标注层），只有模板模式才加载
    taxonomy = None if args.native else load_taxonomy(args.taxonomy)
    context = Context(taxonomy, mappings=args.mappings, question_lang=args.question_lang,
                      stratum_cap=args.stratum_cap, created_at=args.created_at,
                      max_state_chars=max_state_chars or MAX_STATE_CHARS)
    context.native = bool(args.native)
    by_slug = source_config(args.sources)
    units = load_units(args.raw_root, set(args.source) or None)
    if not units:
        print(f"错误：{args.raw_root} 下没有可转换的来源目录", file=sys.stderr)
        return 1

    reports, written, total, total_targets = [], 0, 0, 0
    skipped_units, out_of_scope = [], []
    out_path = None
    if not args.stdout:
        out_path = args.out or (DEFAULT_NATIVE_OUT if args.native else DEFAULT_OUT)
    handle = None
    if not args.stdout:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        handle = out_path.open("w", encoding="utf-8")
    try:
        for slug, manifest, rows_path, problem in units:
            if problem:
                skipped_units.append({"slug": slug, "reason": problem})
                print(f"跳过 {slug}：{problem}", file=sys.stderr)
                continue
            if args.native and slug not in NATIVE_SLUGS:
                out_of_scope.append({"slug": slug,
                                     "reason": "原生模式只重建 SOURCES.md 推荐的 7 个单元"})
                continue
            configured = by_slug.get(slug) or {}
            name = configured.get("converter") or manifest.get("converter")
            if str(name) not in converters:
                skipped_units.append({"slug": slug, "reason": f"未知转换器 {name!r}"})
                print(f"跳过 {slug}：未知转换器 {name!r}", file=sys.stderr)
                continue
            rows = read_rows(rows_path, args.limit)
            items, report = convert_unit(context, slug, manifest, rows, converter=name,
                                         limit=args.limit, converters=converters,
                                         stratum_cap=float(configured.get("stratum_cap",
                                                                          args.stratum_cap)))
            for item in items:
                if handle is not None:
                    handle.write(jsonl_line(item))
                else:
                    print(jsonl_line(item), end="")
                written += 1
            reports.append(report)
            total += report["items"]
            total_targets += report["with_targets"]
            context.log(f"[{slug}] 读 {report['rows_read']} 行 → {report['items']} 条"
                        f"（带 targets {report['with_targets']}，去重 {report['duplicate_states']}，"
                        f"无效 {report['invalid']}）")
    finally:
        if handle is not None:
            handle.close()

    by_domain, by_domain_targets, target_classes = {}, {}, {DIRECT: 0, DOCUMENTED: 0}
    for report in reports:
        for domain, count in report["by_domain"].items():
            by_domain[domain] = by_domain.get(domain, 0) + count
        for domain, count in report["by_domain_with_targets"].items():
            by_domain_targets[domain] = by_domain_targets.get(domain, 0) + count
        for name, count in report["target_classes"].items():
            target_classes[name] = target_classes.get(name, 0) + count
    domain_rates = {domain: {"items": count,
                             "with_targets": by_domain_targets.get(domain, 0),
                             "native_target_rate": round(by_domain_targets.get(domain, 0) / count, 4)}
                    for domain, count in sorted(by_domain.items())}
    summary = {
        "converter": CONVERTER_NAME, "converter_version": CONVERTER_VERSION,
        "mode": "native" if args.native else "taxonomy",
        "native_slugs": list(NATIVE_SLUGS) if args.native else None,
        "created_at": context.created_at, "raw_root": str(args.raw_root),
        "items_path": str(out_path) if out_path else None,
        "mappings_used": args.mappings,
        "mappings_default": "all",
        "mappings_default_note": "core 问题 + direct 映射 + documented 映射；"
                                  "--mappings direct 只保留 core 问题与 direct 映射",
        "mapping_classes": {"direct_targets": target_classes[DIRECT],
                            "documented_targets": target_classes[DOCUMENTED]},
        "question_lang": args.question_lang,
        "stratum_cap": args.stratum_cap, "limit": args.limit,
        "items": total, "items_with_targets": total_targets,
        "native_target_rate": round((total_targets / total) if total else 0.0, 4),
        "pending_external_answers": total - total_targets,
        "by_domain": by_domain, "by_domain_detail": domain_rates,
        "units": reports, "skipped_units": skipped_units, "out_of_scope": out_of_scope,
    }
    if not args.stdout:
        default_report_name = "items.native.report.json" if args.native else "convert-report.json"
        report_path = args.report or out_path.with_name(default_report_name)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({"mode": summary["mode"], "items": total, "with_targets": total_targets,
                      "native_target_rate": summary["native_target_rate"],
                      "pending_external_answers": summary["pending_external_answers"],
                      "mappings": args.mappings, "by_domain": by_domain,
                      "units": len(reports), "skipped_units": len(skipped_units),
                      "out_of_scope": len(out_of_scope)},
                     ensure_ascii=False))
    invalid = sum(report["invalid"] for report in reports)
    return 1 if invalid or skipped_units else 0


if __name__ == "__main__":
    sys.exit(main())
