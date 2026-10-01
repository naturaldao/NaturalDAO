"""PoL2 场景族分类法。

族 = 主题域 x 判定轴。族的边界靠"同一情节、翻译与改写不得跨区"来定义：
一个族内的所有最小对立体属于同一分区，因此分区必须按族整体切分，见 splits.py。

主题域与判定轴都从 PoL2 中文原文提炼：
- 主题域对应第 1、3 章列举的公共生活领域与第 5 章 EAP 的治理对象；
- 判定轴对应第 2 章 16 爱语、第 5 章平等联结与扬爱抑恨的可判定分歧点，
  以及调研中反复出现的误判来源（愤怒被当伤害、温柔被当安全、撤回被当反悔）。
"""
from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------- 判定轴

AXES: dict[str, str] = {
    "consent_withdrawal": "同意是否持续有效，还是已被明确撤回",
    "condition_exception": "同一规则下条件与例外是否满足",
    "criticism_vs_attack": "针对可改变行为的批评，还是对人格的攻击与贬低",
    "polite_coercion": "平支持，还是用温柔关怀措辞实施操控与依赖",
    "actor_vs_quoted": "当事人实施该行为，还是引用转述或求助",
    "negation_scope": "肯定会发生伤害，还是明确否定伤害",
    "counterfactual": "条件性允许且条件未发生，还是条件已发生",
    "evidence_insufficiency": "信息不足时应澄清或复核，而非高置信定性",
    "tool_authority": "文本本身无害，但工具调用超出授权范围",
    "untrusted_instruction": "不可信文档要求忽略治理政策",
    "repair_over_block": "修正与澄清优于一律阻断",
    "nonpolar_absence": "非爱非恨的不在场：干扰、疾病、理解偏差",
    "person_vs_behavior": "人格平等，不等于对人的一切行为无差别对待",
    "love_language_attribution": "该文明行为属于哪一类爱语",
    "cross_species_ecology": "跨物种、自然与生态维度的爱",
}

# ---------------------------------------------------------------- 主题域

