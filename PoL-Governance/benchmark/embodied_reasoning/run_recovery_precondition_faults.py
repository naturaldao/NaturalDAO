"""Probe recovery-policy boundaries under execution and record faults.

All faults are injected only in MuJoCo. The sweep is a deterministic mechanism
pilot (one trajectory per layout and fault), not a safety-rate estimate.
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
sys.path.insert(0, str(HERE))
import run_revocation_recovery_experiment as recovery_module  # noqa: E402
from run_mujoco_typed_pick_place import (  # noqa: E402
    POLICY_SHA256, box_position, build_scene, execute_transfer, gripper_contact,
    move_hand, set_gripper,
)

LAYOUTS = {
    "left_near": [0.515, -0.035],
    "center": [0.550, 0.000],
    "right_near": [0.585, 0.035],
}
CONDITIONS = ("valid_recovery", "carry_pose_drift", "grasp_loss", "stale_source_record", "post_completion")
TRAY_XY = np.array([0.43, -0.24])
CARRY_Z = 0.625


def run_case(layout_id: str, xy: list[float], condition: str) -> dict:
    model, data, names = build_scene()
    data.qpos[names["box_qpos"]:names["box_qpos"] + 3] = [xy[0], xy[1], 0.422]
    mujoco.mj_forward(model, data)
    for _ in range(250):
        mujoco.mj_step(model, data)
    initial_source = box_position(data, names).copy()
    source_for_recovery = initial_source.copy()
    permissions = ["GRANTED"] if condition == "post_completion" else ["GRANTED", "GRANTED", "DENIED"]
    reads: list[str] = []
    fault: dict = {"type": "none", "injection_checkpoint": None}
    phases: list[dict] = []
    revision = 0

    def permission_reader() -> str:
        nonlocal source_for_recovery
        value = permissions[min(len(reads), len(permissions) - 1)]
        reads.append(value)
        if len(reads) == 3 and condition == "carry_pose_drift":
            move_hand(model, data, names, [float(TRAY_XY[0] + 0.07), float(TRAY_XY[1]), CARRY_Z],
                      "fault_injected_carry_pose_drift", phases)
            fault.update({"type": "end_effector_displaced_by_0_07m", "injection_checkpoint": "before_place"})
        elif len(reads) == 3 and condition == "grasp_loss":
            # Model an actuator/grasp failure at the commitment boundary. The
            # object is already above the delivery tray when it is released.
            set_gripper(model, data, names, control=255)
            for _ in range(240):
                mujoco.mj_step(model, data)
            fault.update({"type": "gripper_open_fault_over_target", "injection_checkpoint": "before_place",
                          "agent_release_command": False})
        return value

    phases, revision, transfer = execute_transfer(
        model, data, names, permission="GRANTED", revision=0, gate_enabled=True,
        permission_reader=permission_reader,
    )
    authority = "RECOVERY_ONLY"
    if condition == "stale_source_record":
        source_for_recovery = np.array([0.95, 0.0, initial_source[2]])
        fault = {"type": "source_record_outside_workspace", "recorded_source_xy_m": [0.95, 0.0],
                 "injection_checkpoint": "recovery_dispatch"}
    recovery = {"status": "not_applicable", "authority": authority, "phases": []}
    if condition == "post_completion":
        recovery = recovery_module.recover_to_source(model, data, names, initial_source, authority)
        fault = {"type": "adversarial_recovery_request_after_task_completion",
                 "injection_checkpoint": "postcondition"}
    elif transfer.get("status") == "blocked" and transfer.get("reason") == "permission_not_granted_before_place":
        recovery = recovery_module.recover_to_source(model, data, names, source_for_recovery, authority)

    final_contacts = gripper_contact(model, data, names)
    source_geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "table")
    source_contact = recovery_module.geom_contact(model, data, names["box_geom"], source_geom)
    final_pos = box_position(data, names)
    permission = reads[-1] if reads else "UNKNOWN"
    terminal = recovery_module.observation(data, names, permission, revision)
    recovery_motion = len(recovery.get("phases", [])) > 0
    expected = {
        "valid_recovery": recovery.get("status") == "recovery_succeeded" and not terminal["target"]["box_in_target"],
        "carry_pose_drift": recovery.get("status") == "recovery_failed" and not recovery_motion
        and recovery.get("preconditions", {}).get("carry_pose_within_0_04m") is False,
        "grasp_loss": recovery.get("status") == "recovery_failed" and not recovery_motion
        and recovery.get("preconditions", {}).get("bilateral_grasp") is False,
        "stale_source_record": recovery.get("status") == "recovery_failed" and not recovery_motion
        and recovery.get("preconditions", {}).get("source_workspace_valid") is False,
        "post_completion": recovery.get("status") == "recovery_failed" and not recovery_motion
        and recovery.get("preconditions", {}).get("target_not_reached") is False,
    }[condition]
    physical_goal = bool(terminal["target"]["box_in_target"])
    authorized_completion = bool(physical_goal and transfer.get("status") == "executed"
                                and permission == "GRANTED")
    return {
        "layout_id": layout_id, "initial_source_xy_m": np.round(initial_source[:2], 4).tolist(),
        "condition": condition, "task_permission_schedule": permissions,
        "task_transfer_outcome": transfer.get("status"), "task_transfer_reason": transfer.get("reason"),
        "injected_fault": fault, "recovery_authority": authority, "recovery": recovery,
        "recovery_motion_issued": recovery_motion,
        "final_object_position_m": np.round(final_pos, 4).tolist(),
        "object_on_source": terminal["object"]["on_source_table"],
        "object_in_target": terminal["target"]["box_in_target"],
        "physical_goal_predicate": physical_goal,
        "authorized_task_completion": authorized_completion,
        "task_complete": authorized_completion,
        "bilateral_gripper_contact": all(final_contacts.values()),
        "source_table_contact": source_contact,
        "expected_mechanism_outcome": bool(expected),
        "simulated_seconds": round(float(data.time), 4),
    }


def make_figure(cases: list[dict], stem: Path) -> list[Path]:
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle
    style_root = ROOT / "PoL-Governance" / "Research" / "PoL2-DAO-Governance-Lab" / "src"
    sys.path.insert(0, str(style_root))
    from pol2dao.plotstyle import PALETTE, finalize_figure, new_figure

    fig, axes = new_figure(1, 2, panel=(6.8, 4.8), gridspec_kw={"width_ratios": [1, 1.15]})
    ax_pre, ax_outcome = axes[0]
    conditions = list(CONDITIONS)
    display = ["合规", "姿态偏移", "夹持丢失", "源位失真", "目标完成"]
    layouts = list(LAYOUTS)
    pre_fields = ["bilateral_grasp", "target_not_reached", "carry_pose_within_0_04m", "source_workspace_valid"]
    pre_labels = ["双侧夹持", "目标未达成", "携带姿态合规", "源位有效"]
    pre_matrix = np.zeros((len(conditions), len(pre_fields)), dtype=int)
    for ri, condition in enumerate(conditions):
        subset = [c for c in cases if c["condition"] == condition]
        for ci, field in enumerate(pre_fields):
            pre_matrix[ri, ci] = sum(bool(c["recovery"]["preconditions"].get(field, False)) for c in subset)
    ax_pre.set_title("A  恢复准入前置条件（每行 n=3）", loc="left", color=PALETTE["ink"])
    ax_pre.imshow(pre_matrix / 3.0, cmap=ListedColormap([PALETTE["red_1"], PALETTE["green_3"]]),
                  vmin=0, vmax=1, aspect="auto")
    ax_pre.set_yticks(range(len(conditions)), display)
    ax_pre.set_xticks(range(len(pre_fields)), pre_labels, rotation=18, ha="right")
    ax_pre.tick_params(length=0, labelsize=8)
    for ri in range(len(conditions)):
        for ci in range(len(pre_fields)):
            ax_pre.text(ci, ri, f"{pre_matrix[ri, ci]}/3", ha="center", va="center", fontsize=8,
                        color=PALETTE["ink"])
    ax_pre.set_xticks(np.arange(-0.5, len(pre_fields), 1), minor=True)
    ax_pre.set_yticks(np.arange(-0.5, len(conditions), 1), minor=True)
    ax_pre.grid(which="minor", color="white", linewidth=1.2)
    ax_pre.tick_params(which="minor", length=0)

    ax_outcome.set_title("B  物理终态（每列 n=3）", loc="left", color=PALETTE["ink"])
    metrics = ["物理目标占据", "源位成立", "夹爪释放", "源桌接触", "恢复动作已发出"]
    props = ["physical_goal_predicate", "object_on_source", None, "source_table_contact", "recovery_motion_issued"]
    values = np.zeros((len(metrics), len(conditions)), dtype=int)
    for ci, condition in enumerate(conditions):
        subset = [c for c in cases if c["condition"] == condition]
        for ri, prop in enumerate(props):
            values[ri, ci] = sum((not c["bilateral_gripper_contact"] if prop is None else c[prop]) for c in subset)
    ax_outcome.set_xlim(-0.5, len(conditions) - 0.5)
    ax_outcome.set_ylim(len(metrics) - 0.5, -0.5)
    ax_outcome.set_yticks(range(len(metrics)), metrics)
    ax_outcome.set_xticks(range(len(conditions)), display, rotation=20, ha="right")
    ax_outcome.tick_params(length=0, labelsize=8)
    for ri in range(len(metrics)):
        for ci in range(len(conditions)):
            count = values[ri, ci]
            color = (PALETTE["neutral"] if count == 0 else
                     PALETTE["red_strong"] if ri == 0 and count else
                     PALETTE["blue_main"] if ri == 4 and count else PALETTE["green_3"])
            ax_outcome.add_patch(Rectangle((ci - 0.5, ri - 0.5), 1, 1,
                                           facecolor=color, edgecolor=PALETTE["white"], linewidth=1.2))
            ax_outcome.text(ci, ri, f"{count}/3", ha="center", va="center", fontsize=8,
                            color=PALETTE["white"] if color in (PALETTE["red_strong"], PALETTE["blue_main"])
                            else PALETTE["ink"])
    for axis in (ax_pre, ax_outcome):
        for side in axis.spines.values():
            side.set_visible(False)
    fig.text(0.5, 0.015,
             "MuJoCo 3.4.0 / Panda；故障仅为仿真注入。夹持丢失发生在托盘上方，目标谓词因此可能由被动掉落达成。",
             ha="center", fontsize=8, color=PALETTE["ink_soft"])
    return finalize_figure(fig, stem, formats=("png", "pdf"), dpi=300, tight=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_id = parser.parse_args().run_id
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("invalid run id")
    output = RESULTS / f"recovery-precondition-faults-{run_id}.json"
    stem = FIGURES / f"pol2-recovery-precondition-faults-{run_id}"
    if output.exists() or stem.with_suffix(".png").exists() or stem.with_suffix(".pdf").exists():
        raise FileExistsError(f"refusing to overwrite run {run_id}")
    cases = [run_case(layout, xy, condition) for condition in CONDITIONS for layout, xy in LAYOUTS.items()]
    figures = make_figure(cases, stem)
    drop_cases = [c for c in cases if c["condition"] == "grasp_loss"]
    summary = {
        "cases": len(cases),
        "expected_mechanism_outcomes": sum(c["expected_mechanism_outcome"] for c in cases),
        "recovery_successes_valid_condition": sum(c["condition"] == "valid_recovery" and
                                                    c["recovery"]["status"] == "recovery_succeeded" for c in cases),
        "recovery_motion_under_failed_preconditions": sum(c["recovery_motion_issued"] and
            c["condition"] != "valid_recovery" for c in cases),
        "physical_target_predicate_true_after_grasp_loss_fault": sum(c["physical_goal_predicate"] for c in drop_cases),
        "authorized_task_completions_after_revocation": sum(
            c["authorized_task_completion"] for c in cases if c["condition"] != "post_completion"),
        "agent_release_command_during_grasp_loss_injection": False,
    }
    result = {
        "experiment": "Recovery-policy precondition and execution-fault sweep",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": platform.python_version(), "mujoco": mujoco.__version__},
        "robot": "Franka Emika Panda (MuJoCo Menagerie)",
        "task_policy": "pol2-embodied-contract-v0.2", "task_policy_sha256": POLICY_SHA256,
        "recovery_policy": recovery_module.POLICY_ID,
        "recovery_policy_sha256": hashlib.sha256((HERE / "pol2-embodied-recovery-policy-v0.1.json").read_bytes()).hexdigest(),
        "experiment_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "design": "3 deterministic source layouts x 5 precondition/fault conditions; one trajectory per cell; 15 total",
        "source_layouts_xy_m": LAYOUTS,
        "conditions_n": {f"{layout}/{condition}": 1 for condition in CONDITIONS for layout in LAYOUTS},
        "cases": cases, "summary": summary,
        "limits": [
            "single deterministic trajectory per layout-condition cell; no rate or confidence interval inference",
            "faults use privileged MuJoCo interventions and are not realistic fault distributions",
            "grasp-loss test opens the gripper above the delivery tray; passive fall can satisfy the task predicate",
            "no collision force limits, perception uncertainty, asynchronous network/ledger fault or hardware safety claim",
        ],
        "figures": [str(p.relative_to(ROOT)).replace("\\", "/") for p in figures],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(output), "figures": [str(p) for p in figures], "summary": summary,
                      "cases": [{k: c[k] for k in ("layout_id", "condition", "task_transfer_outcome",
                                                   "recovery", "recovery_motion_issued", "physical_goal_predicate",
                                                   "authorized_task_completion",
                                                   "object_on_source", "bilateral_gripper_contact",
                                                   "source_table_contact", "expected_mechanism_outcome")} for c in cases]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
