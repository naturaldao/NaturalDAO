"""Reproduce the PoL2 recovery figure from its JSON and deterministic MuJoCo scene."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "PoL-Governance" / "benchmark" / "embodied_reasoning"
STYLE_ROOT = ROOT / "PoL-Governance" / "Research" / "PoL2-DAO-Governance-Lab" / "src"
sys.path[:0] = [str(BENCH), str(STYLE_ROOT)]

from pol2dao.plotstyle import FigureStyle, PALETTE, finalize_figure, new_figure  # noqa: E402
from run_mujoco_typed_pick_place import (  # noqa: E402
    box_position,
    build_scene,
    execute_transfer,
    gripper_contact,
    observation,
)
from run_revocation_recovery_experiment import (  # noqa: E402
    CARRY_Z,
    TRAY_XY,
    recover_to_source,
)

CONDITION_ORDER = [
    "revoked_before_grasp",
    "revoked_before_place_recovery_denied",
    "revoked_before_place_recovery_unknown",
    "revoked_before_place_recovery_only",
    "continuous_task_grant_control",
]
CONDITION_LABELS = ["抓取前\n撤回", "晚撤回\n无权限", "晚撤回\n未知权限",
                    "晚撤回\n恢复许可", "持续\n授权"]
OUTCOME_ROWS = [
    ("目标谓词成立", "task_complete", False),
    ("物体返回源位", "object_on_source", False),
    ("夹爪仍夹持物体", "bilateral_gripper_contact", True),
    ("物体有支撑接触", "any_verified_support_contact", False),
]


def replay_terminal_state(permissions: list[str], recovery_authority: str):
    """Replay one deterministic condition to obtain an actual rendered state."""
    model, data, names = build_scene()
    mujoco.mj_forward(model, data)
    for _ in range(250):
        mujoco.mj_step(model, data)
    source = box_position(data, names).copy()
    reads: list[str] = []

    def read_permission() -> str:
        value = permissions[min(len(reads), len(permissions) - 1)]
        reads.append(value)
        return value

    phases, _, outcome = execute_transfer(
        model, data, names, permission="GRANTED", revision=0,
        gate_enabled=True, permission_reader=read_permission,
    )
    del phases
    if outcome.get("status") == "blocked" and outcome.get("reason") == "permission_not_granted_before_place":
        recover_to_source(model, data, names, source, recovery_authority)
    return model, data, names


def render_terminal_image(permissions: list[str], recovery_authority: str) -> np.ndarray:
    model, data, _ = replay_terminal_state(permissions, recovery_authority)
    model.vis.headlight.ambient[:] = [0.48, 0.48, 0.48]
    model.vis.headlight.diffuse[:] = [0.55, 0.55, 0.55]
    model.vis.headlight.specular[:] = [0.12, 0.12, 0.12]
    floor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "demo_floor")
    model.geom_rgba[floor_id] = [0.93, 0.94, 0.96, 1.0]
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=480, width=640)
    camera = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(camera)
    camera.lookat[:] = [0.48, -0.05, 0.38]
    camera.distance = 1.25
    camera.azimuth = 140
    camera.elevation = -28
    renderer.update_scene(data, camera=camera)
    renderer.scene.framergb[:] = [0.97, 0.97, 0.97]
    image = renderer.render().copy()
    renderer.close()
    return image


def draw_flow(ax, image_recovered: np.ndarray, image_unresolved: np.ndarray) -> None:
    from matplotlib.patches import FancyBboxPatch

    ink, soft = PALETTE["ink"], PALETTE["ink_soft"]
    nodes = [
        (0.025, "执行中\nGRANTED", PALETTE["blue_main"]),
        (0.275, "授权撤回\nDENIED", PALETTE["red_strong"]),
        (0.525, "阻断目标放置\n物体仍被夹持", PALETTE["neutral_dark"]),
        (0.775, "检查独立恢复权限", PALETTE["blue_secondary"]),
    ]
    for x, label, edge in nodes:
        node = FancyBboxPatch((x, 0.80), 0.20, 0.15,
                              boxstyle="round,pad=0.008,rounding_size=0.012",
                              linewidth=1.0, edgecolor=edge, facecolor=PALETTE["white"])
        ax.add_patch(node)
        ax.text(x + 0.10, 0.875, label, ha="center", va="center", fontsize=9.0,
                color=ink, linespacing=1.1)
    for x in (0.225, 0.475, 0.725):
        ax.annotate("", xy=(x + 0.045, 0.875), xytext=(x, 0.875),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": soft})

    # A connected fork terminates in rendered MuJoCo states, not illustrative icons.
    ax.plot([0.875, 0.875, 0.255], [0.80, 0.68, 0.68], color=soft, lw=1.0)
    ax.annotate("", xy=(0.255, 0.59), xytext=(0.255, 0.68),
                arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": PALETTE["green_3"]})
    ax.annotate("", xy=(0.755, 0.59), xytext=(0.755, 0.68),
                arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": PALETTE["red_strong"]})

    cards = [
        (0.035, "RECOVERY_ONLY", image_recovered,
         "回到源位并释放；目标任务仍未完成", PALETTE["green_3"]),
        (0.525, "DENIED / UNKNOWN", image_unresolved,
         "不发恢复动作；物体保持悬持", PALETTE["red_strong"]),
    ]
    for x, title, image, note, edge in cards:
        card = FancyBboxPatch((x, 0.035), 0.44, 0.55,
                              boxstyle="round,pad=0.008,rounding_size=0.012",
                              linewidth=1.0, edgecolor=edge, facecolor=PALETTE["white"])
        ax.add_patch(card)
        ax.text(x + 0.015, 0.545, title, ha="left", va="center", fontsize=9.0,
                fontweight="bold", color=edge)
        image_ax = ax.inset_axes([x + 0.015, 0.13, 0.41, 0.31])
        image_ax.imshow(image, aspect="auto")
        image_ax.set_xticks([])
        image_ax.set_yticks([])
        for spine in image_ax.spines.values():
            spine.set_color(PALETTE["neutral"])
            spine.set_linewidth(0.6)
        ax.text(x + 0.015, 0.075, note, ha="left", va="center", fontsize=8.1, color=soft)


def draw_matrix(ax, cases: list[dict]) -> None:
    from matplotlib.patches import Rectangle

    ink, soft = PALETTE["ink"], PALETTE["ink_soft"]
    by_id = {case["case_id"]: case for case in cases}
    ordered = [by_id[name] for name in CONDITION_ORDER]
    matrix = np.asarray([[bool(case[key]) for case in ordered]
                         for _, key, _ in OUTCOME_ROWS], dtype=bool)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    centers = np.linspace(0.43, 0.95, len(CONDITION_LABELS))
    header_y, row_ys = 0.84, [0.64, 0.45, 0.26, 0.07]
    for x, label in zip(centers, CONDITION_LABELS):
        ax.text(x, header_y, label, ha="center", va="center", fontsize=8.1,
                color=ink, linespacing=1.08)
        ax.text(x, header_y - 0.105, "n=1", ha="center", va="center", fontsize=7.2, color=soft)
    for i, ((label, _, adverse_if_true), y) in enumerate(zip(OUTCOME_ROWS, row_ys)):
        ax.text(0.015, y, label, ha="left", va="center", fontsize=8.8, color=ink)
        if i < len(row_ys) - 1:
            ax.plot([0.015, 0.985], [y - 0.095, y - 0.095], color=PALETTE["neutral"], lw=0.55)
        for j, x in enumerate(centers):
            value = bool(matrix[i, j])
            if value and adverse_if_true:
                face, edge, color = PALETTE["red_1"], PALETTE["red_strong"], PALETTE["red_strong"]
            elif value:
                face, edge, color = PALETTE["green_1"], PALETTE["green_3"], ink
            else:
                face, edge, color = PALETTE["white"], PALETTE["neutral"], soft
            ax.add_patch(Rectangle((x - 0.036, y - 0.043), 0.072, 0.086,
                                   facecolor=face, edgecolor=edge, linewidth=0.75))
            ax.text(x, y, "是" if value else "否", ha="center", va="center", fontsize=8.3, color=color)


def render(result_path: Path, output_stem: Path) -> list[Path]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    cases = {case["case_id"]: case for case in result["cases"]}
    images = {
        "recovered": render_terminal_image(
            ["GRANTED", "GRANTED", "DENIED"], "RECOVERY_ONLY"),
        "unresolved": render_terminal_image(
            ["GRANTED", "GRANTED", "DENIED"], "DENIED"),
    }
    # Validate the image-generating replay against the saved terminal-state record.
    replay_specs = [
        ("revoked_before_place_recovery_only", ["GRANTED", "GRANTED", "DENIED"], "RECOVERY_ONLY"),
        ("revoked_before_place_recovery_denied", ["GRANTED", "GRANTED", "DENIED"], "DENIED"),
    ]
    for case_id, permissions, authority in replay_specs:
        model, data, names = replay_terminal_state(permissions, authority)
        got = observation(data, names, "DENIED", 0)
        expected = cases[case_id]
        matches = (
            bool(got["target"]["box_in_target"]) == bool(expected["task_complete"])
            and bool(got["object"]["on_source_table"]) == bool(expected["object_on_source"])
            and bool(all(gripper_contact(model, data, names).values())) == bool(expected["bilateral_gripper_contact"])
        )
        if not matches:
            raise ValueError(f"render replay diverges from saved result for {case_id}")

    compact = FigureStyle(font_size=10, axes_linewidth=0.9)
    fig, axes = new_figure(2, 1, panel=(8.4, 3.7), style=compact,
                           gridspec_kw={"height_ratios": [1.08, 0.92]})
    flow_ax, matrix_ax = axes[:, 0]
    for ax in axes[:, 0]:
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
    flow_ax.set_title("A  授权撤回后的物理状态与恢复分支", loc="left", color=PALETTE["ink"], pad=5)
    draw_flow(flow_ax, images["recovered"], images["unresolved"])
    matrix_ax.set_title("B  五个仿真条件的终态谓词", loc="left", color=PALETTE["ink"], pad=5)
    draw_matrix(matrix_ax, result["cases"])
    fig.tight_layout(pad=0.7, h_pad=0.4)
    return finalize_figure(fig, output_stem, formats=("png", "pdf"), dpi=300, tight=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path, help="path to experiment JSON")
    parser.add_argument("--output-stem", required=True, type=Path, help="output path without extension")
    args = parser.parse_args()
    print("\n".join(map(str, render(args.result, args.output_stem))))


if __name__ == "__main__":
    main()
