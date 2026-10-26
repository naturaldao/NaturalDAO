"""Inject permission revocation at MuJoCo action boundaries.

This fault-injection experiment checks both whether the gate notices a live
authorization change and what physical state the arm leaves when it does.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco

from run_mujoco_typed_pick_place import (
    build_scene,
    box_position,
    execute_transfer,
    gripper_contact,
    observation,
    POLICY_SHA256,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = HERE / "results"
FIGURES = ROOT / "Research" / "figures"


def run_case(name: str, permissions: list[str]) -> dict:
    model, data, names = build_scene()
    for _ in range(250):
        mujoco.mj_step(model, data)
    initial = box_position(data, names).copy()
    permission_reads: list[str] = []

    def read_permission() -> str:
        index = len(permission_reads)
        value = permissions[min(index, len(permissions) - 1)]
        permission_reads.append(value)
        if value == "LEDGER_ERROR":
            raise TimeoutError("simulated permission-ledger read timeout")
        return value

    phases, revision, outcome = execute_transfer(
        model, data, names, permission="GRANTED", revision=0, gate_enabled=True,
        permission_reader=read_permission,
    )
    final = box_position(data, names)
    final_obs = observation(data, names, permission_reads[-1], revision)
    contact = gripper_contact(model, data, names)
    moved = float(((final - initial) ** 2).sum() ** 0.5) > 0.01
    return {
        "case": name,
        "permission_schedule": permissions,
        "permission_checks": outcome.get("permission_checks", []),
        "permission_reader_values": permission_reads,
        "outcome": outcome["status"],
        "reason": outcome.get("reason"),
        "phase_names": [phase["phase"] for phase in phases],
        "initial_box_position_m": [round(float(x), 4) for x in initial],
        "final_box_position_m": [round(float(x), 4) for x in final],
        "box_moved_more_than_1cm": moved,
        "box_on_source": final_obs["object"]["on_source_table"],
        "box_in_target": final_obs["target"]["box_in_target"],
        "gripper_contact": contact,
        "object_still_held": all(contact.values()),
        "simulated_seconds": round(float(data.time), 4),
        "revision": revision,
    }


def make_figure(cases: list[dict], output: Path) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Noto Sans CJK SC", "Arial", "DejaVu Sans"],
        "figure.facecolor": "#F6F8FB", "axes.facecolor": "#F6F8FB",
        "axes.spines.top": False, "axes.spines.right": False,
        "text.color": "#17324D", "axes.titleweight": "bold", "axes.titlesize": 13,
    })
    navy, teal, coral, gray = "#17324D", "#168C8C", "#D95D50", "#718096"
    fig, axes = plt.subplots(2, 1, figsize=(12, 6.2), constrained_layout=True)
    fig.suptitle("PoL2 执行闭环扩展：授权撤回时的动作边界", fontsize=18,
                 color=navy, fontweight="bold")
    labels = [
        ("授权在接触前撤回", cases[0], ["授权有效", "移动到预抓取位", "复验发现撤回", "停止；物体仍在源位"]),
        ("搬运到目标上方后、放置前撤回", cases[1], ["授权有效", "接近并抓取", "抬升并搬运", "复验发现撤回", "停止；物体仍被夹持"]),
    ]
    for ax, (title, row, steps) in zip(axes, labels):
        ax.set_title(title, loc="left", color=navy)
        ax.set_xlim(-0.16, len(steps) - 0.35); ax.set_ylim(-0.65, 0.75)
        ax.set_yticks([]); ax.set_xticks(range(len(steps)), steps)
        ax.tick_params(axis="x", labelsize=9, pad=9)
        ax.axhline(0, color="#CBD5E0", lw=2, zorder=0)
        stop_index = next((i for i, s in enumerate(steps) if "复验发现" in s), len(steps)-1)
        for i, step in enumerate(steps):
            color = coral if i >= stop_index else teal
            ax.scatter(i, 0, s=125, color=color, edgecolor="white", linewidth=1.5, zorder=3)
        text = ("物体未移动" if not row["box_moved_more_than_1cm"]
                else "物体已离开源位；仍被夹持")
        ax.text(0.99, 0.77, text, transform=ax.transAxes, ha="right", va="top",
                color=coral if row["object_still_held"] else teal,
                fontsize=10, fontweight="bold")
        ax.grid(axis="x", alpha=0.12)
    fig.text(0.5, -0.02,
             "同一 MuJoCo Panda 控制器；撤回发生在指定机器检查点。每种故障注入 n=1，结果用于定位闭环缺口。",
             ha="center", fontsize=9, color=gray)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_id = parser.parse_args().run_id
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("--run-id may contain only letters, numbers, underscores, and hyphens")
    out_json = RESULTS / f"permission-revocation-experiment-{run_id}.json"
    out_png = FIGURES / f"pol2-permission-revocation-{run_id}.png"
    if out_json.exists() or out_png.exists():
        raise FileExistsError(f"Refusing to overwrite existing experiment output: {run_id}")

    cases = [
        run_case("revoked_after_approach_before_grasp", ["GRANTED", "DENIED"]),
        run_case("revoked_at_pre_place_check", ["GRANTED", "GRANTED", "DENIED"]),
        run_case("ledger_read_failure_before_grasp", ["GRANTED", "LEDGER_ERROR"]),
        run_case("control_permission_remains_granted", ["GRANTED"]),
    ]
    for case in cases:
        case["interpretation"] = (
            "revocation_detected_before_object_contact; object remains at source"
            if case["case"] == "revoked_after_approach_before_grasp" and not case["box_moved_more_than_1cm"]
            else "ledger read error became UNKNOWN; motion stopped before object contact"
            if case["case"] == "ledger_read_failure_before_grasp" and not case["box_moved_more_than_1cm"]
            else "revocation detected, but object remains held after lift/transport; recovery is not implemented"
            if case["case"] == "revoked_at_pre_place_check" and case["object_still_held"]
            else "positive control completes under continuously granted permission"
            if case["case"] == "control_permission_remains_granted" and case["box_in_target"]
            else "observed state did not match the expected boundary outcome"
        )
    result = {
        "experiment": "PoL2 embodied permission-revocation boundary fault injection",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": platform.python_version(), "mujoco": mujoco.__version__},
        "policy": "pol2-embodied-contract-v0.2",
        "policy_sha256": POLICY_SHA256,
        "robot": "Franka Emika Panda (MuJoCo Menagerie)",
        "design": "one deterministic trajectory per permission schedule; checks at transfer start, pre-grasp, and pre-place",
        "cases": cases,
        "summary": {
            "pre_grasp_revocation_prevented_box_motion": not cases[0]["box_moved_more_than_1cm"],
            "pre_place_revocation_detected": cases[1]["outcome"] == "blocked",
            "pre_place_revocation_left_object_held": cases[1]["object_still_held"],
            "ledger_read_failure_failed_closed": cases[2]["outcome"] == "blocked" and not cases[2]["box_moved_more_than_1cm"],
            "continuous_grant_control_completed": cases[3]["box_in_target"],
        },
        "limits": [
            "synthetic permission ledger and synchronous fault injection; no natural-language or visual sensing",
            "one trajectory per schedule; no statistical inference",
            "the injected revocation is observed at its named checkpoint, not asynchronously at every physics step",
            "rollback/recovery after in-flight revocation is not implemented",
        ],
        "figure": str(out_png.relative_to(ROOT)).replace("\\", "/"),
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    make_figure(cases, out_png)
    print(json.dumps({"json": str(out_json), "figure": str(out_png),
                      "summary": result["summary"],
                      "cases": [{k: c[k] for k in ("case", "outcome", "reason", "box_moved_more_than_1cm",
                                                      "box_on_source", "box_in_target", "object_still_held",
                                                      "permission_checks") } for c in cases]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
