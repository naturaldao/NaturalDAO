"""Test bounded source-restoration after task authorization is revoked.

The experiment keeps task permission and preconfigured RECOVERY_ONLY authority
separate. It reports physical terminal predicates from the MuJoCo state and
never treats an object-held intermediate state as a safe recovery outcome.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = HERE / "results"
FIGURES = ROOT / "Research" / "figures"
STYLE_ROOT = ROOT / "PoL-Governance" / "Research" / "PoL2-DAO-Governance-Lab" / "src"
sys.path.insert(0, str(STYLE_ROOT))

from pol2dao.plotstyle import PALETTE, finalize_figure, new_figure  # noqa: E402
from run_mujoco_typed_pick_place import (  # noqa: E402
    POLICY_SHA256,
    box_position,
    build_scene,
    ee_position,
    execute_transfer,
    gripper_contact,
    move_hand,
    observation,
    set_gripper,
)


SOURCE_TABLE = "table"
TRAY_FLOOR = "tray_floor"
TRAY_XY = np.array([0.43, -0.24])
CARRY_Z = 0.625
SOURCE_PLACE_Z = 0.535
POLICY_ID = "pol2-embodied-recovery-policy-v0.1"


def geom_contact(model: mujoco.MjModel, data: mujoco.MjData,
                 geom_a: int, geom_b: int) -> bool:
    return any({int(data.contact[i].geom1), int(data.contact[i].geom2)} == {geom_a, geom_b}
               for i in range(data.ncon))


def recover_to_source(model: mujoco.MjModel, data: mujoco.MjData,
                      names: dict, source: np.ndarray,
                      authority: str) -> dict:
    phases: list[dict] = []
    contact = gripper_contact(model, data, names)
    initial_position = box_position(data, names)
    initial_ee = ee_position(data, names)
    table_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, SOURCE_TABLE)
    tray_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, TRAY_FLOOR)
    start_error = float(np.linalg.norm(initial_ee - np.array([*TRAY_XY, CARRY_Z])))

    preconditions = {
        "bilateral_grasp": all(contact.values()),
        "target_not_reached": not observation(data, names, "DENIED", 0)["target"]["box_in_target"],
        "carry_pose_error_m": round(start_error, 5),
        "carry_pose_within_0_04m": start_error <= 0.04,
        "source_workspace_valid": bool(0.25 <= source[0] <= 0.78 and -0.42 <= source[1] <= 0.35),
    }
    if authority != "RECOVERY_ONLY":
        return {"status": "recovery_unavailable", "reason": "recovery_authority_not_explicitly_granted",
                "authority": authority, "preconditions": preconditions, "phases": phases}
    if not all((preconditions["bilateral_grasp"], preconditions["target_not_reached"],
                preconditions["carry_pose_within_0_04m"], preconditions["source_workspace_valid"])):
        return {"status": "recovery_failed", "reason": "recovery_precondition_failed",
                "authority": authority, "preconditions": preconditions, "phases": phases}

    try:
        move_hand(model, data, names, [float(source[0]), float(source[1]), CARRY_Z],
                  "recovery_return_over_source", phases)
        after_transport_contact = gripper_contact(model, data, names)
        if not all(after_transport_contact.values()):
            raise RuntimeError("bilateral_grasp_lost_during_recovery_transport")
        move_hand(model, data, names, [float(source[0]), float(source[1]), SOURCE_PLACE_Z],
                  "recovery_lower_to_source", phases)
        before_release_contact = gripper_contact(model, data, names)
        if not all(before_release_contact.values()):
            raise RuntimeError("bilateral_grasp_lost_before_recovery_release")
        set_gripper(model, data, names, control=255)
        phases.append({"phase": "recovery_release", "box_m": np.round(box_position(data, names), 4).tolist()})
        for _ in range(240):
            mujoco.mj_step(model, data)

        released_contact = gripper_contact(model, data, names)
        on_source_obs = observation(data, names, "DENIED", 0)
        source_support = geom_contact(model, data, names["box_geom"], table_id)
        tray_support = geom_contact(model, data, names["box_geom"], tray_id)
        postconditions = {
            "object_on_source": on_source_obs["object"]["on_source_table"],
            "direct_source_table_contact": source_support,
            "gripper_released": not any(released_contact.values()),
            "target_predicate_false": not on_source_obs["target"]["box_in_target"],
            "object_position_m": np.round(box_position(data, names), 4).tolist(),
            "source_position_error_m": round(float(np.linalg.norm(box_position(data, names) - source)), 5),
            "tray_floor_contact": tray_support,
        }
        if not (postconditions["object_on_source"] and postconditions["direct_source_table_contact"]
                and postconditions["gripper_released"] and postconditions["target_predicate_false"]):
            return {"status": "recovery_failed", "reason": "source_restoration_postcondition_failed",
                    "authority": authority, "preconditions": preconditions,
                    "postconditions": postconditions, "phases": phases}

        move_hand(model, data, names, [float(source[0]), float(source[1]), 0.64],
                  "recovery_retreat_after_support_verified", phases)
        for _ in range(120):
            mujoco.mj_step(model, data)
        final_contact = gripper_contact(model, data, names)
        final_obs = observation(data, names, "DENIED", 0)
        final_support = geom_contact(model, data, names["box_geom"], table_id)
        postconditions.update({
            "object_on_source_after_retreat": final_obs["object"]["on_source_table"],
            "source_contact_after_retreat": final_support,
            "gripper_released_after_retreat": not any(final_contact.values()),
            "target_predicate_false_after_retreat": not final_obs["target"]["box_in_target"],
            "final_object_position_m": np.round(box_position(data, names), 4).tolist(),
        })
        success = all((postconditions["object_on_source_after_retreat"],
                       postconditions["source_contact_after_retreat"],
                       postconditions["gripper_released_after_retreat"],
                       postconditions["target_predicate_false_after_retreat"]))
        return {"status": "recovery_succeeded" if success else "recovery_failed",
                "reason": "all_machine_postconditions_hold" if success else "post_retreat_check_failed",
                "authority": authority, "preconditions": preconditions,
                "postconditions": postconditions, "phases": phases,
                "object_position_before_recovery_m": np.round(initial_position, 4).tolist()}
    except Exception as exc:
        return {"status": "recovery_failed", "reason": "controller_or_monitor_exception",
                "error_type": type(exc).__name__, "authority": authority,
                "preconditions": preconditions, "phases": phases}


def run_case(case_id: str, permissions: list[str], recovery_authority: str) -> dict:
    model, data, names = build_scene()
    mujoco.mj_forward(model, data)
    for _ in range(250):
        mujoco.mj_step(model, data)
    source = box_position(data, names).copy()
    permission_reads: list[str] = []

    def read_permission() -> str:
        value = permissions[min(len(permission_reads), len(permissions) - 1)]
        permission_reads.append(value)
        if value == "LEDGER_ERROR":
            raise TimeoutError("simulated permission ledger timeout")
        return value

    phases, revision, outcome = execute_transfer(
        model, data, names, permission="GRANTED", revision=0, gate_enabled=True,
        permission_reader=read_permission,
    )
    recovery = {"status": "not_applicable", "authority": recovery_authority,
                "phases": [], "reason": "task_transfer_not_blocked_after_commit"}
    if outcome.get("status") == "blocked" and outcome.get("reason") == "permission_not_granted_before_place":
        recovery = recover_to_source(model, data, names, source, recovery_authority)

    final = box_position(data, names)
    final_permission = permission_reads[-1] if permission_reads else "UNKNOWN"
    final_obs = observation(data, names, final_permission, revision)
    final_gripper = gripper_contact(model, data, names)
    table_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, SOURCE_TABLE)
    tray_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, TRAY_FLOOR)
    source_contact = geom_contact(model, data, names["box_geom"], table_id)
    tray_contact = geom_contact(model, data, names["box_geom"], tray_id)
    return {
        "case_id": case_id,
        "task_permission_schedule": permissions,
        "recovery_authority": recovery_authority,
        "permission_checks": outcome.get("permission_checks", []),
        "transfer_outcome": outcome.get("status"),
        "transfer_block_reason": outcome.get("reason"),
        "transfer_phases": [p["phase"] for p in phases],
        "recovery": recovery,
        "initial_object_position_m": np.round(source, 4).tolist(),
        "final_object_position_m": np.round(final, 4).tolist(),
        "object_on_source": final_obs["object"]["on_source_table"],
        "object_in_target": final_obs["target"]["box_in_target"],
        "bilateral_gripper_contact": all(final_gripper.values()),
        "source_table_contact": source_contact,
        "tray_floor_contact": tray_contact,
        "any_verified_support_contact": source_contact or tray_contact,
        "task_complete": final_obs["target"]["box_in_target"],
        "simulated_seconds": round(float(data.time), 4),
        "final_revision": revision,
    }


def create_figure(cases: list[dict], output_stem: Path) -> list[Path]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, axes = new_figure(1, 2, panel=(7.0, 4.8), gridspec_kw={"width_ratios": [1.15, 1]})
    ax_flow, ax_matrix = axes[0]
    ax_flow.set_title("A  撤回后的受限恢复路径", loc="left", color=PALETTE["ink"])
    ax_flow.set_xlim(0, 1); ax_flow.set_ylim(0, 1); ax_flow.axis("off")
    flow = [
        (0.03, 0.58, 0.20, 0.20, "任务授权\nGRANTED", PALETTE["blue_main"]),
        (0.28, 0.58, 0.20, 0.20, "转移中\n撤回", PALETTE["red_strong"]),
        (0.53, 0.58, 0.20, 0.20, "恢复权限\nRECOVERY_ONLY", PALETTE["blue_secondary"]),
        (0.78, 0.58, 0.19, 0.20, "返回源位\n验证支撑", PALETTE["green_3"]),
    ]
    for x, y, w, h, label, color in flow:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.025",
                             linewidth=1.5, edgecolor=color, facecolor=PALETTE["white"])
        ax_flow.add_patch(box)
        ax_flow.text(x + w/2, y + h/2, label, ha="center", va="center",
                     fontsize=10, color=PALETTE["ink"])
    for x0, x1 in ((0.23, 0.28), (0.48, 0.53), (0.73, 0.78)):
        ax_flow.annotate("", xy=(x1-0.008, 0.68), xytext=(x0+0.008, 0.68),
                         arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": PALETTE["neutral_dark"]})
    ax_flow.text(0.5, 0.37, "任务权限撤回后，不再提交目标转移。\n仅在独立恢复权限明确时执行预定义回退。",
                 ha="center", va="center", fontsize=10, color=PALETTE["ink_soft"])
    ax_flow.text(0.5, 0.12, "恢复终态：回到记录源位 · 桌面接触 · 夹爪释放 · 目标未完成",
                 ha="center", va="center", fontsize=9, color=PALETTE["ink_soft"])

    ax_matrix.set_title("B  单次仿真终态（每条件 n=1）", loc="left", color=PALETTE["ink"])
    columns = ["抓取前\n撤回", "晚撤回\n无权限", "晚撤回\n权限未知", "晚撤回\n恢复许可", "持续\n授权"]
    rows = ["任务目标完成", "物体在源位", "夹爪仍夹持", "有支撑接触"]
    values = [
        [c["task_complete"], c["object_on_source"], c["bilateral_gripper_contact"],
         c["any_verified_support_contact"]] for c in cases
    ]
    values = np.asarray(values, dtype=bool).T
    ax_matrix.set_xlim(-0.5, len(columns)-0.5); ax_matrix.set_ylim(len(rows)-0.5, -0.5)
    ax_matrix.set_xticks(range(len(columns)), columns)
    ax_matrix.set_yticks(range(len(rows)), rows)
    ax_matrix.tick_params(axis="both", length=0, labelsize=9)
    for spine in ax_matrix.spines.values():
        spine.set_visible(False)
    for r, row in enumerate(rows):
        for c, _ in enumerate(columns):
            positive = bool(values[r, c])
            adverse = row == "夹爪仍夹持" and positive
            color = PALETTE["red_strong"] if adverse else (
                PALETTE["green_3"] if positive else PALETTE["neutral"])
            ax_matrix.scatter(c, r, s=450, marker="s", color=color,
                              edgecolor=PALETTE["black"], linewidth=0.6, zorder=2)
            ax_matrix.text(c, r, "是" if positive else "否", ha="center", va="center",
                           fontsize=9, color=PALETTE["black"], zorder=3)
    ax_matrix.set_xticks(np.arange(-0.5, len(columns), 1), minor=True)
    ax_matrix.set_yticks(np.arange(-0.5, len(rows), 1), minor=True)
    ax_matrix.grid(which="minor", color=PALETTE["white"], linewidth=1.4)
    ax_matrix.tick_params(which="minor", length=0)
    fig.tight_layout(pad=1.2, rect=(0, 0.09, 1, 1))
    fig.text(0.5, 0.025,
             "MuJoCo 3.4.0 / Panda；RECOVERY_ONLY 为任务授权之外、仿真开始前配置的恢复权限。单场景机制试验，不作统计推断。",
             ha="center", fontsize=9, color=PALETTE["ink_soft"])
    return finalize_figure(fig, output_stem, formats=("png", "pdf"), dpi=300, tight=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_id = parser.parse_args().run_id
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("--run-id may contain only letters, numbers, underscores, and hyphens")
    out_json = RESULTS / f"revocation-recovery-experiment-{run_id}.json"
    out_figure = FIGURES / f"pol2-revocation-recovery-{run_id}"
    if out_json.exists() or out_figure.with_suffix(".png").exists() or out_figure.with_suffix(".pdf").exists():
        raise FileExistsError(f"Refusing to overwrite existing experiment output: {run_id}")

    cases = [
        run_case("revoked_before_grasp", ["GRANTED", "DENIED"], "RECOVERY_ONLY"),
        run_case("revoked_before_place_recovery_denied", ["GRANTED", "GRANTED", "DENIED"], "DENIED"),
        run_case("revoked_before_place_recovery_unknown", ["GRANTED", "GRANTED", "DENIED"], "UNKNOWN"),
        run_case("revoked_before_place_recovery_only", ["GRANTED", "GRANTED", "DENIED"], "RECOVERY_ONLY"),
        run_case("continuous_task_grant_control", ["GRANTED"], "DENIED"),
    ]
    for case in cases:
        case["expected_mechanism_outcome"] = (
            case["object_on_source"] and case["source_table_contact"]
            and not case["bilateral_gripper_contact"] and not case["object_in_target"]
            if case["case_id"] == "revoked_before_place_recovery_only"
            else case["object_in_target"] and case["tray_floor_contact"]
            and not case["bilateral_gripper_contact"]
            if case["case_id"] == "continuous_task_grant_control"
            else case["object_on_source"] and case["source_table_contact"]
            and not case["bilateral_gripper_contact"]
            if case["case_id"] == "revoked_before_grasp"
            else case["bilateral_gripper_contact"] and not case["object_in_target"]
            if case["case_id"] in ("revoked_before_place_recovery_denied",
                                    "revoked_before_place_recovery_unknown")
            else False
        )
    figure_paths = create_figure(cases, out_figure)
    result = {
        "experiment": "Bounded recovery after task-permission revocation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": platform.python_version(), "mujoco": mujoco.__version__},
        "robot": "Franka Emika Panda (MuJoCo Menagerie)",
        "task_policy": "pol2-embodied-contract-v0.2",
        "task_policy_sha256": POLICY_SHA256,
        "recovery_policy": POLICY_ID,
        "recovery_policy_sha256": hashlib.sha256(
            (HERE / "pol2-embodied-recovery-policy-v0.1.json").read_bytes()).hexdigest(),
        "experiment_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "design": "five deterministic single-trajectory conditions in one fixed scene; independent task and recovery authorities",
        "conditions_n": {c["case_id"]: 1 for c in cases},
        "cases": cases,
        "summary": {
            "recovery_only_authority_restored_source": cases[3]["recovery"]["status"] == "recovery_succeeded"
            and cases[3]["object_on_source"] and cases[3]["source_table_contact"]
            and not cases[3]["bilateral_gripper_contact"] and not cases[3]["object_in_target"],
            "task_goal_was_not_completed_after_revocation_recovery": not cases[3]["task_complete"],
            "unknown_recovery_authority_issued_no_recovery_motion":
                cases[2]["recovery"]["status"] == "recovery_unavailable"
                and not cases[2]["recovery"]["phases"],
            "denied_recovery_authority_issued_no_recovery_motion":
                cases[1]["recovery"]["status"] == "recovery_unavailable"
                and not cases[1]["recovery"]["phases"],
            "continuous_grant_control_completed_target": cases[4]["task_complete"],
            "all_expected_mechanisms_observed": all(c["expected_mechanism_outcome"] for c in cases),
        },
        "limits": [
            "one deterministic trajectory per condition; no statistical inference",
            "fixed, obstacle-free scene and privileged simulator state; no perception or asynchronous revocation",
            "recovery-only authority is a synthetic machine policy input, not a real permission service",
            "no force/torque bounds or actuator-failure injection; no claim of real-robot safety",
        ],
        "figures": [str(p.relative_to(ROOT)).replace("\\", "/") for p in figure_paths],
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(out_json), "figures": [str(p) for p in figure_paths],
                      "summary": result["summary"],
                      "cases": [{k: c[k] for k in ("case_id", "transfer_outcome", "recovery_authority",
                                                    "recovery", "object_on_source", "object_in_target",
                                                    "bilateral_gripper_contact", "source_table_contact",
                                                    "tray_floor_contact", "task_complete",
                                                    "expected_mechanism_outcome")} for c in cases]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
