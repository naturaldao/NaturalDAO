"""PoL2 专用数据包 pack-1022 的冻结集验证、切分物化与 HF 导出。

pack-1022.tar.gz（来自协作者项目 pol2-label-team-v1）内的 freeze-8705-v1 是
POL2-accepted-8705-v1：8,705 个 accepted unit / 75 个场景族 / 4,888 个 case，
状态 FROZEN_READ_ONLY_NOT_TRAINING_APPROVED（未批准训练、非专家金标）。

本脚本只读数据包，按 pack manifest 里已冻结的四区提案物化切分，不重新切分、
不引入新盐、不改标签：

    freeze 区        → 项目区（provisional，待 owner 签字）
    train            → train
    validation       → public_test
    calibration      → validation
    blind_test       → private_holdout

blind_test 的 unit_id / family_id / 内容绝不写入 tracked 路径：写盘前断言，失败即中止。

    uv run --no-project --offline python datasets/pol2/prepare_freeze.py build
    uv run --no-project --offline python datasets/pol2/prepare_freeze.py verify
    uv run --no-project --offline python datasets/pol2/prepare_freeze.py verify --json

build 幂等且确定性：同一 pack 两次运行写出逐字节相同的文件。verify 只读，重算
unit 数 / schema / 族级切分一致性 / answer_a-b 一致 / 每 mapping 标签词表 / id 唯一 /
question type 统计，并把切分、导出与 tracked SPLIT-MANIFEST.json 的 sha256 全部复算比对。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POL2_DIR = REPO_ROOT / "datasets" / "pol2"
DEFAULT_PACK = POL2_DIR / "pack-1022.tar.gz"
DEFAULT_DATA = POL2_DIR / "data"
DEFAULT_TRACKED = POL2_DIR / "freeze-8705-v1"

FREEZE_ID = "POL2-accepted-8705-v1"
FREEZE_STATUS = "FROZEN_READ_ONLY_NOT_TRAINING_APPROVED"
PACK_MEMBER_ROOT = "root/projects/pol2-label-team-v1/root/"
FREEZE_MEMBER_DIR = PACK_MEMBER_ROOT + "freeze-8705-v1/"

# 选择解压的成员：freeze 本体 + 复核所需的少量元数据；其余 6 万条目留在原始 tar 内。
EXTRACT_MEMBERS = (
    "freeze-8705-v1/accepted-units.jsonl",
    "freeze-8705-v1/manifest.json",
    "handbook.md",
    "team.json",
    "gates.json",
    "label-queue-gates.json",
    "question-policy.json",
    "question_policy.py",
    "choice_protocols.py",
    "score_protocols.py",
    "inputs/theory.md",
    "inputs/theory-index.md",
    "inputs/manifest.json",
    "inputs/selection.json",
)
# 体积大且已由 freeze manifest 记录哈希、不参与切分：只登记不物化。
EXCLUDED_MEMBERS = ("inputs/cases.json",)

REGIONS = ("train", "validation", "calibration", "blind_test")
PROJECT_REGION = {
    "train": "train",
    "validation": "public_test",
    "calibration": "validation",
    "blind_test": "private_holdout",
}
PUBLIC_REGIONS = ("train", "validation", "calibration")
BLIND_REGION = "blind_test"

HF_EXPORT_DIR = "pol2-freeze-8705-v1"
DATA_CARD_PATH = "FREEZE-8705-V1.md"
README_PATH = "README.md"

EXPECTED_UNIT_KEYS = frozenset({
    "unit_id", "case_id", "world", "family_id", "mapping_id", "source_run",
    "source_batch", "status", "split_proposal", "label", "answer_a", "answer_b",
    "audit_status", "state", "question", "question_sha", "source_sha",
})
ANSWER_REQUIRED_KEYS = ("unit_id", "status", "label", "evidence", "theory_refs", "reason")
ANSWER_OPTIONAL_KEYS = ("checks", "check_evidence", "original_label", "label_adapter",
                        "check_evidence_adapter", "rubric_assessment", "unresolved_kind",
                        "turns", "missing_conditions")
QUESTION_TYPES = ("choice", "score")
MAX_ERRORS_PER_CHECK = 12


# --------------------------------------------------------------------------- 基础工具


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> str:
    """question_sha 的口径：sort_keys + ensure_ascii=False 的 JSON 文本。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def relative_posix(path: Path, anchor: Path) -> str:
    try:
        return path.resolve().relative_to(anchor.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def anchor_label(data_dir: Path) -> str:
    base = data_dir.resolve().parent
    try:
        return base.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return base.name


def iso_utc(timestamp) -> str:
    return datetime.datetime.fromtimestamp(float(timestamp), datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


class Unit:
    """一个 accepted unit：原始行（保真写出）+ 解析后的对象（校验/统计）。"""

    __slots__ = ("raw", "data")

    def __init__(self, raw: str, data: dict):
        self.raw = raw
        self.data = data

    @property
    def unit_id(self) -> str:
        return self.data["unit_id"]

    @property
    def region(self) -> str:
        return self.data["split_proposal"]


def load_units_from_bytes(payload: bytes) -> list[Unit]:
    text = payload.decode("utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    units = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"accepted-units.jsonl:{number}: invalid JSON: {error}") from error
        if not isinstance(row, dict):
            raise ValueError(f"accepted-units.jsonl:{number}: each line must be an object")
        units.append(Unit(line, row))
    return units


def load_units(path: Path) -> list[Unit]:
    return load_units_from_bytes(path.read_bytes())


def unit_sort_key(unit: Unit) -> str:
    return unit.unit_id


def line_count(payload: bytes) -> int:
    return len([line for line in payload.split(b"\n") if line.strip()])


# --------------------------------------------------------------------------- 校验与统计


def _add_error(failures: dict[str, list[str]], check: str, message: str) -> None:
    bucket = failures[check]
    if len(bucket) < MAX_ERRORS_PER_CHECK:
        bucket.append(message)
    elif len(bucket) == MAX_ERRORS_PER_CHECK:
        bucket.append("... more errors suppressed")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_question(unit: Unit, failures: dict[str, list[str]]) -> None:
    question = unit.data.get("question")
    if not isinstance(question, dict) or set(question) != {"criteria", "instructions", "type"}:
        _add_error(failures, "question_schema", f"{unit.unit_id}: malformed question object")
        return
    instructions = question["instructions"]
    if not isinstance(instructions, str) or not instructions.strip():
        _add_error(failures, "question_schema", f"{unit.unit_id}: empty instructions")
    qtype = question["type"]
    label = unit.data.get("label")
    if qtype == "choice":
        criteria = question["criteria"]
        if not isinstance(criteria, dict) or len(criteria) < 2:
            _add_error(failures, "question_schema", f"{unit.unit_id}: choice criteria not a dict")
            return
        for key, text in criteria.items():
            if not isinstance(key, str) or not key:
                _add_error(failures, "question_schema", f"{unit.unit_id}: bad option key")
            if not isinstance(text, str) or not text.strip():
                _add_error(failures, "question_schema", f"{unit.unit_id}: empty criteria text")
        if not isinstance(label, str) or label not in criteria:
            _add_error(failures, "question_schema",
                       f"{unit.unit_id}: label {label!r} not in criteria keys")
    elif qtype == "score":
        criteria = question["criteria"]
        if not isinstance(criteria, list) or len(criteria) != 5:
            _add_error(failures, "question_schema",
                       f"{unit.unit_id}: score criteria must be a 5-item list")
        elif not all(isinstance(text, str) and text.strip() for text in criteria):
            _add_error(failures, "question_schema", f"{unit.unit_id}: empty score band")
        if not _is_int(label) or not 0 <= label <= 4:
            _add_error(failures, "question_schema",
                       f"{unit.unit_id}: score label {label!r} not an int in 0..4")
    else:
        _add_error(failures, "question_schema", f"{unit.unit_id}: unknown type {qtype!r}")


def _validate_answer(unit: Unit, field: str, failures: dict[str, list[str]]) -> None:
    answer = unit.data.get(field)
    if not isinstance(answer, dict):
        _add_error(failures, "answer_agreement", f"{unit.unit_id}: {field} is not an object")
        return
    missing = [key for key in ANSWER_REQUIRED_KEYS if key not in answer]
    if missing:
        _add_error(failures, "answer_agreement", f"{unit.unit_id}: {field} missing {missing}")
        return
    if answer["status"] != "ANSWER":
        _add_error(failures, "answer_agreement",
                   f"{unit.unit_id}: {field}.status={answer['status']!r}")
    if answer["label"] != unit.data.get("label"):
        _add_error(failures, "answer_agreement",
                   f"{unit.unit_id}: {field}.label {answer['label']!r} != unit label")
    evidence = answer["evidence"]
    if not isinstance(evidence, list) or not evidence:
        _add_error(failures, "answer_agreement", f"{unit.unit_id}: {field}.evidence empty")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) \
                    or not isinstance(item.get("quote"), str) or not item["quote"].strip():
                _add_error(failures, "answer_agreement",
                           f"{unit.unit_id}: {field}.evidence item malformed")
                break
    refs = answer["theory_refs"]
    if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs):
        _add_error(failures, "answer_agreement", f"{unit.unit_id}: {field}.theory_refs bad")
    if not isinstance(answer["reason"], str) or not answer["reason"].strip():
        _add_error(failures, "answer_agreement", f"{unit.unit_id}: {field}.reason empty")


def _validate_state(unit: Unit, failures: dict[str, list[str]]) -> None:
    state = unit.data.get("state")
    required = {"fixed_facts", "judgment_actor", "observer_cutoff", "action_stage", "world"}
    if not isinstance(state, dict) or not required <= set(state):
        _add_error(failures, "unit_schema", f"{unit.unit_id}: state structure missing")
        return
    for key in ("judgment_actor", "observer_cutoff", "action_stage"):
        if not isinstance(state[key], str) or not state[key].strip():
            _add_error(failures, "unit_schema", f"{unit.unit_id}: state.{key} empty")
    facts = state["fixed_facts"]
    if not isinstance(facts, list) or not facts:
        _add_error(failures, "unit_schema", f"{unit.unit_id}: fixed_facts must be non-empty list")
    elif not all(isinstance(item, dict) and isinstance(item.get("content"), str)
                 for item in facts):
        _add_error(failures, "unit_schema", f"{unit.unit_id}: fixed_facts item malformed")
    world = state["world"]
    if not isinstance(world, dict) or not isinstance(world.get("variable_facts"), list):
        _add_error(failures, "unit_schema", f"{unit.unit_id}: world.variable_facts bad")
    elif not isinstance(world.get("candidate_action"), str) or not world["candidate_action"].strip():
        _add_error(failures, "unit_schema", f"{unit.unit_id}: candidate_action empty")


def analyze_units(units: list[Unit], freeze_manifest: dict,
                  accepted_units_sha256: str | None = None) -> tuple[dict, dict[str, list[str]]]:
    """一次性完成 schema 校验与分布统计；返回 (stats, failures)。"""
    checks = ("unit_count", "unit_schema", "question_schema", "family_split_consistency",
              "split_counts", "answer_agreement", "id_uniqueness", "question_sha",
              "mapping_label_vocabulary", "audit_coverage", "freeze_manifest")
    failures: dict[str, list[str]] = {name: [] for name in checks}

    region_units = {region: 0 for region in REGIONS}
    region_families: dict[str, set] = {region: set() for region in REGIONS}
    region_cases: dict[str, set] = {region: set() for region in REGIONS}
    region_choice = {region: 0 for region in REGIONS}
    region_score = {region: 0 for region in REGIONS}
    region_audit = {region: 0 for region in REGIONS}
    family_region: dict[str, str] = {}
    case_region: dict[str, str] = {}
    case_worlds: dict[str, set] = {}
    case_source: dict[str, str] = {}
    mapping_templates: dict[str, set] = {}
    mapping_labels: dict[str, set] = {}
    label_values: dict[str, int] = {}
    label_by_type: dict[str, dict[str, int]] = {qtype: {} for qtype in QUESTION_TYPES}
    option_keysets: dict[tuple, int] = {}
    question_types = {qtype: 0 for qtype in QUESTION_TYPES}
    template_counts: dict[str, int] = {}
    audit_status = {"pass": 0, "not_sampled": 0}
    answer_status: dict[str, int] = {}
    a_equals_b = 0
    a_equals_unit = 0
    pair_cases = 0
    single_world_cases = 0
    unit_ids: set[str] = set()
    case_world_pairs: set[tuple] = set()
    extra_answer_fields: dict[str, dict[str, int]] = {"answer_a": {}, "answer_b": {}}
    theory_refs: set[str] = set()

    for index, unit in enumerate(units, 1):
        data = unit.data
        unit_id = data.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            _add_error(failures, "unit_schema", f"unit #{index}: bad unit_id")
            continue
        if unit_id in unit_ids:
            _add_error(failures, "id_uniqueness", f"duplicate unit_id {unit_id}")
        unit_ids.add(unit_id)

        if set(data) != EXPECTED_UNIT_KEYS:
            _add_error(failures, "unit_schema",
                       f"{unit_id}: unit keys differ from the 17-key schema "
                       f"(+{sorted(set(data) - EXPECTED_UNIT_KEYS)} "
                       f"-{sorted(EXPECTED_UNIT_KEYS - set(data))})")
            continue

        case_id, world, region = data["case_id"], data["world"], data["split_proposal"]
        family_id, mapping_id, label = data["family_id"], data["mapping_id"], data["label"]
        qtype = data["question"]["type"]

        if not isinstance(case_id, str) or not case_id:
            _add_error(failures, "unit_schema", f"{unit_id}: bad case_id")
            continue
        if world not in ("a", "b"):
            _add_error(failures, "unit_schema", f"{unit_id}: world {world!r}")
        if unit_id != f"{case_id}:{world}":
            _add_error(failures, "id_uniqueness", f"{unit_id}: unit_id != case_id:world")
        if (case_id, world) in case_world_pairs:
            _add_error(failures, "id_uniqueness", f"{unit_id}: duplicate (case_id, world)")
        case_world_pairs.add((case_id, world))
        if not isinstance(family_id, str) or not family_id:
            _add_error(failures, "unit_schema", f"{unit_id}: bad family_id")
        if not isinstance(mapping_id, str) or not mapping_id:
            _add_error(failures, "unit_schema", f"{unit_id}: bad mapping_id")
        if not isinstance(data["source_run"], str) or not data["source_run"]:
            _add_error(failures, "unit_schema", f"{unit_id}: bad source_run")
        if data["source_batch"] != data["source_run"]:
            _add_error(failures, "unit_schema", f"{unit_id}: source_batch != source_run")
        if data["status"] != "ACCEPTED":
            _add_error(failures, "unit_schema", f"{unit_id}: status {data['status']!r}")
        if region not in REGIONS:
            _add_error(failures, "split_counts", f"{unit_id}: region {region!r}")
            continue
        if data["audit_status"] not in audit_status:
            _add_error(failures, "audit_coverage",
                       f"{unit_id}: audit_status {data['audit_status']!r}")

        previous = family_region.setdefault(family_id, region)
        if previous != region:
            _add_error(failures, "family_split_consistency",
                       f"family {family_id} spans {previous} and {region}")
        previous = case_region.setdefault(case_id, region)
        if previous != region:
            _add_error(failures, "family_split_consistency",
                       f"case {case_id} spans {previous} and {region}")
        case_worlds.setdefault(case_id, set()).add(world)
        source_sha = data["source_sha"]
        if isinstance(source_sha, str):
            previous_source = case_source.setdefault(case_id, source_sha)
            if previous_source != source_sha:
                _add_error(failures, "id_uniqueness", f"case {case_id} has two source_sha")
        else:
            _add_error(failures, "unit_schema", f"{unit_id}: bad source_sha")

        region_units[region] += 1
        region_families[region].add(family_id)
        region_cases[region].add(case_id)
        if qtype in QUESTION_TYPES:
            question_types[qtype] += 1
            if qtype == "choice":
                region_choice[region] += 1
            else:
                region_score[region] += 1
        if data["audit_status"] == "pass":
            audit_status["pass"] += 1
            region_audit[region] += 1
        elif data["audit_status"] == "not_sampled":
            audit_status["not_sampled"] += 1

        _validate_question(unit, failures)
        _validate_answer(unit, "answer_a", failures)
        _validate_answer(unit, "answer_b", failures)
        _validate_state(unit, failures)

        answer_a, answer_b = data["answer_a"], data["answer_b"]
        if isinstance(answer_a, dict) and isinstance(answer_b, dict):
            if answer_a.get("label") == answer_b.get("label"):
                a_equals_b += 1
            if answer_a.get("label") == label:
                a_equals_unit += 1
            status_key = answer_a.get("status")
            answer_status[status_key] = answer_status.get(status_key, 0) + 1
            for field in ("answer_a", "answer_b"):
                payload = data[field]
                if not isinstance(payload, dict):
                    continue
                extra = extra_answer_fields[field]
                for key in payload:
                    if key in ANSWER_OPTIONAL_KEYS:
                        extra[key] = extra.get(key, 0) + 1
            for ref in answer_a.get("theory_refs") or []:
                if isinstance(ref, str):
                    theory_refs.add(ref)

        label_key = str(label)
        label_values[label_key] = label_values.get(label_key, 0) + 1
        if qtype in QUESTION_TYPES:
            bucket = label_by_type[qtype]
            bucket[label_key] = bucket.get(label_key, 0) + 1
        if isinstance(data["question"], dict) and isinstance(mapping_id, str):
            mapping_templates.setdefault(mapping_id, set()).add(data["question_sha"])
            mapping_labels.setdefault(mapping_id, set()).add(label_key)
            criteria = data["question"].get("criteria")
            if qtype == "choice" and isinstance(criteria, dict):
                keyset = tuple(sorted(criteria))
                option_keysets[keyset] = option_keysets.get(keyset, 0) + 1
        if isinstance(data["question_sha"], str):
            template_counts[data["question_sha"]] = \
                template_counts.get(data["question_sha"], 0) + 1

    for case_id, worlds in case_worlds.items():
        if worlds == {"a", "b"}:
            pair_cases += 1
        elif len(worlds) == 1:
            single_world_cases += 1
        else:
            _add_error(failures, "id_uniqueness", f"case {case_id}: worlds {sorted(worlds)}")

    for unit in units:
        question = unit.data.get("question")
        expected = unit.data.get("question_sha")
        if isinstance(question, dict) and isinstance(expected, str):
            if expected != sha256_bytes(canonical_json(question).encode("utf-8")):
                _add_error(failures, "question_sha",
                           f"{unit.unit_id}: question_sha != sha256(canonical question)")

    for mapping_id, template_set in sorted(mapping_templates.items()):
        if len(template_set) > 1:
            _add_error(failures, "mapping_label_vocabulary",
                       f"mapping {mapping_id}: {len(template_set)} question templates")
    for mapping_id, labels in sorted(mapping_labels.items()):
        if not labels:
            _add_error(failures, "mapping_label_vocabulary", f"mapping {mapping_id}: no labels")

    if freeze_manifest.get("freeze_id") != FREEZE_ID:
        _add_error(failures, "freeze_manifest",
                   f"freeze_id {freeze_manifest.get('freeze_id')!r} != {FREEZE_ID!r}")
    if freeze_manifest.get("status") != FREEZE_STATUS:
        _add_error(failures, "freeze_manifest", f"status {freeze_manifest.get('status')!r}")
    if freeze_manifest.get("training_approved") is not False:
        _add_error(failures, "freeze_manifest", "training_approved is not false")
    if freeze_manifest.get("expert_gold") is not False:
        _add_error(failures, "freeze_manifest", "expert_gold is not false")
    if freeze_manifest.get("accepted_units") != len(units):
        _add_error(failures, "unit_count",
                   f"manifest.accepted_units={freeze_manifest.get('accepted_units')} "
                   f"!= units={len(units)}")
    if freeze_manifest.get("family_count") != len(family_region):
        _add_error(failures, "unit_count",
                   f"manifest.family_count={freeze_manifest.get('family_count')} "
                   f"!= families={len(family_region)}")
    proposal = freeze_manifest.get("split_proposal_counts") or {}
    for region in REGIONS:
        if proposal.get(region) is None:
            _add_error(failures, "split_counts", f"manifest missing proposal count for {region}")
        elif proposal[region] != region_units[region]:
            _add_error(failures, "split_counts",
                       f"{region}: units {region_units[region]} != proposal {proposal[region]}")
    if sum(region_units.values()) != len(units):
        _add_error(failures, "split_counts", "region unit totals do not add up")
    if accepted_units_sha256 is not None:
        frozen = (freeze_manifest.get("frozen_files") or {}).get("accepted-units.jsonl")
        if frozen != accepted_units_sha256:
            _add_error(failures, "freeze_manifest",
                       "frozen_files['accepted-units.jsonl'] != accepted file sha256")

    stats = {
        "units": len(units),
        "families": len(family_region),
        "cases": len(case_region),
        "question_types": dict(question_types),
        "label_values": dict(sorted(label_values.items())),
        "label_values_by_question_type": {qtype: dict(sorted(bucket.items()))
                                          for qtype, bucket in label_by_type.items()},
        "choice_option_keysets": [
            {"keys": list(keys), "units": count}
            for keys, count in sorted(option_keysets.items())
        ],
        "question_templates": len(template_counts),
        "templates": dict(sorted(template_counts.items())),
        "mappings": len(mapping_labels),
        "mapping_label_vocabulary": {mapping_id: sorted(labels)
                                     for mapping_id, labels in sorted(mapping_labels.items())},
        "ab_pair_cases": pair_cases,
        "single_world_cases": single_world_cases,
        "answer_status": dict(sorted(answer_status.items())),
        "answer_label_agreement": {"a_equals_b": a_equals_b, "a_equals_unit": a_equals_unit},
        "audit": {"pass": audit_status["pass"], "not_sampled": audit_status["not_sampled"],
                  "coverage": round(audit_status["pass"] / len(units), 6) if units else 0.0},
        "theory_refs": len(theory_refs),
        "extra_answer_fields": {field: dict(sorted(values.items()))
                                for field, values in extra_answer_fields.items()},
        "regions": {
            region: {
                "units": region_units[region],
                "families": len(region_families[region]),
                "cases": len(region_cases[region]),
                "choice": region_choice[region],
                "score": region_score[region],
                "audit_pass": region_audit[region],
            } for region in REGIONS
        },
    }
    return stats, failures


def raise_failures(failures: dict[str, list[str]]) -> None:
    messages = [f"{check}: {message}" for check, errors in failures.items() for message in errors]
    if messages:
        raise ValueError("data invariants failed:" + "\n  " + "\n  ".join(messages))


# --------------------------------------------------------------------------- 计划与渲染


def region_bytes(units: list[Unit], region: str) -> bytes:
    selected = sorted((unit for unit in units if unit.region == region), key=unit_sort_key)
    return "".join(unit.raw + "\n" for unit in selected).encode("utf-8")


def limited_counts(units: list[Unit]) -> dict:
    families = {unit.data["family_id"] for unit in units}
    cases = {unit.data["case_id"] for unit in units}
    worlds: dict[str, set] = {}
    for unit in units:
        worlds.setdefault(unit.data["case_id"], set()).add(unit.data["world"])
    labels: dict[str, int] = {}
    for unit in units:
        key = str(unit.data["label"])
        labels[key] = labels.get(key, 0) + 1
    return {
        "units": len(units),
        "families": len(families),
        "cases": len(cases),
        "choice": sum(1 for unit in units if unit.data["question"]["type"] == "choice"),
        "score": sum(1 for unit in units if unit.data["question"]["type"] == "score"),
        "audit_pass": sum(1 for unit in units if unit.data["audit_status"] == "pass"),
        "mappings": len({unit.data["mapping_id"] for unit in units}),
        "question_templates": len({unit.data["question_sha"] for unit in units}),
        "ab_pair_cases": sum(1 for value in worlds.values() if value == {"a", "b"}),
        "label_values": dict(sorted(labels.items())),
    }


def output_spaces(units: list[Unit]) -> list[dict]:
    choice_keysets: dict[tuple, int] = {}
    score_units = 0
    for unit in units:
        data = unit.data
        if data["question"]["type"] == "choice":
            keys = tuple(sorted(data["question"]["criteria"]))
            choice_keysets[keys] = choice_keysets.get(keys, 0) + 1
        else:
            score_units += 1
    spaces = [{"question_type": "choice", "option_keys": list(keys), "units": count}
              for keys, count in sorted(choice_keysets.items())]
    if score_units:
        spaces.append({"question_type": "score", "levels": [0, 1, 2, 3, 4],
                       "units": score_units})
    return spaces


def render_public_readme(public_units: list[Unit], files: dict, source: dict) -> str:
    counts = limited_counts(public_units)
    lines = [
        f"# {FREEZE_ID}（公开分区）",
        "",
        "PoL2 专用冻结集的公开导出，只含 train / public_test / validation 三个项目区。",
        "",
        "**状态：NOT_TRAINING_APPROVED（未批准训练）· expert_gold=false（非专家金标）· "
        "尚未上传 Hugging Face。**",
        "在数据所有者书面批准训练之前，不得用于训练、蒸馏或教师生成。",
        "",
        "## 文件",
        "",
        "JSONL，UTF-8，一行一个 unit，按 unit_id 升序。",
        "",
        "| 文件 | 冻结区 | 项目区 | units | sha256 |",
        "|---|---|---|---:|---|",
    ]
    for name in ("train.units.jsonl", "public_test.units.jsonl", "validation.units.jsonl"):
        info = files[name]
        lines.append(f"| {name} | {info['freeze_region']} | {info['project_region']} "
                     f"| {info['lines']} | {info['sha256']} |")
    lines += [
        "",
        "区名对应关系是项目侧 provisional 映射（尊重冻结包的族级提案，未重新切分）：",
        "",
        "| 冻结区 | 项目区 | 用途 |",
        "|---|---|---|",
        "| train | train | 训练 |",
        "| validation | public_test | 公开回归；一旦用于改方案须披露 |",
        "| calibration | validation | 选模型 / 校准 |",
        "",
        f"合计 {counts['units']:,} units / {counts['families']} families / "
        f"{counts['cases']:,} cases；choice {counts['choice']:,} · score {counts['score']:,}；"
        f"本目录范围内审计抽检 pass {counts['audit_pass']:,}。",
        "",
        "## 字段（17 键 unit）",
        "",
        "unit_id（case_id:world）、case_id、world（a / b，同一 case 的反事实世界）、"
        "family_id、mapping_id（64 种中文主题名）、source_run、source_batch、"
        "status（恒为 ACCEPTED）、split_proposal、label、answer_a / answer_b"
        "（各自独立作答，含 evidence / theory_refs / checks / reason；两者的 label 与本条 "
        "label 完全一致）、audit_status（pass / not_sampled）、state（fixed_facts / "
        "judgment_actor / observer_cutoff / action_stage / world）、question"
        "（instructions / type / criteria）、question_sha、source_sha。",
        "",
        "## 输出空间（adapter 必读）",
        "",
        "| question.type | 输出空间 | 说明 |",
        "|---|---|---|",
        "| choice | 3 种选项键集：yes,no,unknown,not_applicable；"
        "necessary,unnecessary,unknown,not_applicable；hate2,love2,mixed,neither,unknown | "
        "选项没有独立短标签，question.criteria 的键即选项、值是判定条件长文本 |",
        "| score | 整数 0-4 | question.criteria 是 5 条档位定义（下标即等级） |",
        "",
        "标签词表是异质的：不同 mapping_id 使用不同选项集，adapter 必须按 mapping_id "
        "建输出头，不能把 15 种标签值压进一个分类空间。",
        "",
        "## 来源与可复算",
        "",
        f"- pack：{source['pack']['path']}，{source['pack']['bytes']:,} bytes，"
        f"sha256 {source['pack']['sha256']}",
        f"- freeze 文件 accepted-units.jsonl：{source['freeze_units']['bytes']:,} bytes，"
        f"sha256 {source['freeze_units']['sha256']}",
        f"- freeze manifest：sha256 {source['freeze_manifest']['sha256']}，"
        f"生成时间 {source['freeze_created_at']}",
        "- 复算脚本：仓库 datasets/pol2/prepare_freeze.py verify；区计数与 sha256 见仓库 "
        "datasets/pol2/freeze-8705-v1/SPLIT-MANIFEST.json。",
        "",
        "## 诚实限制",
        "",
        "1. 未批准训练：冻结状态 FROZEN_READ_ONLY_NOT_TRAINING_APPROVED；训练需 owner 书面签字。",
        "2. 非专家金标：expert_gold=false。标注由 Agent 团队完成"
        "（deepseek-flash + deepseek-v4-pro），人工审计只抽检 19.6%。",
        "3. 审计抽检 pass 1,703 / 8,705（19.6%），覆盖率低；未抽检不等于无问题。",
        "4. 标签异质（15 种取值）、无选项短标签、answer_a / answer_b 的 checks 字段类型"
        "不统一（字符串 / 对象 / 数组 / 布尔都出现过），不可当稳定机器 schema。",
        "5. 只有中文，无英文翻译；原文没有 public_test 区，本映射是项目侧安排。",
        "6. 4,888 个 case 中 3,817 个有 a/b 反事实对，1,071 个单条；"
        "对子共享事实模板，不构成独立样本。",
        "7. 语义近重复 / 跨族重叠未做检测；族级切分只保证 family_id 粒度不混。",
        "8. 源包未声明再分发许可；公开上传前必须由数据所有者确认许可与训练授权。",
        "",
        "## 私有保留集",
        "",
        "blind_test（687 units / 5 families / 373 cases）另存于物理分开的私有目录，"
        "不随本目录发布；本目录任何文件都不含其 unit_id / family_id。",
        "",
    ]
    return "\n".join(lines)


def render_public_manifest(public_units: list[Unit], files: dict, source: dict) -> dict:
    return {
        "dataset": f"{FREEZE_ID}-public",
        "freeze_id": FREEZE_ID,
        "visibility": "public",
        "status": {"training_approved": False, "expert_gold": False,
                   "hf_upload": "NOT_UPLOADED", "freeze_status": FREEZE_STATUS},
        "line_order": "unit_id ascending (Unicode code point; ids are ASCII)",
        "files_dir": ".",
        "files": files,
        "region_mapping": {"train": "train", "validation": "public_test",
                           "calibration": "validation"},
        "counts": limited_counts(public_units),
        "output_spaces": output_spaces(public_units),
        "source": source,
        "excluded_private_holdout": {
            "visibility": "private_holdout", "units": 687, "families": 5, "cases": 373,
            "note": "content lives in a physically separate private directory",
        },
        "verify": "repo script datasets/pol2/prepare_freeze.py verify recomputes every sha256",
    }


def render_private_readme(private_units: list[Unit], files: dict, source: dict) -> str:
    counts = limited_counts(private_units)
    lines = [
        f"# {FREEZE_ID}（私有保留集 / private_holdout）",
        "",
        "**PRIVATE HOLDOUT —— 不得公开、不得进入公开仓库 / fork / PR / 日志 / 截图 / "
        "训练 Agent 上下文。**",
        "",
        "本目录是 blind_test 区（冻结提案中的盲测区）的物理隔离副本，对应项目区 "
        "private_holdout。它不随公开包发布，只在受控评测时提供给参评模型；"
        "评测环境应隔离、禁网、只导出汇总。",
        "",
        "**状态：NOT_TRAINING_APPROVED · expert_gold=false · 尚未上传任何托管。**",
        "",
        "## 文件",
        "",
        "JSONL，UTF-8，一行一个 unit，按 unit_id 升序。",
        "",
        "| 文件 | 冻结区 | 项目区 | units | sha256 |",
        "|---|---|---|---:|---|",
    ]
    for name, info in files.items():
        lines.append(f"| {name} | {info['freeze_region']} | {info['project_region']} "
                     f"| {info['lines']} | {info['sha256']} |")
    lines += [
        "",
        f"合计 {counts['units']} units / {counts['families']} families / "
        f"{counts['cases']} cases；choice {counts['choice']} · score {counts['score']}。",
        "",
        "## 使用纪律",
        "",
        "1. 只能在模型定版后的受控评测中使用；不得用于梯度、教师生成、蒸馏或选阈值。",
        "2. 不得把内容、unit_id、family_id 或逐例答案写进任何公开文件或日志。",
        "3. 公开区若被用于改方案，须在结果卡披露；本保留集只用于最终盲测。",
        "4. 源包未声明再分发许可；即使私有上传也需所有者确认。",
        "",
        "## 来源",
        "",
        f"- pack sha256 {source['pack']['sha256']}",
        f"- freeze accepted-units.jsonl sha256 {source['freeze_units']['sha256']}",
        f"- freeze manifest sha256 {source['freeze_manifest']['sha256']}",
        "- 区计数与 sha256 见仓库 datasets/pol2/freeze-8705-v1/SPLIT-MANIFEST.json"
        "（只登记计数与哈希，不含 unit_id / family_id）。",
        "",
    ]
    return "\n".join(lines)


def render_private_manifest(private_units: list[Unit], files: dict, source: dict) -> dict:
    return {
        "dataset": f"{FREEZE_ID}-holdout",
        "freeze_id": FREEZE_ID,
        "visibility": "private_holdout",
        "warning": "PRIVATE HOLDOUT: never publish, never train on it, never log unit ids.",
        "status": {"training_approved": False, "expert_gold": False,
                   "hf_upload": "NOT_UPLOADED"},
        "line_order": "unit_id ascending (Unicode code point; ids are ASCII)",
        "files_dir": ".",
        "files": files,
        "region_mapping": {"blind_test": "private_holdout"},
        "counts": limited_counts(private_units),
        "access": "kept outside the public repository; release only inside a controlled, "
                  "network-off evaluation environment",
        "source": source,
    }


LIMITATIONS = [
    "未批准训练：freeze 状态 FROZEN_READ_ONLY_NOT_TRAINING_APPROVED，training_approved=false；"
    "owner 书面签字前不得用于训练、蒸馏或教师生成。",
    "非专家金标：expert_gold=false；标注来自 Agent 团队（models 见 labeling），"
    "人工审计只做抽检。",
    "审计覆盖低：pass 1,703 / 8,705（19.6%），not_sampled 不等于无问题。",
    "标签异质：15 种 label 取值、3 种 choice 选项键集 + 0-4 score；adapter 必须按 "
    "mapping_id 建输出头。",
    "无选项短标签：choice 的选项只有键名，判定条件在 question.criteria 的长文本里。",
    "answer_a / answer_b 的 checks 与 check_evidence 类型不统一（字符串 / 对象 / 数组 / "
    "布尔），不是稳定机器 schema；580 条带 original_label / label_adapter 归一化记录。",
    "只有中文，无翻译；原文没有 public_test 区，四区到项目区的映射是项目侧 provisional 安排。",
    "3,817 / 4,888 个 case 有 a/b 反事实对，1,071 个单条；对子共享事实模板，"
    "统计上不构成独立样本。",
    "语义近重复与跨族内容重叠未检测；族级切分只保证 family_id 粒度。",
    "18 个 question 模板的 question-policy v0.8.1 以 sha256(source_question) 为键；"
    "7 个模板已修订，unit 使用修订后的 question 文本。",
    "源包未声明再分发许可；上传任何托管前必须由数据所有者确认许可与训练授权。",
    "blind_test 只以计数与 sha256 出现在 tracked 文件；其内容、unit_id、family_id 不进入"
    "公开路径。",
]


def render_tracked_manifest(stats: dict, source: dict, files: dict,
                            freeze_manifest: dict) -> dict:
    def region_entry(region: str) -> dict:
        row = dict(stats["regions"][region])
        row["freeze_region"] = region
        row["project_region"] = PROJECT_REGION[region]
        row.update(files["splits"][region])
        return row

    def export_entry(bucket: str, names: tuple[str, ...]) -> dict:
        return {
            "files": {name: files["export"][bucket][name] for name in names},
            "manifest": files["export"][bucket]["MANIFEST.json"],
            "readme": files["export"][bucket]["README.md"],
        }

    return {
        "manifest_version": 1,
        "freeze_id": FREEZE_ID,
        "generator": "datasets/pol2/prepare_freeze.py",
        "paths_relative_to": source["paths_relative_to"],
        "line_order": "unit_id ascending (Unicode code point; ids are ASCII)",
        "source": source,
        "flags": {
            "freeze_status": freeze_manifest.get("status"),
            "training_approved": bool(freeze_manifest.get("training_approved")),
            "expert_gold": bool(freeze_manifest.get("expert_gold")),
            "split_status": "PROVISIONAL_FAMILY_LEVEL_PROPOSAL_MATERIALIZED",
            "hf_upload": "NOT_UPLOADED",
            "training_gate": "training_approved=true（owner 书面签字）之前不得用于训练",
        },
        "split_rule": {
            "source": "freeze-8705-v1/manifest.json 的 split_proposal 字段",
            "proposed_split_rule": freeze_manifest.get("proposed_split_rule"),
            "recomputed": False,
            "new_salt": False,
            "note": "不重新切分、不引入新盐；仅按冻结提案物化四区，项目区映射为 provisional。",
        },
        "region_mapping": {region: PROJECT_REGION[region] for region in REGIONS},
        "regions": {region: region_entry(region) for region in REGIONS},
        "export": {
            "root": files["export"]["root"],
            "public": export_entry("public", ("train.units.jsonl", "public_test.units.jsonl",
                                              "validation.units.jsonl")),
            "private": export_entry("private", ("private_holdout.units.jsonl",)),
        },
        "schema": {
            "unit_keys": sorted(EXPECTED_UNIT_KEYS),
            "question_types": stats["question_types"],
            "label_values": stats["label_values"],
            "label_values_by_question_type": stats["label_values_by_question_type"],
            "choice_option_keysets": stats["choice_option_keysets"],
            "output_spaces": output_spaces_from_stats(stats),
            "mappings": stats["mappings"],
            "question_templates": stats["question_templates"],
            "templates": stats["templates"],
            "cases": stats["cases"],
            "ab_pair_cases": stats["ab_pair_cases"],
            "single_world_cases": stats["single_world_cases"],
            "answers": {"status": stats["answer_status"],
                        "label_agreement": stats["answer_label_agreement"]},
            "audit": stats["audit"],
            "theory_refs": stats["theory_refs"],
            "extra_answer_fields": stats["extra_answer_fields"],
        },
        "labeling": source["labeling"],
        "docs": {
            "data_card": DATA_CARD_PATH,
            "readme": README_PATH,
            "script": "prepare_freeze.py",
            "test": "test_prepare_freeze.py",
        },
        "limitations": LIMITATIONS,
    }


def output_spaces_from_stats(stats: dict) -> list[dict]:
    spaces = [{"question_type": "choice", "option_keys": row["keys"], "units": row["units"]}
              for row in stats["choice_option_keysets"]]
    if stats["question_types"].get("score"):
        spaces.append({"question_type": "score", "levels": [0, 1, 2, 3, 4],
                       "units": stats["question_types"]["score"]})
    return spaces


def source_section(freeze_bytes: dict, pack_info: dict, freeze_manifest: dict,
                   data_dir: Path, labeled: dict) -> dict:
    anchor = data_dir.resolve().parent
    frozen_files = freeze_manifest.get("frozen_files") or {}
    created = freeze_manifest.get("created_at")
    labeling = dict(labeled)
    labeling["handbook"] = labeling.get("handbook")
    return {
        "paths_relative_to": anchor_label(data_dir),
        "pack": dict(pack_info),
        "freeze_units": {
            "path": relative_posix(data_dir / "freeze-8705-v1" / "accepted-units.jsonl", anchor),
            "bytes": len(freeze_bytes["accepted-units.jsonl"]),
            "sha256": sha256_bytes(freeze_bytes["accepted-units.jsonl"]),
            "lines": line_count(freeze_bytes["accepted-units.jsonl"]),
        },
        "freeze_manifest": {
            "path": relative_posix(data_dir / "freeze-8705-v1" / "manifest.json", anchor),
            "bytes": len(freeze_bytes["manifest.json"]),
            "sha256": sha256_bytes(freeze_bytes["manifest.json"]),
        },
        "pack_extract": relative_posix(data_dir / "pack-1022" / "EXTRACT-MANIFEST.json", anchor),
        "freeze_status": freeze_manifest.get("status"),
        "freeze_created_at": iso_utc(created) if created is not None else None,
        "source_runs": len(freeze_manifest.get("source_runs") or []),
        "frozen_files": frozen_files,
        "labeling": labeling,
    }


def build_plan(units: list[Unit], stats: dict, freeze_manifest: dict, freeze_bytes: dict,
               pack_info: dict, data_dir: Path, tracked_dir: Path,
               labeled: dict) -> dict[str, bytes]:
    anchor = data_dir.resolve().parent
    freezes = {region: region_bytes(units, region) for region in REGIONS}
    public_units = [unit for unit in units if unit.region in PUBLIC_REGIONS]
    private_units = [unit for unit in units if unit.region == BLIND_REGION]

    splits_dir = data_dir / "freeze-8705-v1" / "splits"
    splits = {region: {"path": relative_posix(splits_dir / f"{region}.units.jsonl", anchor),
                       "bytes": len(freezes[region]),
                       "sha256": sha256_bytes(freezes[region]),
                       "lines": line_count(freezes[region])}
              for region in REGIONS}

    export_root = data_dir / "hf-export" / HF_EXPORT_DIR
    plan: dict[str, bytes] = {}
    public_files: dict[str, dict] = {}
    for region in PUBLIC_REGIONS:
        name = f"{PROJECT_REGION[region]}.units.jsonl"
        payload = freezes[region]
        public_files[name] = {
            "path": relative_posix(export_root / "public" / name, anchor),
            "bytes": len(payload), "sha256": sha256_bytes(payload),
            "lines": line_count(payload), "freeze_region": region,
            "project_region": PROJECT_REGION[region],
        }
        plan[public_files[name]["path"]] = payload
    private_name = "private_holdout.units.jsonl"
    private_files = {private_name: {
        "path": relative_posix(export_root / "private" / private_name, anchor),
        "bytes": len(freezes[BLIND_REGION]),
        "sha256": sha256_bytes(freezes[BLIND_REGION]),
        "lines": line_count(freezes[BLIND_REGION]),
        "freeze_region": BLIND_REGION,
        "project_region": PROJECT_REGION[BLIND_REGION],
    }}
    plan[private_files[private_name]["path"]] = freezes[BLIND_REGION]

    source = source_section(freeze_bytes, pack_info, freeze_manifest, data_dir, labeled)
    public_readme = render_public_readme(public_units, public_files, source).encode("utf-8")
    public_manifest = json_bytes(render_public_manifest(public_units, public_files, source))
    private_readme = render_private_readme(private_units, private_files, source).encode("utf-8")
    private_manifest = json_bytes(render_private_manifest(private_units, private_files, source))

    public_dir, private_dir = export_root / "public", export_root / "private"
    export_bundle = {
        "root": relative_posix(export_root, anchor),
        "public": {
            **public_files,
            "MANIFEST.json": {"path": relative_posix(public_dir / "MANIFEST.json", anchor),
                              "bytes": len(public_manifest),
                              "sha256": sha256_bytes(public_manifest)},
            "README.md": {"path": relative_posix(public_dir / "README.md", anchor),
                          "bytes": len(public_readme),
                          "sha256": sha256_bytes(public_readme)},
        },
        "private": {
            **private_files,
            "MANIFEST.json": {"path": relative_posix(private_dir / "MANIFEST.json", anchor),
                              "bytes": len(private_manifest),
                              "sha256": sha256_bytes(private_manifest)},
            "README.md": {"path": relative_posix(private_dir / "README.md", anchor),
                          "bytes": len(private_readme),
                          "sha256": sha256_bytes(private_readme)},
        },
    }
    plan[export_bundle["public"]["README.md"]["path"]] = public_readme
    plan[export_bundle["public"]["MANIFEST.json"]["path"]] = public_manifest
    plan[export_bundle["private"]["README.md"]["path"]] = private_readme
    plan[export_bundle["private"]["MANIFEST.json"]["path"]] = private_manifest

    for region in REGIONS:
        plan[splits[region]["path"]] = freezes[region]
    plan[relative_posix(data_dir / "freeze-8705-v1" / "accepted-units.jsonl", anchor)] = \
        freeze_bytes["accepted-units.jsonl"]
    plan[relative_posix(data_dir / "freeze-8705-v1" / "manifest.json", anchor)] = \
        freeze_bytes["manifest.json"]

    tracked = render_tracked_manifest(stats, source,
                                      {"splits": splits, "export": export_bundle},
                                      freeze_manifest)
    tracked_path = relative_posix(tracked_dir / "SPLIT-MANIFEST.json", anchor)
    plan[tracked_path] = json_bytes(tracked)
    return plan


# --------------------------------------------------------------------------- 抽取


def render_extract_manifest(pack_path: Path, pack_info: dict,
                            extracted: list[dict], missing: list[str],
                            excluded: list[dict], anchor: Path) -> dict:
    return {
        "generator": "datasets/pol2/prepare_freeze.py",
        "pack": {"path": relative_posix(pack_path, anchor), "bytes": pack_info["bytes"],
                 "sha256": pack_info["sha256"]},
        "layout": {
            "base": "data/pack-1022",
            "note": "tar member path 去掉前缀 root/projects/pol2-label-team-v1/root/；"
                    "完整 tar 仍是唯一真源。",
        },
        "extracted": extracted,
        "missing_members": missing,
        "excluded_members": excluded,
    }


def extraction_plan(pack_path: Path, data_dir: Path, pack_info: dict) -> tuple[dict, dict]:
    """返回 (相对 anchor 的 {路径: 字节}, 抽取报告)；不写盘。"""
    anchor = data_dir.resolve().parent
    pack_root = data_dir / "pack-1022"
    files: dict[str, bytes] = {}
    extracted: list[dict] = []
    missing: list[str] = []
    excluded: list[dict] = []
    with tarfile.open(pack_path, "r:gz") as archive:
        members = {member.name: member for member in archive.getmembers()}
        for relative in EXTRACT_MEMBERS:
            member_name = PACK_MEMBER_ROOT + relative
            member = members.get(member_name)
            if member is None or not member.isfile():
                missing.append(relative)
                continue
            handle = archive.extractfile(member)
            if handle is None:
                missing.append(relative)
                continue
            payload = handle.read()
            destination = pack_root / relative
            files[relative_posix(destination, anchor)] = payload
            extracted.append({"member": member_name,
                              "path": relative_posix(destination, anchor),
                              "bytes": len(payload), "sha256": sha256_bytes(payload)})
        for relative in EXCLUDED_MEMBERS:
            member = members.get(PACK_MEMBER_ROOT + relative)
            if member is not None:
                excluded.append({"member": PACK_MEMBER_ROOT + relative,
                                 "bytes": member.size,
                                 "reason": "体积大且不参与切分；哈希已由 freeze manifest 记录"})
    manifest = render_extract_manifest(pack_path, pack_info, extracted, missing, excluded, anchor)
    manifest_path = relative_posix(pack_root / "EXTRACT-MANIFEST.json", anchor)
    files[manifest_path] = json_bytes(manifest)
    return files, {"extracted": extracted, "missing": missing, "excluded": excluded,
                   "manifest_path": manifest_path}


def read_pack_info(pack_path: Path, anchor: Path) -> dict:
    return {"path": relative_posix(pack_path, anchor), "bytes": pack_path.stat().st_size,
            "sha256": sha256_file(pack_path)}


def assert_no_blind_leak(text: str, blind_unit_ids: set, blind_family_ids: set,
                         where: str) -> None:
    hits = [unit_id for unit_id in blind_unit_ids if unit_id in text]
    hits += [family_id for family_id in blind_family_ids if family_id in text]
    if hits:
        raise ValueError(f"{where}: blind_test identifiers leaked into a tracked path: "
                         f"{hits[:3]} (+{max(0, len(hits) - 3)} more)")


def label_metadata(data_dir: Path, anchor: Path) -> dict:
    """读取物化的 team / handbook / question-policy / gates 元数据（缺失则 None）。"""
    pack_root = data_dir / "pack-1022"
    labeled: dict = {"models": None, "roles": None, "handbook": None,
                     "question_policy": None, "gates": None}
    team_path = pack_root / "team.json"
    if team_path.is_file():
        try:
            team = json.loads(team_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            team = {}
        labeled["models"] = team.get("models")
        labeled["roles"] = sorted(team.get("profiles") or {})
    handbook_path = pack_root / "handbook.md"
    if handbook_path.is_file():
        text = handbook_path.read_text(encoding="utf-8", errors="replace")
        found = re.search(r"POL2答案判定手册\s*(v[0-9.]+)", text)
        labeled["handbook"] = {
            "path": relative_posix(handbook_path, anchor),
            "sha256": sha256_file(handbook_path),
            "version": found.group(1) if found else None,
        }
    policy_path = pack_root / "question-policy.json"
    if policy_path.is_file():
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            policy = {}
        labeled["question_policy"] = {
            "path": relative_posix(policy_path, anchor),
            "sha256": sha256_file(policy_path),
            "version": policy.get("version"),
            "entries": len(policy.get("entries") or {}),
        }
    gates_path = pack_root / "gates.json"
    if gates_path.is_file():
        try:
            labeled["gates"] = json.loads(gates_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            labeled["gates"] = None
    return labeled


# --------------------------------------------------------------------------- build


def build(pack_path: Path, data_dir: Path, tracked_dir: Path,
          allow_pack_change: bool = False) -> dict:
    pack_path = pack_path.resolve()
    data_dir = data_dir.resolve()
    tracked_dir = tracked_dir.resolve()
    anchor = data_dir.parent
    if not pack_path.is_file():
        raise ValueError(f"pack not found: {pack_path}")
    if not tracked_dir.is_relative_to(anchor):
        raise ValueError(f"tracked dir must live under {anchor} for portable paths")
    tracked_manifest_path = tracked_dir / "SPLIT-MANIFEST.json"
    if tracked_manifest_path.is_relative_to(data_dir):
        raise ValueError("tracked manifest must not live inside the gitignored data dir")

    pack_info = read_pack_info(pack_path, anchor)
    if tracked_manifest_path.is_file() and not allow_pack_change:
        previous = json.loads(tracked_manifest_path.read_text(encoding="utf-8"))
        previous_pack = (previous.get("source") or {}).get("pack") or {}
        if previous_pack.get("sha256") and previous_pack["sha256"] != pack_info["sha256"]:
            raise ValueError("pack sha256 differs from the existing SPLIT-MANIFEST; "
                             "pass --allow-pack-change to rebuild intentionally")

    extraction_files, extraction_report = extraction_plan(pack_path, data_dir, pack_info)
    for relative, payload in extraction_files.items():
        write_bytes_atomic(anchor / relative, payload)

    freeze_prefix = relative_posix(data_dir / "pack-1022" / "freeze-8705-v1", anchor)
    freeze_bytes = {
        "accepted-units.jsonl": extraction_files[f"{freeze_prefix}/accepted-units.jsonl"],
        "manifest.json": extraction_files[f"{freeze_prefix}/manifest.json"],
    }
    freeze_manifest = json.loads(freeze_bytes["manifest.json"].decode("utf-8"))

    frozen = freeze_manifest.get("frozen_files") or {}
    for name, payload in freeze_bytes.items():
        recorded = frozen.get(name)
        if recorded is not None and recorded != sha256_bytes(payload):
            raise ValueError(f"{name}: extracted sha256 != freeze manifest frozen_files")
    for relative in ("inputs/theory.md", "inputs/theory-index.md"):
        recorded = frozen.get(relative)
        path = anchor / relative_posix(data_dir / "pack-1022" / relative, anchor)
        if path.is_file() and recorded is not None and sha256_file(path) != recorded:
            raise ValueError(f"{relative}: extracted sha256 != freeze manifest frozen_files")

    units = load_units_from_bytes(freeze_bytes["accepted-units.jsonl"])
    stats, failures = analyze_units(units, freeze_manifest,
                                    sha256_bytes(freeze_bytes["accepted-units.jsonl"]))
    raise_failures(failures)

    labeled = label_metadata(data_dir, anchor)
    plan = build_plan(units, stats, freeze_manifest, freeze_bytes, pack_info, data_dir,
                      tracked_dir, labeled)

    blind_units = [unit for unit in units if unit.region == BLIND_REGION]
    blind_ids = {unit.unit_id for unit in blind_units}
    blind_families = {unit.data["family_id"] for unit in blind_units}
    public_ids = {unit.unit_id for unit in units if unit.region in PUBLIC_REGIONS}
    leaked = public_ids & blind_ids
    if leaked:
        raise ValueError(f"blind units leaked into public split: {sorted(leaked)[:3]}")

    tracked_rel = relative_posix(tracked_manifest_path, anchor)
    assert_no_blind_leak(plan[tracked_rel].decode("utf-8"), blind_ids, blind_families,
                         tracked_rel)

    for relative, payload in plan.items():
        write_bytes_atomic(anchor / relative, payload)
        if (anchor / relative).read_bytes() != payload:
            raise ValueError(f"write verification failed for {relative}")

    return {
        "command": "build",
        "status": "pass",
        "freeze_id": FREEZE_ID,
        "pack": pack_info,
        "units": len(units),
        "families": stats["families"],
        "cases": stats["cases"],
        "regions": {region: stats["regions"][region]["units"] for region in REGIONS},
        "schema": {"question_types": stats["question_types"], "mappings": stats["mappings"],
                   "audit": stats["audit"]},
        "extracted_members": len(extraction_report["extracted"]),
        "missing_members": extraction_report["missing"],
        "written_files": sorted(plan),
        "tracked_manifest": {"path": tracked_rel,
                             "sha256": sha256_bytes(plan[tracked_rel]),
                             "bytes": len(plan[tracked_rel])},
        "blind_guard": "pass",
    }


# --------------------------------------------------------------------------- verify


def verify_question_policy(data_dir: Path, units: list[Unit]) -> dict:
    policy_path = data_dir / "pack-1022" / "question-policy.json"
    if not policy_path.is_file():
        return {"status": "skip", "detail": "question-policy.json not extracted"}
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "fail", "detail": f"unreadable question-policy.json: {error}"}
    entries = policy.get("entries") or {}
    covered = set(entries)
    revised = 0
    for entry in entries.values():
        if not isinstance(entry, dict):
            return {"status": "fail", "detail": "question-policy entry is not an object"}
        question = entry.get("question")
        if isinstance(question, dict):
            covered.add(sha256_bytes(canonical_json(question).encode("utf-8")))
        if entry.get("revised"):
            revised += 1
    templates = {unit.data.get("question_sha") for unit in units}
    uncovered = sorted(value for value in templates if value not in covered)
    detail = {"version": policy.get("version"), "entries": len(entries), "revised": revised,
              "unit_templates": len(templates),
              "covered_templates": len(templates) - len(uncovered)}
    if uncovered:
        return {"status": "fail", "detail": {**detail, "uncovered": uncovered[:3]}}
    return {"status": "pass", "detail": detail}


def _check_detail(name: str, stats: dict):
    if name == "unit_count":
        return {"units": stats["units"], "families": stats["families"]}
    if name == "split_counts":
        return {region: stats["regions"][region]["units"] for region in REGIONS}
    if name == "audit_coverage":
        return stats["audit"]
    if name == "question_sha":
        return {"templates": stats["question_templates"]}
    if name == "mapping_label_vocabulary":
        return {"mappings": stats["mappings"]}
    return {"ok": True}


def verify(pack_path: Path, data_dir: Path, tracked_dir: Path) -> dict:
    pack_path = pack_path.resolve()
    data_dir = data_dir.resolve()
    tracked_dir = tracked_dir.resolve()
    anchor = data_dir.parent
    report: dict = {"command": "verify", "freeze_id": FREEZE_ID,
                    "pack": {"present": pack_path.is_file()}, "checks": [], "errors": []}

    def check(name: str, status: str, detail) -> None:
        report["checks"].append({"check": name, "status": status, "detail": detail})
        if status == "fail":
            message = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
            report["errors"].append(f"{name}: {message}")

    units_path = data_dir / "freeze-8705-v1" / "accepted-units.jsonl"
    manifest_path = data_dir / "freeze-8705-v1" / "manifest.json"
    if not units_path.is_file() or not manifest_path.is_file():
        check("data_layout", "fail",
              f"missing {relative_posix(units_path, anchor)}; run build first")
        report["status"] = "fail"
        return report

    freeze_bytes = {"accepted-units.jsonl": units_path.read_bytes(),
                    "manifest.json": manifest_path.read_bytes()}
    freeze_manifest = json.loads(freeze_bytes["manifest.json"].decode("utf-8"))
    units = load_units_from_bytes(freeze_bytes["accepted-units.jsonl"])
    units_sha = sha256_bytes(freeze_bytes["accepted-units.jsonl"])

    # ---- pack 绑定：有 tar 时以 tar 为信任根；无 tar 时只做自洽复核
    if pack_path.is_file():
        pack_info = read_pack_info(pack_path, anchor)
        report["pack"] = {**pack_info, "present": True}
        report["integrity_basis"] = "pack"
        extraction_files, extraction_report = extraction_plan(pack_path, data_dir, pack_info)
        mismatched = [relative for relative, payload in extraction_files.items()
                      if not (anchor / relative).is_file()
                      or (anchor / relative).read_bytes() != payload]
        check("pack_extraction",
              "pass" if not mismatched else "fail",
              {"checked": len(extraction_files), "mismatched": mismatched[:5],
               "missing_members": extraction_report["missing"]})
        packed = extraction_files.get(
            f"{relative_posix(data_dir / 'pack-1022' / 'freeze-8705-v1', anchor)}"
            f"/accepted-units.jsonl")
        check("pack_freeze_binding",
              "pass" if packed == freeze_bytes["accepted-units.jsonl"] else "fail",
              {"tar_sha256": sha256_bytes(packed) if packed is not None else None,
               "data_sha256": units_sha})
    else:
        pack_info = None
        report["pack"] = {"present": False,
                          "note": "pack-1022.tar.gz absent; verifying self-consistency only"}
        report["integrity_basis"] = "data_only"

    # ---- 数据不变式
    stats, failures = analyze_units(units, freeze_manifest, units_sha)
    for name, messages in failures.items():
        check(name, "pass" if not messages else "fail",
              messages if messages else _check_detail(name, stats))
    report["freeze"] = {"units": stats["units"], "families": stats["families"],
                        "cases": stats["cases"], "accepted_units_sha256": units_sha,
                        "manifest_sha256": sha256_bytes(freeze_bytes["manifest.json"])}
    report["schema"] = {
        "question_types": stats["question_types"],
        "label_values": stats["label_values"],
        "label_values_by_question_type": stats["label_values_by_question_type"],
        "mappings": stats["mappings"],
        "mapping_label_vocabulary": stats["mapping_label_vocabulary"],
        "question_templates": stats["question_templates"],
        "choice_option_keysets": stats["choice_option_keysets"],
        "ab_pair_cases": stats["ab_pair_cases"],
        "single_world_cases": stats["single_world_cases"],
        "audit": stats["audit"],
        "answer_label_agreement": stats["answer_label_agreement"],
    }
    report["regions"] = {region: {**stats["regions"][region],
                                  "project_region": PROJECT_REGION[region]}
                         for region in REGIONS}

    policy = verify_question_policy(data_dir, units)
    check("question_policy_coverage", policy["status"], policy["detail"])

    # ---- tracked manifest 盲区守卫 + 逐字节复算
    tracked_manifest_path = tracked_dir / "SPLIT-MANIFEST.json"
    blind_units = [unit for unit in units if unit.region == BLIND_REGION]
    blind_ids = {unit.unit_id for unit in blind_units}
    blind_families = {unit.data["family_id"] for unit in blind_units}
    if not tracked_manifest_path.is_file():
        check("tracked_manifest", "fail",
              f"missing {relative_posix(tracked_manifest_path, anchor)}")
        report["status"] = "fail"
        return report

    raw_tracked = tracked_manifest_path.read_bytes()
    text = raw_tracked.decode("utf-8")
    leaked = [unit_id for unit_id in blind_ids if unit_id in text]
    leaked += [family_id for family_id in blind_families if family_id in text]
    check("tracked_manifest_blind_guard", "pass" if not leaked else "fail",
          {"blind_hits": leaked[:3]} if leaked else {"blind_hits": 0})

    tracked_pack = (json.loads(text).get("source") or {}).get("pack") or {}
    if pack_info is None:
        if not tracked_pack.get("sha256"):
            check("tracked_manifest", "fail", "no pack info to rebuild the source section")
            report["status"] = "fail"
            return report
        pack_info = tracked_pack

    labeled = label_metadata(data_dir, anchor)
    plan = build_plan(units, stats, freeze_manifest, freeze_bytes, pack_info, data_dir,
                      tracked_dir, labeled)
    tracked_rel = relative_posix(tracked_manifest_path, anchor)
    expected_tracked = plan.get(tracked_rel)
    reproducible = expected_tracked == raw_tracked
    check("tracked_manifest", "pass" if reproducible else "fail",
          {"sha256": sha256_bytes(raw_tracked), "bytes": len(raw_tracked),
           "reproducible": reproducible})
    report["tracked_manifest"] = {"path": tracked_rel, "sha256": sha256_bytes(raw_tracked),
                                  "bytes": len(raw_tracked), "reproducible": reproducible}

    if expected_tracked is not None:
        mismatched = [relative for relative, payload in plan.items()
                      if not (anchor / relative).is_file()
                      or (anchor / relative).read_bytes() != payload]
        missing = [relative for relative in plan if not (anchor / relative).is_file()]
        check("files_reproducible", "pass" if not mismatched and not missing else "fail",
              {"checked": len(plan),
               "mismatched": [value for value in mismatched if value not in missing][:5],
               "missing": missing[:5]})
        split_report = {}
        for region in REGIONS:
            payload = plan[relative_posix(
                data_dir / "freeze-8705-v1" / "splits" / f"{region}.units.jsonl", anchor)]
            split_report[region] = {"sha256": sha256_bytes(payload), "bytes": len(payload)}
        report["files"] = {"checked": len(plan), "splits": split_report}
        export_root = data_dir / "hf-export" / HF_EXPORT_DIR
        export_public = {}
        for name, region in (("train.units.jsonl", "train"),
                             ("public_test.units.jsonl", "validation"),
                             ("validation.units.jsonl", "calibration")):
            payload = plan[relative_posix(export_root / "public" / name, anchor)]
            export_public[name] = {"sha256": sha256_bytes(payload), "bytes": len(payload),
                                   "project_region": PROJECT_REGION[region]}
        private_payload = plan[relative_posix(
            export_root / "private" / "private_holdout.units.jsonl", anchor)]
        report["export"] = {"public": export_public,
                            "private": {"private_holdout.units.jsonl": {
                                "sha256": sha256_bytes(private_payload),
                                "bytes": len(private_payload)}}}

    report["status"] = "pass" if not report["errors"] else "fail"
    report["check_counts"] = {
        "pass": sum(1 for row in report["checks"] if row["status"] == "pass"),
        "fail": sum(1 for row in report["checks"] if row["status"] == "fail"),
        "skip": sum(1 for row in report["checks"] if row["status"] == "skip"),
    }
    return report


# --------------------------------------------------------------------------- CLI


def print_human(report: dict) -> None:
    command = report.get("command")
    print(f"{command}: {report.get('freeze_id')} -> {report.get('status')}")
    if command == "build":
        print(f"  units={report['units']} families={report['families']} "
              f"cases={report['cases']}")
        print("  regions: " + ", ".join(f"{key}={value}"
                                        for key, value in report["regions"].items()))
        print(f"  wrote {len(report['written_files'])} files")
        print(f"  tracked manifest: {report['tracked_manifest']['path']} "
              f"sha256={report['tracked_manifest']['sha256']}")
        return
    if report.get("pack", {}).get("present"):
        print(f"  pack sha256: {report['pack']['sha256']}")
        print(f"  integrity basis: {report.get('integrity_basis')}")
    else:
        print("  pack: absent (self-consistency only)")
    freeze = report.get("freeze", {})
    print(f"  units={freeze.get('units')} families={freeze.get('families')} "
          f"cases={freeze.get('cases')}")
    print(f"  accepted-units sha256: {freeze.get('accepted_units_sha256')}")
    for region, row in (report.get("regions") or {}).items():
        print(f"  {region:<11} units={row['units']:<5} families={row['families']:<3} "
              f"cases={row['cases']:<5} project={row['project_region']}")
    if "tracked_manifest" in report:
        print(f"  tracked manifest sha256: {report['tracked_manifest']['sha256']}")
        print(f"  tracked manifest reproducible: {report['tracked_manifest']['reproducible']}")
    counts = report.get("check_counts", {})
    print(f"  checks: {counts.get('pass', 0)} pass / {counts.get('fail', 0)} fail / "
          f"{counts.get('skip', 0)} skip")
    for error in report.get("errors", []):
        print(f"  ERROR: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("build", "extract + materialize splits + HF export + manifest"),
                            ("verify", "read-only re-check; recomputes every sha256")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--pack", type=Path, default=DEFAULT_PACK)
        command.add_argument("--data", type=Path, default=DEFAULT_DATA)
        command.add_argument("--tracked", type=Path, default=DEFAULT_TRACKED)
        command.add_argument("--json", action="store_true", help="emit the report as JSON")
        if name == "build":
            command.add_argument("--allow-pack-change", action="store_true",
                                 help="rebuild even if the pack sha256 differs from the manifest")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            report = build(args.pack, args.data, args.tracked, args.allow_pack_change)
        else:
            report = verify(args.pack, args.data, args.tracked)
    except (OSError, ValueError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0 if report.get("status") == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
