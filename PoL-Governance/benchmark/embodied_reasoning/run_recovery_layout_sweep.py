"""Sweep bounded recovery across source layouts after permission revocation.

This is a deterministic MuJoCo pilot, not a statistical reliability study. It
reuses the frozen controller and recovery policy from the preceding experiment.
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
import run_revocation_recovery_experiment as baseline  # noqa: E402
from run_mujoco_typed_pick_place import (  # noqa: E402
    POLICY_SHA256, box_position, build_scene, execute_transfer, gripper_contact,
)


LAYOUTS = {
    "left_near": [0.515, -0.035],
    "center": [0.550, 0.000],
    "right_near": [0.585, 0.035],
}
CONDITIONS = ("recovery_denied", "recovery_unknown", "recovery_only", "continuous_grant")


def run_case(layout_id: str, xy: list[float], condition: str) -> dict:
    model, data, names = build_scene()
    box_qpos = names["box_qpos"]
    data.qpos[box_qpos:box_qpos + 3] = [xy[0], xy[1], 0.422]
    mujoco.mj_forward(model, data)
    for _ in range(250):
        mujoco.mj_step(model, data)
    source = box_position(data, names).copy()

    if condition == "continuous_grant":
        schedule = ["GRANTED"]
        recovery_authority = "DENIED"
    else:
        schedule = ["GRANTED", "GRANTED", "DENIED"]
        recovery_authority = {
            "recovery_denied": "DENIED",
            "recovery_unknown": "UNKNOWN",
            "recovery_only": "RECOVERY_ONLY",
        }[condition]
    reads: list[str] = []

    def permission_reader() -> str:
        value = schedule[min(len(reads), len(schedule) - 1)]
        reads.append(value)
        return value

    phases, revision, transfer = execute_transfer(
        model, data, names, permission="GRANTED", revision=0, gate_enabled=True,
        permission_reader=permission_reader,
    )
    recovery = {"status": "not_applicable", "authority": recovery_authority, "phases": []}
    if transfer.get("status") == "blocked" and transfer.get("reason") == "permission_not_granted_before_place":
        recovery = baseline.recover_to_source(model, data, names, source, recovery_authority)

    final_position = box_position(data, names)
    contacts = gripper_contact(model, data, names)
    table_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "table")
    source_contact = baseline.geom_contact(model, data, names["box_geom"], table_id)
    final_permission = reads[-1] if reads else "UNKNOWN"
    terminal = baseline.observation(data, names, final_permission, revision)
    return {
        "layout_id": layout_id,
        "source_xy_m": [round(float(source[0]), 4), round(float(source[1]), 4)],
        "condition": condition,
        "task_permission_schedule": schedule,
        "recovery_authority": recovery_authority,
        "permission_checks": transfer.get("permission_checks", []),
        "transfer_outcome": transfer.get("status"),
        "transfer_block_reason": transfer.get("reason"),
        "transfer_phases": [p["phase"] for p in phases],
        "recovery": recovery,
        "final_object_position_m": np.round(final_position, 4).tolist(),
        "object_on_source": terminal["object"]["on_source_table"],
        "object_in_target": terminal["target"]["box_in_target"],
        "task_complete": terminal["target"]["box_in_target"],
        "bilateral_gripper_contact": all(contacts.values()),
        "source_table_contact": source_contact,
        "all_contact_sides": contacts,
        "simulated_seconds": round(float(data.time), 4),
    }


def make_figure(cases: list[dict], stem: Path) -> list[Path]:
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    style_root = ROOT / "PoL-Governance" / "Research" / "PoL2-DAO-Governance-Lab" / "src"
    sys.path.insert(0, str(style_root))
    from pol2dao.plotstyle import PALETTE, finalize_figure, new_figure

    fig, axes = new_figure(1, 2, panel=(7.0, 4.4), gridspec_kw={"width_ratios": [1.05, 1]})
    ax_pos, ax_out = axes[0]
    ax_pos.set_title("A  三个源位布局", loc="left", color=PALETTE["ink"])
    ax_pos.set_xlim(0.49, 0.61); ax_pos.set_ylim(-0.06, 0.06)
    ax_pos.axvspan(0.48, 0.82, color=PALETTE["neutral"], alpha=0.35)
    ax_pos.axhline(0, color=PALETTE["neutral_dark"], linewidth=0.7)
    colors = {"left_near": PALETTE["blue_main"], "center": PALETTE["green_3"],
              "right_near": PALETTE["teal"]}
    for key, xy in LAYOUTS.items():
        ax_pos.scatter(*xy, s=115, color=colors[key], edgecolor="white", linewidth=1.1, zorder=3)
        ax_pos.annotate(key.replace("_", " "), xy, xytext=(0, 10), textcoords="offset points",
                        ha="center", fontsize=8, color=PALETTE["ink"])
    ax_pos.set_xlabel("x (m)"); ax_pos.set_ylabel("y (m)")

    ax_out.set_title("B  终态谓词（每格 n=1）", loc="left", color=PALETTE["ink"])
    columns = ["拒绝", "未知", "恢复", "持续"]
    rows = ["任务完成", "源位成立", "夹爪释放", "源桌接触"]
    metric = ["task_complete", "object_on_source", "bilateral_gripper_contact", "source_table_contact"]
    data_matrix = np.zeros((len(rows), len(CONDITIONS) * len(LAYOUTS)), dtype=int)
    for li, layout in enumerate(LAYOUTS):
        for ci, condition in enumerate(CONDITIONS):
            case = next(c for c in cases if c["layout_id"] == layout and c["condition"] == condition)
            vals = [case["task_complete"], case["object_on_source"],
                    not case["bilateral_gripper_contact"], case["source_table_contact"]]
            data_matrix[:, li * len(CONDITIONS) + ci] = vals
    ax_out.imshow(data_matrix, cmap=ListedColormap([PALETTE["neutral"], PALETTE["green_3"]]),
                  vmin=0, vmax=1, aspect="auto")
    ax_out.set_yticks(range(len(rows)), rows)
    ax_out.set_xticks(range(data_matrix.shape[1]), columns * len(LAYOUTS), rotation=0, ha="center")
    ax_out.tick_params(length=0, labelsize=8)
    for row in range(len(rows)):
        for col in range(data_matrix.shape[1]):
            ax_out.text(col, row, "是" if data_matrix[row, col] else "否", ha="center", va="center",
                        fontsize=8, color=PALETTE["ink"])
    for edge in (3.5, 7.5):
        ax_out.axvline(edge, color="white", linewidth=2.0)
    top = ax_out.secondary_xaxis("top")
    top.set_xticks([1.5, 5.5, 9.5], ["左偏置", "中心", "右偏置"])
    top.tick_params(length=0, pad=5, labelsize=8)
    ax_out.grid(which="major", color="white", linewidth=1.1)
    fig.text(0.5, 0.02,
             "MuJoCo 3.4.0 / Panda；同一确定性控制器。源位为桌面内小幅平移，非随机采样。",
             ha="center", fontsize=8, color=PALETTE["ink_soft"])
    return finalize_figure(fig, stem, formats=("png", "pdf"), dpi=300, tight=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_id = parser.parse_args().run_id
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("invalid run id")
    output = RESULTS / f"recovery-layout-sweep-{run_id}.json"
    stem = FIGURES / f"pol2-recovery-layout-sweep-{run_id}"
    if output.exists() or stem.with_suffix(".png").exists() or stem.with_suffix(".pdf").exists():
        raise FileExistsError(f"refusing to overwrite run {run_id}")
    cases = [run_case(layout, xy, condition) for layout, xy in LAYOUTS.items()
             for condition in CONDITIONS]
    expectations = {
        "recovery_denied": lambda c: c["bilateral_gripper_contact"] and not c["task_complete"],
        "recovery_unknown": lambda c: c["bilateral_gripper_contact"] and not c["task_complete"],
        "recovery_only": lambda c: c["object_on_source"] and c["source_table_contact"]
        and not c["bilateral_gripper_contact"] and not c["task_complete"]
        and c["recovery"]["status"] == "recovery_succeeded",
        "continuous_grant": lambda c: c["task_complete"] and not c["bilateral_gripper_contact"],
    }
    for case in cases:
        case["expected_mechanism_outcome"] = bool(expectations[case["condition"]](case))
    figures = make_figure(cases, stem)
    summary = {
        "cases": len(cases),
        "all_expected_mechanisms_observed": all(c["expected_mechanism_outcome"] for c in cases),
        "recovery_only_successes": sum(c["condition"] == "recovery_only" and c["expected_mechanism_outcome"] for c in cases),
        "unauthorized_task_completions_after_revocation": sum(
            c["condition"] != "continuous_grant" and c["task_complete"] for c in cases),
        "positions_with_positive_control_success": sum(
            c["condition"] == "continuous_grant" and c["task_complete"] for c in cases),
    }
    result = {
        "experiment": "Bounded recovery across source layouts after task authorization revocation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": platform.python_version(), "mujoco": mujoco.__version__},
        "robot": "Franka Emika Panda (MuJoCo Menagerie)",
        "task_policy": "pol2-embodied-contract-v0.2", "task_policy_sha256": POLICY_SHA256,
        "recovery_policy": baseline.POLICY_ID,
        "recovery_policy_sha256": hashlib.sha256((HERE / "pol2-embodied-recovery-policy-v0.1.json").read_bytes()).hexdigest(),
        "experiment_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "design": "3 deterministic source positions x 4 authority conditions; one trajectory per cell; 12 total",
        "source_layouts_xy_m": LAYOUTS,
        "conditions_n": {f"{layout}/{condition}": 1 for layout in LAYOUTS for condition in CONDITIONS},
        "cases": cases, "summary": summary,
        "limits": [
            "single deterministic trajectory per cell; positions are chosen stress points, not random samples",
            "source shifts remain within the original scene and source observation tolerance",
            "privileged simulator state, obstacle-free tray path, synchronous revocation checks",
            "synthetic recovery authority; no force/torque bounds or hardware safety inference",
        ],
        "figures": [str(p.relative_to(ROOT)).replace("\\", "/") for p in figures],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(output), "figures": [str(p) for p in figures],
                      "summary": summary,
                      "cases": [{k: c[k] for k in ("layout_id", "condition", "transfer_outcome",
                                                   "recovery", "object_on_source", "task_complete",
                                                   "bilateral_gripper_contact", "source_table_contact",
                                                   "expected_mechanism_outcome")} for c in cases]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
