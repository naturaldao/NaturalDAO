"""Sweep grasp-force derating onset against PoL2 recovery response delay.

The 3x3 timing grid is crossed with three deterministic source layouts. Grip
loss is modeled by reducing the MuJoCo gripper actuator force limit, not by an
agent release command. This is a mechanism pilot, not a hardware reliability
model or statistical estimate.
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
)

LAYOUTS = {
    "left_near": [0.515, -0.035],
    "center": [0.550, 0.000],
    "right_near": [0.585, 0.035],
}
FAULT_ONSETS_S = (0.0, 0.25, 0.75)
RECOVERY_DELAYS_S = (0.0, 0.25, 0.50)
DERATE_DURATION_S = 0.30
DERATE_FLOOR_N = 0.10
TRAY_XY = np.array([0.43, -0.24])
CARRY_Z = 0.625


def geom_contact(model: mujoco.MjModel, data: mujoco.MjData, geom_a: int, geom_b: int) -> bool:
    return any({int(data.contact[i].geom1), int(data.contact[i].geom2)} == {geom_a, geom_b}
               for i in range(data.ncon))


def run_case(layout_id: str, xy: list[float], fault_onset_s: float | None,
             recovery_delay_s: float) -> dict:
    model, data, names = build_scene()
    data.qpos[names["box_qpos"]:names["box_qpos"] + 3] = [xy[0], xy[1], 0.422]
    mujoco.mj_forward(model, data)
    for _ in range(250):
        mujoco.mj_step(model, data)
    source = box_position(data, names).copy()
    actuator_id = names["gripper_actuator"]
    table_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "table")
    tray_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "tray_floor")
    floor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "demo_floor")
    ledger: list[dict] = [{"event": "episode_started", "sim_time_s": round(float(data.time), 5)}]
    permission_reads: list[str] = []
    denial_time: float | None = None
    onset_time: float | None = None
    first_contact_loss: dict | None = None
    first_supported: dict | None = None
    first_physical_goal: dict | None = None
    fault_onset_recorded = False
    last_contact = all(gripper_contact(model, data, names).values())
    original_step = mujoco.mj_step

    def tracked_step(m, d, *args, **kwargs):
        nonlocal first_contact_loss, first_supported, first_physical_goal, last_contact, fault_onset_recorded
        t = float(d.time)
        if onset_time is not None and t >= onset_time:
            if not fault_onset_recorded:
                fault_onset_recorded = True
                ledger.append({"event": "gripper_force_derating_started", "sim_time_s": round(t, 5),
                               "offset_from_revocation_s": round(t - float(denial_time), 5)})
            elapsed = t - onset_time
            fraction = min(max(elapsed / DERATE_DURATION_S, 0.0), 1.0)
            force_limit = 100.0 * (1.0 - fraction) + DERATE_FLOOR_N * fraction
            m.actuator_forcerange[actuator_id] = [-force_limit, force_limit]
        original_step(m, d, *args, **kwargs)
        now = float(d.time)
        contact = all(gripper_contact(m, d, names).values())
        release_command_active = float(d.ctrl[actuator_id]) > 200.0
        fault_active = onset_time is not None and now >= onset_time
        if last_contact and not contact and first_contact_loss is None and fault_active and not release_command_active:
            first_contact_loss = {"event": "bilateral_grasp_lost", "sim_time_s": round(now, 5),
                                  "object_position_m": np.round(box_position(d, names), 4).tolist()}
            ledger.append(first_contact_loss)
        last_contact = contact
        table_support = geom_contact(m, d, names["box_geom"], table_id)
        tray_support = geom_contact(m, d, names["box_geom"], tray_id)
        floor_support = geom_contact(m, d, names["box_geom"], floor_id)
        if (table_support or tray_support or floor_support) and first_supported is None \
                and denial_time is not None and now >= denial_time:
            first_supported = {"event": "object_support_contact", "sim_time_s": round(now, 5),
                               "support": ("source_table" if table_support else
                                           "delivery_tray" if tray_support else "demo_floor"),
                               "object_position_m": np.round(box_position(d, names), 4).tolist()}
            ledger.append(first_supported)
        pos = box_position(d, names)
        in_target = bool(np.linalg.norm(pos[:2] - TRAY_XY, ord=np.inf) < 0.073 and 0.405 <= pos[2] <= 0.49)
        if in_target and first_physical_goal is None and denial_time is not None and now >= denial_time:
            first_physical_goal = {"event": "physical_goal_predicate_became_true", "sim_time_s": round(now, 5),
                                   "object_position_m": np.round(pos, 4).tolist()}
            ledger.append(first_physical_goal)

    def permission_reader() -> str:
        nonlocal denial_time
        result = ("GRANTED", "GRANTED", "DENIED")[min(len(permission_reads), 2)]
        permission_reads.append(result)
        if result == "DENIED":
            denial_time = float(data.time)
            ledger.append({"event": "task_permission_revoked_and_observed", "sim_time_s": round(denial_time, 5),
                           "permission": result, "checkpoint": "before_place"})
        return result

    phases: list[dict] = []
    recovery: dict = {"status": "not_run", "authority": "RECOVERY_ONLY", "phases": []}
    transfer: dict = {}
    try:
        mujoco.mj_step = tracked_step
        phases, revision, transfer = execute_transfer(
            model, data, names, permission="GRANTED", revision=0, gate_enabled=True,
            permission_reader=permission_reader,
        )
        if transfer.get("status") != "blocked" or transfer.get("reason") != "permission_not_granted_before_place":
            raise RuntimeError(f"expected before-place revocation block, got {transfer}")
        if fault_onset_s is not None:
            onset_time = float(denial_time) + fault_onset_s
            ledger.append({"event": "gripper_force_derating_scheduled", "sim_time_s": round(float(data.time), 5),
                           "offset_from_revocation_s": fault_onset_s,
                           "planned_onset_sim_time_s": round(onset_time, 5),
                           "ramp_duration_s": DERATE_DURATION_S, "terminal_force_limit_N": DERATE_FLOOR_N})
        wait_steps = int(round(recovery_delay_s / model.opt.timestep))
        for _ in range(wait_steps):
            mujoco.mj_step(model, data)
        ledger.append({"event": "recovery_dispatch", "sim_time_s": round(float(data.time), 5),
                       "delay_after_revocation_s": recovery_delay_s,
                       "authority": "RECOVERY_ONLY"})
        recovery = recovery_module.recover_to_source(model, data, names, source, "RECOVERY_ONLY")
        # Allow an unresolved object to settle before classifying support. This
        # avoids labeling a transient airborne frame as the terminal outcome.
        for _ in range(int(round(1.0 / model.opt.timestep))):
            mujoco.mj_step(model, data)
    finally:
        mujoco.mj_step = original_step

    final_contacts = gripper_contact(model, data, names)
    final_pos = box_position(data, names)
    terminal = recovery_module.observation(data, names, "DENIED", revision)
    table_support = geom_contact(model, data, names["box_geom"], table_id)
    tray_support = geom_contact(model, data, names["box_geom"], tray_id)
    floor_support = geom_contact(model, data, names["box_geom"], floor_id)
    physical_goal = bool(terminal["target"]["box_in_target"])
    authorized_completion = False  # Every episode's task placement was blocked by the revoked permission.
    audit_required = {"episode_started", "task_permission_revoked_and_observed", "recovery_dispatch"}
    if fault_onset_s is not None:
        audit_required.add("gripper_force_derating_started")
    ledger_types = [event["event"] for event in ledger]
    event_times = [event["sim_time_s"] for event in ledger]
    audit_complete = (audit_required.issubset(set(ledger_types)) and
                      transfer.get("permission_checks", [])[-1]["permission"] == "DENIED" and
                      event_times == sorted(event_times))
    recovery_ok = recovery.get("status") == "recovery_succeeded"
    stable_support = table_support or tray_support or floor_support
    expected = (not phases or "place" not in [p["phase"] for p in phases]) and audit_complete
    return {
        "layout_id": layout_id, "initial_source_xy_m": np.round(source[:2], 4).tolist(),
        "fault_onset_after_revocation_s": fault_onset_s,
        "recovery_dispatch_delay_s": recovery_delay_s,
        "gripper_derating": (None if fault_onset_s is None else {
            "model": "linear reduction of actuator force clamp from 100 N to 0.1 N",
            "ramp_duration_s": DERATE_DURATION_S, "agent_release_command": False,
        }),
        "task_permission_schedule": permission_reads,
        "task_transfer_outcome": transfer.get("status"),
        "task_transfer_reason": transfer.get("reason"),
        "task_phases": [p["phase"] for p in phases],
        "recovery": recovery,
        "recovery_motion_issued": bool(recovery.get("phases")),
        "first_grasp_loss": first_contact_loss,
        "first_support_contact": first_supported,
        "first_physical_goal_event": first_physical_goal,
        "timeline": ledger,
        "audit_event_complete": audit_complete,
        "physical_goal_predicate": physical_goal,
        "authorized_task_completion": authorized_completion,
        "stable_support_at_terminal": bool(stable_support),
        "support_type_at_terminal": ("source_table" if table_support else
                                     "delivery_tray" if tray_support else
                                     "demo_floor" if floor_support else "none"),
        "object_on_source": terminal["object"]["on_source_table"],
        "object_in_target": terminal["target"]["box_in_target"],
        "bilateral_gripper_contact_at_terminal": all(final_contacts.values()),
        "final_object_position_m": np.round(final_pos, 4).tolist(),
        "simulated_seconds": round(float(data.time), 5),
        "expected_mechanism_outcome": bool(expected),
    }


def make_figure(cases: list[dict], stem: Path) -> list[Path]:
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle
    style_root = ROOT / "PoL-Governance" / "Research" / "PoL2-DAO-Governance-Lab" / "src"
    sys.path.insert(0, str(style_root))
    from pol2dao.plotstyle import PALETTE, finalize_figure, new_figure

    fig, axes = new_figure(1, 3, panel=(5.0, 4.8))
    outcomes = [
        ("physical_goal_predicate", "A  撤权后物理目标成立", PALETTE["red_strong"]),
        ("recovery_success", "B  受限恢复成功", PALETTE["green_3"]),
        ("stable_support_at_terminal", "C  终态存在支撑", PALETTE["teal"]),
    ]
    onset_labels = ["0 s", "0.25 s", "0.75 s"]
    delay_labels = ["0 s", "0.25 s", "0.50 s"]
    for ax, (key, title, color) in zip(axes[0], outcomes):
        counts = np.zeros((3, 3), dtype=int)
        for yi, onset in enumerate(FAULT_ONSETS_S):
            for xi, delay in enumerate(RECOVERY_DELAYS_S):
                cells = [c for c in cases if c["fault_onset_after_revocation_s"] == onset
                         and c["recovery_dispatch_delay_s"] == delay]
                if key == "recovery_success":
                    counts[yi, xi] = sum(c["recovery"]["status"] == "recovery_succeeded" for c in cells)
                else:
                    counts[yi, xi] = sum(bool(c[key]) for c in cells)
        ax.set_title(title, loc="left", color=PALETTE["ink"])
        ax.imshow(counts / len(LAYOUTS), cmap=ListedColormap([PALETTE["neutral"], color]),
                  vmin=0, vmax=1, aspect="equal")
        ax.set_xticks(range(3), delay_labels)
        ax.set_yticks(range(3), onset_labels)
        ax.set_xlabel("恢复调度延迟")
        if ax is axes[0][0]:
            ax.set_ylabel("退化起点（撤权后）")
        ax.tick_params(length=0, labelsize=8)
        for yi in range(3):
            for xi in range(3):
                ax.text(xi, yi, f"{counts[yi, xi]}/3", ha="center", va="center", fontsize=9,
                        color=PALETTE["white"] if counts[yi, xi] == 3 and color == PALETTE["red_strong"]
                        else PALETTE["ink"])
        ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
        ax.grid(which="minor", color=PALETTE["white"], linewidth=1.5)
        ax.tick_params(which="minor", length=0)
        for side in ax.spines.values():
            side.set_visible(False)
    fig.text(0.5, 0.02,
             "每格汇总 3 个预设源位（每布局一条）；强度为执行器力限线性衰减至 0.1 N / 0.30 s。非统计成功率。",
             ha="center", fontsize=8, color=PALETTE["ink_soft"])
    return finalize_figure(fig, stem, formats=("png", "pdf"), dpi=300, tight=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_id = parser.parse_args().run_id
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("invalid run id")
    output = RESULTS / f"grip-derating-timing-sweep-{run_id}.json"
    stem = FIGURES / f"pol2-grip-derating-timing-sweep-{run_id}"
    if output.exists() or stem.with_suffix(".png").exists() or stem.with_suffix(".pdf").exists():
        raise FileExistsError(f"refusing to overwrite run {run_id}")
    cases: list[dict] = []
    for onset in FAULT_ONSETS_S:
        for delay in RECOVERY_DELAYS_S:
            for layout, xy in LAYOUTS.items():
                cases.append(run_case(layout, xy, onset, delay))
    # No-derating controls provide the expected recovery baseline at each layout.
    cases.extend(run_case(layout, xy, None, 0.0) for layout, xy in LAYOUTS.items())
    figures = make_figure(cases, stem)
    grid = [c for c in cases if c["fault_onset_after_revocation_s"] is not None]
    summary = {
        "cases_total": len(cases), "timing_grid_cases": len(grid), "no_fault_controls": len(cases) - len(grid),
        "all_task_permissions_denied_before_place": all(c["task_transfer_outcome"] == "blocked" for c in cases),
        "task_place_phase_after_revocation": sum("place" in c["task_phases"] for c in cases),
        "all_audit_ledgers_complete": all(c["audit_event_complete"] for c in cases),
        "authorized_task_completions_after_revocation": sum(c["authorized_task_completion"] for c in cases),
        "physical_goal_predicate_after_revocation": sum(c["physical_goal_predicate"] for c in grid),
        "recovery_successes_timing_grid": sum(c["recovery"]["status"] == "recovery_succeeded" for c in grid),
        "recovery_successes_no_fault_controls": sum(c["recovery"]["status"] == "recovery_succeeded"
                                                     for c in cases if c["fault_onset_after_revocation_s"] is None),
        "stable_support_terminal_timing_grid": sum(c["stable_support_at_terminal"] for c in grid),
        "stable_support_terminal_timing_grid_by_type": {
            support: sum(c["support_type_at_terminal"] == support for c in grid)
            for support in ("source_table", "delivery_tray", "demo_floor", "none")},
        "grasp_loss_events_timing_grid": sum(c["first_grasp_loss"] is not None for c in grid),
    }
    result = {
        "experiment": "Gripper force derating onset versus bounded recovery dispatch delay",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": platform.python_version(), "mujoco": mujoco.__version__},
        "robot": "Franka Emika Panda (MuJoCo Menagerie)",
        "task_policy": "pol2-embodied-contract-v0.2", "task_policy_sha256": POLICY_SHA256,
        "recovery_policy": recovery_module.POLICY_ID,
        "recovery_policy_sha256": hashlib.sha256((HERE / "pol2-embodied-recovery-policy-v0.1.json").read_bytes()).hexdigest(),
        "experiment_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "design": "3 force-fault onset times x 3 recovery dispatch delays x 3 fixed source layouts + 3 no-fault controls; 30 trajectories",
        "fault_onsets_after_revocation_s": list(FAULT_ONSETS_S),
        "recovery_dispatch_delays_s": list(RECOVERY_DELAYS_S),
        "derating": {"initial_actuator_force_limit_N": 100.0, "terminal_force_limit_N": DERATE_FLOOR_N,
                     "duration_s": DERATE_DURATION_S, "profile": "linear ramp",
                     "actor_release_command": False},
        "source_layouts_xy_m": LAYOUTS,
        "cases": cases, "summary": summary,
        "limits": [
            "one deterministic trajectory per timing-layout cell; counts summarize designed cells, not independent random replications",
            "force derating changes the MuJoCo actuator force clamp and is not calibrated to Panda hardware or measured grip force",
            "revocation is synchronous at the before-place policy check; asynchronous network and ledger timing are not modeled",
            "state and contact checks use privileged simulator truth; no perception uncertainty, collision force limits, or real-robot claim",
        ],
        "figures": [str(p.relative_to(ROOT)).replace("\\", "/") for p in figures],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(output), "figures": [str(p) for p in figures], "summary": summary,
                      "timing_grid": [{"onset_s": onset, "dispatch_delay_s": delay,
                                       "physical_target_count": sum(c["physical_goal_predicate"] for c in grid
                                           if c["fault_onset_after_revocation_s"] == onset and c["recovery_dispatch_delay_s"] == delay),
                                       "recovery_success_count": sum(c["recovery"]["status"] == "recovery_succeeded" for c in grid
                                           if c["fault_onset_after_revocation_s"] == onset and c["recovery_dispatch_delay_s"] == delay),
                                       "stable_support_count": sum(c["stable_support_at_terminal"] for c in grid
                                           if c["fault_onset_after_revocation_s"] == onset and c["recovery_dispatch_delay_s"] == delay)}
                                       for onset in FAULT_ONSETS_S for delay in RECOVERY_DELAYS_S]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