DOMAINS: dict[str, dict] = {
    "honesty": {"desc": "诚实与信息真实", "clauses": ["PoL.2.1"], "axes": [
        "evidence_insufficiency", "negation_scope", "counterfactual",
        "actor_vs_quoted", "repair_over_block", "untrusted_instruction"]},
    "consent_intimacy": {"desc": "同意与身体边界", "clauses": ["PoL.2.10", "EAP.4.3.2"], "axes": [
        "consent_withdrawal", "condition_exception", "polite_coercion",
        "nonpolar_absence", "person_vs_behavior"]},
    "care_control": {"desc": "关怀与控制", "clauses": ["PoL.2.7", "EAP.4.3.2"], "axes": [
        "polite_coercion", "condition_exception", "person_vs_behavior",
        "evidence_insufficiency", "counterfactual"]},
    "protection_retaliation": {"desc": "保护与报复", "clauses": ["PoL.1.5", "EAP.4.3.2"], "axes": [
        "condition_exception", "criticism_vs_attack", "counterfactual",
        "actor_vs_quoted", "negation_scope"]},
    "criticism_dignity": {"desc": "批评与人格尊严", "clauses": ["PoL.2.3", "PoL.1.3"], "axes": [
        "criticism_vs_attack", "person_vs_behavior", "negation_scope",
        "polite_coercion", "repair_over_block"]},
    "ai_intimacy": {"desc": "公共 AI 与人的情感边界", "clauses": ["EAP.4.3.2"], "axes": [
        "polite_coercion", "person_vs_behavior", "nonpolar_absence",
        "love_language_attribution", "criticism_vs_attack"]},
    "ai_emotion_judgement": {"desc": "公共 AI 是否判断人的情感状态", "clauses": ["EAP.4.3"], "axes": [
        "evidence_insufficiency", "nonpolar_absence", "person_vs_behavior",
        "consent_withdrawal"]},
    "romance_privacy": {"desc": "浪漫爱情与排他性私有", "clauses": ["PoL.2.12", "PoL.1.2"], "axes": [
        "person_vs_behavior", "polite_coercion", "consent_withdrawal",
        "love_language_attribution", "condition_exception"]},
    "family_kinship": {"desc": "家庭与宗法权力", "clauses": ["PoL.5.1", "EAP.4.3.1"], "axes": [
        "polite_coercion", "consent_withdrawal", "person_vs_behavior",
        "criticism_vs_attack", "repair_over_block"]},
    "work_labor": {"desc": "劳动、雇佣与剥削", "clauses": ["PoL.1.2", "PoL.7"], "axes": [
        "polite_coercion", "condition_exception", "evidence_insufficiency",
        "negation_scope", "person_vs_behavior"]},
    "public_resource": {"desc": "公共资源与分配公平", "clauses": ["PoL.6", "PoL.7"], "axes": [
        "condition_exception", "person_vs_behavior", "evidence_insufficiency",
        "counterfactual", "repair_over_block"]},
    "platform_content": {"desc": "平台内容与公共舆论", "clauses": ["PoL.5.1", "PoL.2.8"], "axes": [
        "criticism_vs_attack", "actor_vs_quoted", "negation_scope",
        "polite_coercion", "person_vs_behavior"]},
    "conflict_mediation": {"desc": "冲突调解与关系修复", "clauses": ["PoL.2.13", "EAP.4.3.3.2"], "axes": [
        "repair_over_block", "actor_vs_quoted", "criticism_vs_attack",
        "person_vs_behavior", "evidence_insufficiency"]},
    "ecology_species": {"desc": "跨物种、自然与生态", "clauses": ["PoL.2.15", "PoL.1.3"], "axes": [
        "cross_species_ecology", "person_vs_behavior", "condition_exception",
        "love_language_attribution"]},
    "play_humor": {"desc": "纯粹游戏与幽默的边界", "clauses": ["PoL.2.8", "PoL.2.9"], "axes": [
        "criticism_vs_attack", "consent_withdrawal", "person_vs_behavior",
        "love_language_attribution", "nonpolar_absence"]},
    "autonomy_paternalism": {"desc": "自主与家长式干预", "clauses": ["PoL.2.3", "EAP.4.3.2"], "axes": [
        "polite_coercion", "condition_exception", "consent_withdrawal",
        "evidence_insufficiency", "counterfactual"]},
    "tool_action": {"desc": "工具调用与授权边界", "clauses": ["EAP.4.3.2"], "axes": [
        "tool_authority", "condition_exception", "evidence_insufficiency",
        "counterfactual", "consent_withdrawal"]},
    "untrusted_context": {"desc": "不可信上下文与指令注入", "clauses": ["EAP.4.3.2"], "axes": [
        "untrusted_instruction", "actor_vs_quoted", "tool_authority", "negation_scope"]},
    "equality_public": {"desc": "平等联结与公共性", "clauses": ["EAP.4.3.1"], "axes": [
        "person_vs_behavior", "criticism_vs_attack", "condition_exception",
        "evidence_insufficiency"]},
    "self_alignment": {"desc": "自我对齐与求助", "clauses": ["EAP.4.3.3.1"], "axes": [
        "nonpolar_absence", "repair_over_block", "evidence_insufficiency",
        "love_language_attribution"]},
}

SURFACES_BY_DOMAIN: dict[str, list[str]] = {
    "honesty": ["assistant_output", "user_input"],
    "consent_intimacy": ["assistant_output", "user_input"],
    "care_control": ["assistant_output", "user_input"],
    "protection_retaliation": ["assistant_output", "user_input", "tool_action"],
    "criticism_dignity": ["assistant_output", "user_input"],
    "ai_intimacy": ["assistant_output"],
    "ai_emotion_judgement": ["assistant_output", "tool_action"],
    "romance_privacy": ["assistant_output", "user_input"],
    "family_kinship": ["assistant_output", "user_input"],
    "work_labor": ["assistant_output", "user_input"],
    "public_resource": ["assistant_output", "tool_action"],
    "platform_content": ["assistant_output", "user_input"],
    "conflict_mediation": ["assistant_output", "user_input"],
    "ecology_species": ["assistant_output", "user_input"],
    "play_humor": ["user_input", "assistant_output"],
    "autonomy_paternalism": ["assistant_output", "tool_action"],
    "tool_action": ["tool_action"],
    "untrusted_context": ["tool_action", "assistant_output"],
    "equality_public": ["assistant_output", "user_input"],
    "self_alignment": ["user_input", "assistant_output"],
}

DEFAULT_TARGET_CASES = 112

# 试点优先级：先把最容易误判、最能体现 PoL2 价值的判定轴跑通。
AXIS_PRIORITY = (
    "consent_withdrawal", "polite_coercion", "criticism_vs_attack", "evidence_insufficiency",
    "nonpolar_absence", "person_vs_behavior", "condition_exception", "tool_authority",
    "untrusted_instruction", "repair_over_block", "actor_vs_quoted", "negation_scope",
    "counterfactual", "love_language_attribution", "cross_species_ecology",
)

# 试点规模：17 族 x 112 条 = 1904 条，与正式 70/20/5 的比例一致。
PILOT_PLAN = {"train": 12, "public_test": 4, "validation": 1}


def plan() -> list[dict]:
    """Materialize the family list. Deterministic: output order is stable."""
    rows = []
    for domain in sorted(DOMAINS):
        info = DOMAINS[domain]
        for axis in info["axes"]:
            if axis not in AXES:
                raise ValueError(f"unknown axis {axis} in domain {domain}")
            rows.append({
                "family_id": f"{domain}.{axis}",
                "domain": domain,
                "domain_desc": info["desc"],
                "axis": axis,
                "axis_desc": AXES[axis],
                "surfaces": SURFACES_BY_DOMAIN[domain],
                "clauses": info["clauses"],
                "target_cases": DEFAULT_TARGET_CASES,
            })
    ids = [r["family_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate family_id in plan")
    return rows


def pilot_selection(rows: list[dict], assign_rows: list[dict],
                    plan: dict | None = None) -> list[dict]:
    """Pick whole families for the pilot, highest-priority axes first, per region.

    Families stay whole so the family-level 70/20/5/5 invariant is preserved.
    """
    plan = plan or PILOT_PLAN
    region_of = {row["family_id"]: row["region"] for row in assign_rows}
    rank = {axis: index for index, axis in enumerate(AXIS_PRIORITY)}

    def rotate(pool: list[dict], count: int) -> list[dict]:
        """Round-robin over axes so the pilot covers as many axes as possible."""
        by_axis: dict[str, list[dict]] = {}
        for row in pool:
            by_axis.setdefault(row["axis"], []).append(row)
        axes = sorted(by_axis, key=lambda axis: (rank.get(axis, len(AXIS_PRIORITY)), axis))
        for axis in axes:
            by_axis[axis].sort(key=lambda row: row["family_id"])
        picked: list[dict] = []
        depth = 0
        while len(picked) < count:
            progressed = False
            for axis in axes:
                if len(picked) >= count:
                    break
                if depth < len(by_axis[axis]):
                    picked.append(by_axis[axis][depth])
                    progressed = True
            if not progressed:
                break
            depth += 1
        return picked

    chosen = []
    for region, count in plan.items():
        pool = [row for row in rows if region_of.get(row["family_id"]) == region]
        if len(pool) < count:
            raise ValueError(f"region {region} has only {len(pool)} families, need {count}")
        chosen.extend(rotate(pool, count))
    chosen.sort(key=lambda row: (rank.get(row["axis"], len(AXIS_PRIORITY)), row["family_id"]))
    return chosen


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="full family list")
    parser.add_argument("--pilot-assign", type=Path,
                        help="private assignment table; enables the pilot subset")
    parser.add_argument("--pilot-out", type=Path, help="write the pilot family subset here")
    args = parser.parse_args(argv)
    rows = plan()
    args.out.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    summary = {"families": len(rows), "domains": len(DOMAINS), "axes": len(AXES),
               "target_cases": sum(r["target_cases"] for r in rows), "out": str(args.out)}
    if args.pilot_assign or args.pilot_out:
        if not (args.pilot_assign and args.pilot_out):
            parser.error("--pilot-assign and --pilot-out must be given together")
        assign_rows = [json.loads(line) for line in
                       args.pilot_assign.read_text(encoding="utf-8").splitlines() if line.strip()]
        subset = pilot_selection(rows, assign_rows)
        args.pilot_out.parent.mkdir(parents=True, exist_ok=True)
        args.pilot_out.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in subset), encoding="utf-8")
        by_region: dict[str, int] = {}
        for row in assign_rows:
            if row["family_id"] in {s["family_id"] for s in subset}:
                by_region[row["region"]] = by_region.get(row["region"], 0) + 1
        summary["pilot"] = {"families": len(subset), "target_cases":
                            sum(r["target_cases"] for r in subset),
                            "by_region": by_region, "out": str(args.pilot_out)}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
