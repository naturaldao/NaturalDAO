"""导出前聚合结果检查器（pol-final-eval-aggregate-v1）。

用途：最终评测在库外私有保留集上执行，只允许把**聚合数字**带出隔离环境。
本脚本是导出通道的唯一闸门：读取 finetune/final_eval_aggregate.py 产出的
aggregate.json，按 .agent/notes/2026-10-27-final-eval-package-spec.md 第 2 节
做全部 fail-closed 检查，任一违规即 exit 2。

检查分四层：
1. 结构白名单：只允许 schema 约定的键；允许的数组是 ci95_wilson / ci95 /
   cluster_size_iqr / ci95_item / ci95_group / ece_ci95_group（长度 2 的数字）
   与 bins（长度恰 15 的分箱对象数组）；
2. 禁键：任何键命中 rid/id/prompt/gold/pred/row/sample 等逐例字段模式 → 违规；
3. 值类型与文本：数字有限；字符串必须命中枚举白名单，或 <=64 且只含
   [A-Za-z0-9._#/-]；禁止中文、换行、\\u 转义和超长可打印串；
4. 数值自洽：accuracy == round(correct/total, 6)、CI 包含点估计且单调、
   coverage 与 models 计数一致、分层 total 之和等于 total、paired 与模型一致、
   calibration rows 等于 tuned total、ECE/MCE/NLL/Brier 范围等。

v2 增补（spec「增补 v2」D 节，2026-10-27）：
- paired 允许 completed_only / cluster 子对象；models 允许 evaluated_accuracy；
  coverage.models 允许 completion_rate；calibration.raw / calibrated 允许
  bins / low_sample_bins / low_sample_flag / ece_ci95_group / ece_rounds；
- 这些 v2 键**按出现校验**（不出现就不要求），保证 v1 文档照样通过；一旦出现
  就做完整自洽检查：completion_rate == evaluated/expected_evaluated、
  accuracy_with_missing <= accuracy、cluster.clusters >= 1、cluster.rounds >= 1000、
  cluster.delta == paired.delta、cluster.ci95 含 cluster.delta、
  reliability 与 clusters 阈值（ok/cautious/low）一致、
  bins 恰好 15 箱且 bin 0..14 各一次、low_sample_bins/low_sample_flag 与 bins 一致、
  completed_only.rows <= paired.rows、completed_only 的 ci95_item/ci95_group 含 delta；
- bins 对象的 gap 沿用 calibrate.ece_bins 的**绝对差**口径（|avg_confidence - accuracy|），
  因此这里校验 gap == |accuracy - avg_confidence|（容差 2*TOL，覆盖两边各自 round 6）。

设计取舍：
- 空的分层块 {} 视为 total=0 的层（与 spec 示例 "noul": {} 一致）；
- 固定分层键必须出现（缺层也要以 {} 或 total=0 出现），未知键直接违规；
- models / coverage.models 的键允许是 CLI 标签（安全 token），但必须恰好两个、
  与 paired.base_label / tuned_label 对应；这是 spec「label 可放宽」的落地；
- calibration.status=pending_temperature 允许最小形态 {"status": ...}（温度未拟合时
  final_eval_aggregate 不写其余字段），也允许显式 null；但不允许伪造已拟合数字；
- v2 键 low_sample_bins / low_sample_flag / ci95_item 与禁键正则字面冲突
  （分别命中 sample / item），按**精确键名**豁免；其余同类键仍按逐例字段违规；
- ece_rounds 允许写在 calibration 顶层或 raw/calibrated 块内（spec 只说
  「输出注明 ece_rounds」，落点未定，两处都放行）；
- --json 时通过输出 {"status":"pass","checks":N,"bytes":B}，失败输出
  {"status":"fail","violations":[...]}，两者都保持退出码语义（0/2）。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA_ID = "pol-final-eval-aggregate-v1"
PROTOCOL_ID = "finetune/EVAL-PROTOCOL.md#v1"
DEFAULT_MAX_BYTES = 262144
TOL = 1e-6
# 派生量（两个已 round6 的数字再相减/比较）最多叠加三重舍入误差（1.5e-6），
# 用 1e-6 会把合法产物误判为违规（已实测：delta=0.273871 vs 0.273872）。
DEDUCED_TOL = 3e-6
# 模型标签与 final_eval_aggregate.py 的 LABEL_RE 保持一致（'#' 等字符不得出现在标签里）
LABEL_RE = re.compile(r"[A-Za-z0-9._-]{1,24}")

ROOT_KEYS = ("schema", "protocol", "coverage", "models", "paired", "calibration")
COVERAGE_KEYS = ("view_rows", "skipped", "skipped_total", "expected_evaluated", "models")
# coverage.skipped 的键只能来自已知的跳过原因枚举。否则一个形如
# "db-bigbench-00183cfc#formal_fallacies" 的 rid 可以伪装成"跳过原因"键被带出隔离环境。
SKIPPED_REASONS = frozenset(
    {
        # eval_decision.py --json skipped_stats
        "options_gt_26",
        "prompt_too_long",
        "invalid_answer_idx",
        "missing_prompt",
        "missing_options",
        "token_map_mismatch",
        # build_training_view.py 的 skipped 计数（若评测者传入完整的视图 manifest 统计）
        "drop",
        "no_route",
        "unknown_route",
        "degenerate_soft",
        "no_target",
        "answer_out_of_range",
        "answer_not_in_options",
        # 训练脚本中的跳过原因（保留给未来视图）
        "non_single_token_answer",
        "seq_len_too_short",
    }
)
# v2：coverage.models.<label>.completion_rate = evaluated / expected_evaluated（出现即校验）
COVERAGE_MODEL_KEYS = ("evaluated", "missing", "completion_rate")
COVERAGE_MODEL_REQUIRED_KEYS = ("evaluated", "missing")
MODEL_REQUIRED_KEYS = (
    "total",
    "correct",
    "accuracy",
    "accuracy_ci95_wilson",
    "accuracy_with_missing",
    "missing_rows",
    "by_kind",
    "by_lang",
    "by_option_bucket",
    "by_route",
)
# v2：evaluated_accuracy 是与 accuracy 同值的显式字段（完成子集准确率），出现即校验
MODEL_KEYS = MODEL_REQUIRED_KEYS + ("evaluated_accuracy",)
GROUP_SPECS = (
    ("by_kind", ("choice", "noul", "score")),
    ("by_lang", ("en", "zh")),
    ("by_option_bucket", ("2", "3-4", "5-8", "9-26")),
    ("by_route", ("classification", "distillation")),
)
GROUP_BLOCK_KEYS = ("total", "correct", "accuracy", "ci95_wilson")
PAIRED_REQUIRED_KEYS = (
    "base_label",
    "tuned_label",
    "rows",
    "base_accuracy",
    "tuned_accuracy",
    "delta",
    "ci95",
    "rounds",
    "seed",
    "method",
)
# v2：completed_only 是双方都完成的 rid 交集敏感性分析；cluster 是 group-cluster bootstrap
# scope 说明配对分析的作用域（本轮聚合脚本写 both_completed），作为可选字段放行
PAIRED_KEYS = PAIRED_REQUIRED_KEYS + ("completed_only", "cluster", "scope")
COMPLETED_ONLY_REQUIRED_KEYS = ("rows", "base_accuracy", "tuned_accuracy", "delta", "ci95_group")
COMPLETED_ONLY_KEYS = COMPLETED_ONLY_REQUIRED_KEYS + ("ci95_item", "scope")
CLUSTER_KEYS = (
    "cluster_key",
    "clusters",
    "cluster_size_median",
    "cluster_size_iqr",
    "cluster_size_max",
    "kish_neff",
    "delta",
    "ci95",
    "rounds",
    "method",
    "reliability",
)
BIN_KEYS = ("bin", "count", "avg_confidence", "accuracy", "gap")
BIN_COUNT = 15
LOW_SAMPLE_THRESHOLD = 20
CALIBRATION_KEYS = (
    "status",
    "temperature",
    "fit_half",
    "fit_rows",
    "fit_method",
    "raw",
    "calibrated",
    "accuracy_unchanged",
    "ece_rounds",
)
CALIBRATION_METRIC_REQUIRED_KEYS = ("rows", "accuracy", "nll", "brier", "ece", "mce")
CALIBRATION_METRIC_KEYS = CALIBRATION_METRIC_REQUIRED_KEYS + (
    "bins",
    "low_sample_bins",
    "low_sample_flag",
    "ece_ci95_group",
    "ece_rounds",
)

STATUS_VALUES = ("fitted", "applied", "pending_temperature")
FIT_HALF_VALUES = ("calibration", "selection", "all")
FIT_METHOD_VALUES = ("grid+golden_section_nll",)
PAIRED_METHOD_VALUES = ("paired_item_bootstrap",)
CLUSTER_METHOD_VALUES = ("paired_group_cluster_bootstrap",)
CLUSTER_KEY_VALUES = ("rid_prefix_before_hash",)
RELIABILITY_VALUES = ("ok", "cautious", "low")
SCOPE_VALUES = ("both_completed",)
MIN_CLUSTER_ROUNDS = 1000
RELIABLE_CLUSTER_MIN = 50
CAUTIOUS_CLUSTER_MIN = 30

# spec 第 2 节字符串枚举白名单；其余字符串必须满足 SAFE_STRING_RE。
STRING_ENUM = frozenset(
    {
        "schema",
        "protocol",
        "base",
        "tuned",
        "choice",
        "noul",
        "score",
        "en",
        "zh",
        "2",
        "3-4",
        "5-8",
        "9-26",
        "classification",
        "distillation",
        "calibration",
        "selection",
        "all",
        "fitted",
        "applied",
        "pending_temperature",
        "paired_item_bootstrap",
        "paired_group_cluster_bootstrap",
        "rid_prefix_before_hash",
        "ok",
        "cautious",
        "low",
        "both_completed",
        "grid+golden_section_nll",
        PROTOCOL_ID,
        SCHEMA_ID,
    }
)

FORBIDDEN_KEY_RE = re.compile(
    r"(?i)(^|_)(rid|id|uuid|prompt|text|content|option|question|answer|gold|pred|"
    r"prediction|row|sample|case|item|logit|prob)\b"
)
# v2 schema 里有三个键与上面的禁键正则字面冲突（low_sample_* 命中 sample、
# ci95_item 命中 item），但它们本身是聚合统计字段而非逐例字段：仅按精确键名豁免。
FORBIDDEN_KEY_EXEMPT = frozenset({"low_sample_bins", "low_sample_flag", "ci95_item"})
SAFE_STRING_RE = re.compile(r"[A-Za-z0-9._#/-]{1,64}")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
CJK_RE = re.compile(
    "[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]"
)
PRINTABLE_RUN_RE = re.compile(r"[\x20-\x7e]{201,}")


@dataclass
class Report:
    """检查结果：违规列表 + 已执行检查数 + 文件字节数。"""

    violations: List[str] = field(default_factory=list)
    checks: int = 0
    size: int = 0

    @property
    def ok(self) -> bool:
        return not self.violations

    def tick(self, count: int = 1) -> None:
        self.checks += count

    def fail(self, message: str) -> None:
        self.violations.append(message)

    def check(self, condition: bool, message: str) -> bool:
        self.tick()
        if not condition:
            self.fail(message)
        return condition


def _key_is_forbidden(key: str) -> bool:
    """判断键是否命中逐例字段模式（v2 的精确键名豁免）。"""
    if key in FORBIDDEN_KEY_EXEMPT:
        return False
    return FORBIDDEN_KEY_RE.search(key) is not None


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _close(left: float, right: float, tolerance: float = TOL) -> bool:
    return abs(left - right) <= tolerance


def _scan_raw_text(text: str, report: Report) -> None:
    """原始文本扫描：禁止 unicode 转义、换行转义、CJK、超长可打印串。"""
    report.tick()
    if "\\u" in text:
        report.fail("raw JSON contains a \\u escape sequence (aggregate must be UTF-8 with ensure_ascii=False)")
    for escape, label in (("\\n", "\\n"), ("\\r", "\\r"), ("\\t", "\\t")):
        if escape in text:
            report.fail(f"raw JSON contains a {label} escape sequence")
    match = CJK_RE.search(text)
    if match:
        report.fail(
            f"raw JSON contains CJK character U+{ord(match.group(0)):04X} at offset {match.start()}"
        )
    match = PRINTABLE_RUN_RE.search(text)
    if match:
        report.fail(
            f"raw JSON contains a printable run of {len(match.group(0))} characters (> 200)"
        )


def _check_object_keys(
    report: Report,
    value: Dict[str, Any],
    path: str,
    allowed: Iterable[str],
    required: Iterable[str],
) -> None:
    """键白名单 + 必填键 + 禁键。"""
    allowed_set = set(allowed)
    report.tick()
    for key in value:
        report.tick()
        if not isinstance(key, str):
            report.fail(f"{path}: JSON object key must be a string")
            continue
        if _key_is_forbidden(key):
            report.fail(f"{path}: forbidden key {key!r} (per-example field pattern)")
        if key not in allowed_set:
            report.fail(f"{path}: unknown key {key!r}")
        if not SAFE_STRING_RE.fullmatch(key):
            report.fail(f"{path}: key {key!r} is not a safe identifier")
    for key in required:
        if key not in value:
            report.fail(f"{path}: missing required key {key!r}")


def _check_label_map(
    report: Report, value: Dict[str, Any], path: str
) -> List[str]:
    """校验动态标签映射（models / coverage.models）：恰好两个安全标签键。"""
    report.tick()
    labels: List[str] = []
    for key in value:
        report.tick()
        if not isinstance(key, str):
            report.fail(f"{path}: JSON object key must be a string")
            continue
        if _key_is_forbidden(key):
            report.fail(f"{path}: forbidden key {key!r} (per-example field pattern)")
        if not LABEL_RE.fullmatch(key):
            report.fail(
                f"{path}: model label {key!r} must match {LABEL_RE.pattern}"
            )
        labels.append(key)
    report.tick()
    if len(value) != 2:
        report.fail(f"{path}: expected exactly two model labels, got {len(value)}")
    return labels


def _object_value(report: Report, value: Any, path: str) -> Optional[Dict[str, Any]]:
    report.tick()
    if isinstance(value, dict):
        return value
    report.fail(f"{path}: expected object, got {_type_name(value)}")
    return None


def _int_value(
    report: Report,
    value: Any,
    path: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> Optional[int]:
    report.tick()
    if isinstance(value, bool) or not isinstance(value, int):
        report.fail(f"{path}: expected integer, got {_type_name(value)}")
        return None
    if minimum is not None and value < minimum:
        report.fail(f"{path}: {value} < minimum {minimum}")
        return None
    if maximum is not None and value > maximum:
        report.fail(f"{path}: {value} > maximum {maximum}")
        return None
    return value


def _number_value(
    report: Report,
    value: Any,
    path: str,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> Optional[float]:
    report.tick()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        report.fail(f"{path}: expected number, got {_type_name(value)}")
        return None
    number = float(value)
    if not math.isfinite(number):
        report.fail(f"{path}: number must be finite")
        return None
    if minimum is not None and number < minimum:
        report.fail(f"{path}: {number} < minimum {minimum}")
        return None
    if maximum is not None and number > maximum:
        report.fail(f"{path}: {number} > maximum {maximum}")
        return None
    return number


def _bool_value(report: Report, value: Any, path: str) -> Optional[bool]:
    report.tick()
    if isinstance(value, bool):
        return value
    report.fail(f"{path}: expected boolean, got {_type_name(value)}")
    return None


def _string_value(report: Report, value: Any, path: str) -> Optional[str]:
    report.tick()
    if not isinstance(value, str):
        report.fail(f"{path}: expected string, got {_type_name(value)}")
        return None
    if CONTROL_RE.search(value):
        report.fail(f"{path}: string contains a control character or newline")
        return None
    if CJK_RE.search(value):
        match = CJK_RE.search(value)
        assert match is not None
        report.fail(
            f"{path}: string contains CJK character U+{ord(match.group(0)):04X}"
        )
        return None
    if "\\u" in value or "\\n" in value:
        report.fail(f"{path}: string contains a JSON escape sequence")
        return None
    if value in STRING_ENUM:
        return value
    if SAFE_STRING_RE.fullmatch(value):
        return value
    report.fail(
        f"{path}: string {value[:40]!r} is neither an allowed enum value "
        "nor a safe token (<=64 chars of [A-Za-z0-9._#/-])"
    )
    return None


def _check_accuracy(
    report: Report,
    value: Any,
    path: str,
    correct: Optional[int],
    total: Optional[int],
) -> Optional[float]:
    accuracy = _number_value(report, value, path, 0.0, 1.0)
    if accuracy is None:
        return None
    if correct is not None and total is not None:
        expected = round(correct / total, 6) if total else 0.0
        report.tick()
        if not _close(accuracy, expected):
            report.fail(
                f"{path}: accuracy {accuracy} != round(correct/total, 6) = {expected}"
            )
    return accuracy


def _check_ci_pair(
    report: Report,
    value: Any,
    path: str,
    point: Optional[float],
    bounds: Tuple[float, float],
) -> Optional[Tuple[float, float]]:
    report.tick()
    if not isinstance(value, list) or len(value) != 2:
        report.fail(f"{path}: expected a two-number array, got {_type_name(value)}")
        return None
    lower = _number_value(report, value[0], f"{path}[0]", bounds[0], bounds[1])
    upper = _number_value(report, value[1], f"{path}[1]", bounds[0], bounds[1])
    if lower is None or upper is None:
        return None
    report.tick()
    if lower > upper + TOL:
        report.fail(f"{path}: CI lower {lower} > upper {upper}")
    if point is not None and not (lower - TOL <= point <= upper + TOL):
        report.fail(f"{path}: CI [{lower}, {upper}] does not contain point estimate {point}")
    return lower, upper


def _check_group_block(
    report: Report,
    block: Any,
    path: str,
) -> Tuple[Optional[int], Optional[int], bool]:
    """分层块：{} 视为 total=0；否则必须含 total/correct/accuracy/ci95_wilson。"""
    report.tick()
    if not isinstance(block, dict):
        report.fail(f"{path}: expected object, got {_type_name(block)}")
        return None, None, False
    if not block:
        return 0, 0, True
    _check_object_keys(report, block, path, GROUP_BLOCK_KEYS, GROUP_BLOCK_KEYS)
    total = _int_value(report, block.get("total"), f"{path}.total", minimum=0)
    correct = _int_value(report, block.get("correct"), f"{path}.correct", minimum=0)
    if total is not None and correct is not None and correct > total:
        report.fail(f"{path}: correct {correct} > total {total}")
    accuracy = _check_accuracy(report, block.get("accuracy"), f"{path}.accuracy", correct, total)
    _check_ci_pair(report, block.get("ci95_wilson"), f"{path}.ci95_wilson", accuracy, (0.0, 1.0))
    valid = total is not None and correct is not None
    return total, correct, valid


def _check_group_family(
    report: Report,
    family: Any,
    path: str,
    family_keys: Sequence[str],
    model_total: Optional[int],
    model_correct: Optional[int],
) -> None:
    family_obj = _object_value(report, family, path)
    if family_obj is None:
        return
    _check_object_keys(report, family_obj, path, family_keys, family_keys)
    total_sum = 0
    correct_sum = 0
    complete = True
    for key in family_keys:
        if key not in family_obj:
            complete = False
            continue
        total, correct, valid = _check_group_block(report, family_obj[key], f"{path}.{key}")
        if not valid:
            complete = False
            continue
        assert total is not None and correct is not None
        total_sum += total
        correct_sum += correct
    if complete and model_total is not None:
        report.tick()
        if total_sum != model_total:
            report.fail(
                f"{path}: stratified totals sum to {total_sum}, model total is {model_total}"
            )
    if complete and model_correct is not None:
        report.tick()
        if correct_sum != model_correct:
            report.fail(
                f"{path}: stratified correct sum is {correct_sum}, model correct is {model_correct}"
            )


def _check_model(
    report: Report,
    model: Dict[str, Any],
    path: str,
    expected_evaluated: Optional[int],
    coverage_stats: Optional[Dict[str, Optional[float]]],
) -> Dict[str, Optional[float]]:
    _check_object_keys(report, model, path, MODEL_KEYS, MODEL_REQUIRED_KEYS)
    total = _int_value(report, model.get("total"), f"{path}.total", minimum=0)
    correct = _int_value(report, model.get("correct"), f"{path}.correct", minimum=0)
    if total is not None and correct is not None and correct > total:
        report.fail(f"{path}: correct {correct} > total {total}")
    accuracy = _check_accuracy(report, model.get("accuracy"), f"{path}.accuracy", correct, total)
    _check_ci_pair(
        report,
        model.get("accuracy_ci95_wilson"),
        f"{path}.accuracy_ci95_wilson",
        accuracy,
        (0.0, 1.0),
    )
    with_missing = _number_value(
        report, model.get("accuracy_with_missing"), f"{path}.accuracy_with_missing", 0.0, 1.0
    )
    if with_missing is not None and correct is not None and expected_evaluated is not None:
        expected_with_missing = (
            round(correct / expected_evaluated, 6) if expected_evaluated else 0.0
        )
        report.tick()
        if not _close(with_missing, expected_with_missing):
            report.fail(
                f"{path}.accuracy_with_missing: {with_missing} != "
                f"correct/expected_evaluated = {expected_with_missing}"
            )
    # v2 主口径：缺失/失败行记错误 → ITT 准确率不得高于完成子集准确率。
    if with_missing is not None and accuracy is not None:
        report.tick()
        if with_missing > accuracy + TOL:
            report.fail(
                f"{path}.accuracy_with_missing: {with_missing} > accuracy {accuracy} "
                "(completed-subset accuracy)"
            )
    # v2：evaluated_accuracy 是 accuracy（完成子集）的显式同值字段。
    if "evaluated_accuracy" in model:
        evaluated_accuracy = _number_value(
            report,
            model.get("evaluated_accuracy"),
            f"{path}.evaluated_accuracy",
            0.0,
            1.0,
        )
        if evaluated_accuracy is not None and accuracy is not None:
            report.tick()
            if not _close(evaluated_accuracy, accuracy):
                report.fail(
                    f"{path}.evaluated_accuracy: {evaluated_accuracy} != accuracy {accuracy}"
                )
    missing_rows = _int_value(report, model.get("missing_rows"), f"{path}.missing_rows", minimum=0)
    if coverage_stats is not None:
        evaluated = coverage_stats.get("evaluated")
        missing = coverage_stats.get("missing")
        report.tick()
        if total is not None and evaluated is not None and total != evaluated:
            report.fail(
                f"{path}.total: {total} != coverage.models evaluated {evaluated}"
            )
        report.tick()
        if missing_rows is not None and missing is not None and missing_rows != missing:
            report.fail(
                f"{path}.missing_rows: {missing_rows} != coverage.models missing {missing}"
            )
    for family_name, family_keys in GROUP_SPECS:
        _check_group_family(
            report,
            model.get(family_name),
            f"{path}.{family_name}",
            family_keys,
            total,
            correct,
        )
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "missing_rows": missing_rows,
    }


def _check_coverage(
    report: Report, coverage: Dict[str, Any]
) -> Tuple[Dict[str, Dict[str, Optional[float]]], Optional[int]]:
    path = "$.coverage"
    _check_object_keys(report, coverage, path, COVERAGE_KEYS, COVERAGE_KEYS)
    view_rows = _int_value(report, coverage.get("view_rows"), f"{path}.view_rows", minimum=0)
    skipped_obj = _object_value(report, coverage.get("skipped"), f"{path}.skipped")
    skipped_sum: Optional[int] = 0
    if skipped_obj is not None:
        skipped_sum = 0
        for key, value in skipped_obj.items():
            report.tick()
            if not isinstance(key, str):
                report.fail(f"{path}.skipped: key must be a string")
                skipped_sum = None
                continue
            if _key_is_forbidden(key):
                report.fail(f"{path}.skipped: forbidden key {key!r}")
            if key not in SKIPPED_REASONS:
                report.fail(
                    f"{path}.skipped: unknown skip reason {key!r} "
                    f"(allowed: {sorted(SKIPPED_REASONS)})"
                )
            count = _int_value(report, value, f"{path}.skipped.{key}", minimum=0)
            if count is None:
                skipped_sum = None
            elif skipped_sum is not None:
                skipped_sum += count
    skipped_total = _int_value(
        report, coverage.get("skipped_total"), f"{path}.skipped_total", minimum=0
    )
    if skipped_sum is not None and skipped_total is not None:
        report.tick()
        if skipped_sum != skipped_total:
            report.fail(
                f"{path}.skipped_total: {skipped_total} != sum(skipped) = {skipped_sum}"
            )
    expected = _int_value(
        report, coverage.get("expected_evaluated"), f"{path}.expected_evaluated", minimum=0
    )
    if view_rows is not None and skipped_sum is not None:
        calculated = view_rows - skipped_sum
        report.tick()
        if calculated < 0:
            report.fail(
                f"{path}: view_rows {view_rows} < skipped_total {skipped_sum}"
            )
        if expected is not None and expected != calculated:
            report.fail(
                f"{path}.expected_evaluated: {expected} != view_rows - skipped_total = {calculated}"
            )
    coverage_models: Dict[str, Dict[str, Optional[float]]] = {}
    models_obj = _object_value(report, coverage.get("models"), f"{path}.models")
    if models_obj is not None:
        for label in _check_label_map(report, models_obj, f"{path}.models"):
            block_path = f"{path}.models.{label}"
            block = _object_value(report, models_obj[label], block_path)
            if block is None:
                continue
            _check_object_keys(
                report,
                block,
                block_path,
                COVERAGE_MODEL_KEYS,
                COVERAGE_MODEL_REQUIRED_KEYS,
            )
            evaluated = _int_value(
                report, block.get("evaluated"), f"{block_path}.evaluated", minimum=0
            )
            missing = _int_value(report, block.get("missing"), f"{block_path}.missing", minimum=0)
            if evaluated is not None and missing is not None and expected is not None:
                report.tick()
                if evaluated + missing != expected:
                    report.fail(
                        f"{block_path}: evaluated {evaluated} + missing {missing} "
                        f"!= expected_evaluated {expected}"
                    )
            completion_rate: Optional[float] = None
            if "completion_rate" in block:
                completion_rate = _number_value(
                    report,
                    block.get("completion_rate"),
                    f"{block_path}.completion_rate",
                    0.0,
                    1.0,
                )
                if (
                    completion_rate is not None
                    and evaluated is not None
                    and expected is not None
                ):
                    expected_rate = round(evaluated / expected, 6) if expected else 0.0
                    report.tick()
                    if not _close(completion_rate, expected_rate):
                        report.fail(
                            f"{block_path}.completion_rate: {completion_rate} != "
                            f"evaluated/expected_evaluated = {expected_rate}"
                        )
            coverage_models[label] = {
                "evaluated": evaluated,
                "missing": missing,
                "completion_rate": completion_rate,
            }
    return coverage_models, expected


def _check_models(
    report: Report,
    models: Dict[str, Any],
    coverage_models: Dict[str, Dict[str, Optional[float]]],
    expected_evaluated: Optional[int],
) -> Dict[str, Dict[str, Optional[float]]]:
    stats: Dict[str, Dict[str, Optional[float]]] = {}
    path = "$.models"
    for label in _check_label_map(report, models, path):
        model_path = f"{path}.{label}"
        model = _object_value(report, models[label], model_path)
        if model is None:
            continue
        stats[label] = _check_model(
            report, model, model_path, expected_evaluated, coverage_models.get(label)
        )
    return stats


def _check_paired(
    report: Report,
    paired: Dict[str, Any],
    coverage_models: Dict[str, Dict[str, Optional[float]]],
    model_stats: Dict[str, Dict[str, Optional[float]]],
) -> Tuple[Optional[str], Optional[str]]:
    path = "$.paired"
    _check_object_keys(report, paired, path, PAIRED_KEYS, PAIRED_REQUIRED_KEYS)
    base_label = _string_value(report, paired.get("base_label"), f"{path}.base_label")
    tuned_label = _string_value(report, paired.get("tuned_label"), f"{path}.tuned_label")
    if base_label is not None and tuned_label is not None:
        report.tick()
        if base_label == tuned_label:
            report.fail(f"{path}: base_label and tuned_label must differ")
        for role, label in (("base_label", base_label), ("tuned_label", tuned_label)):
            if model_stats and label not in model_stats:
                report.fail(f"{path}.{role}: label {label!r} is not present in $.models")
    rows = _int_value(report, paired.get("rows"), f"{path}.rows", minimum=0)
    base_accuracy = _number_value(
        report, paired.get("base_accuracy"), f"{path}.base_accuracy", 0.0, 1.0
    )
    tuned_accuracy = _number_value(
        report, paired.get("tuned_accuracy"), f"{path}.tuned_accuracy", 0.0, 1.0
    )
    delta = _number_value(report, paired.get("delta"), f"{path}.delta", -1.0, 1.0)
    _check_ci_pair(report, paired.get("ci95"), f"{path}.ci95", delta, (-1.0, 1.0))
    rounds = _int_value(report, paired.get("rounds"), f"{path}.rounds", minimum=1)
    _int_value(report, paired.get("seed"), f"{path}.seed",
               minimum=0, maximum=2**63 - 1)
    method = _string_value(report, paired.get("method"), f"{path}.method")
    if method is not None and method not in PAIRED_METHOD_VALUES:
        report.fail(f"{path}.method: unknown method {method!r}")
    if "scope" in paired:
        scope = _string_value(report, paired.get("scope"), f"{path}.scope")
        if scope is not None and scope not in SCOPE_VALUES:
            report.fail(f"{path}.scope: unknown scope {scope!r}")
    if base_accuracy is not None and tuned_accuracy is not None and delta is not None:
        report.tick()
        if not _close(delta, tuned_accuracy - base_accuracy, DEDUCED_TOL):
            report.fail(
                f"{path}.delta: {delta} != tuned_accuracy - base_accuracy = "
                f"{tuned_accuracy - base_accuracy}"
            )
    evaluated = [
        stats.get("evaluated")
        for stats in coverage_models.values()
        if stats.get("evaluated") is not None
    ]
    if rows is not None and evaluated:
        report.tick()
        if rows > min(evaluated):
            report.fail(
                f"{path}.rows: {rows} > min evaluated {min(evaluated)}"
            )
    base_stats = model_stats.get(base_label or "", {})
    tuned_stats = model_stats.get(tuned_label or "", {})
    base_total = base_stats.get("total")
    tuned_total = tuned_stats.get("total")
    # 只有双方都没有缺失行时，配对准确率才必然等于各自模型准确率；
    # 有缺失时配对分析在"双方都完成"的交集上，两者可以不同（不得误判为违规）。
    if (
        rows is not None
        and base_total is not None
        and base_total == tuned_total == rows
        and base_stats.get("missing_rows") == 0
        and tuned_stats.get("missing_rows") == 0
    ):
        base_model_accuracy = base_stats.get("accuracy")
        tuned_model_accuracy = tuned_stats.get("accuracy")
        report.tick()
        if (
            base_accuracy is not None
            and base_model_accuracy is not None
            and not _close(base_accuracy, base_model_accuracy, DEDUCED_TOL)
        ):
            report.fail(
                f"{path}.base_accuracy: {base_accuracy} != "
                f"models.{base_label}.accuracy {base_model_accuracy}"
            )
        report.tick()
        if (
            tuned_accuracy is not None
            and tuned_model_accuracy is not None
            and not _close(tuned_accuracy, tuned_model_accuracy, DEDUCED_TOL)
        ):
            report.fail(
                f"{path}.tuned_accuracy: {tuned_accuracy} != "
                f"models.{tuned_label}.accuracy {tuned_model_accuracy}"
            )
    if "completed_only" in paired:
        _check_completed_only(report, paired.get("completed_only"), path, rows)
    if "cluster" in paired:
        _check_cluster(report, paired.get("cluster"), path, delta)
    return base_label, tuned_label


def _reliability_for(clusters: int) -> str:
    """v2 reliability 阈值：G>=50 ok；30<=G<50 cautious；G<30 low。"""
    if clusters >= RELIABLE_CLUSTER_MIN:
        return "ok"
    if clusters >= CAUTIOUS_CLUSTER_MIN:
        return "cautious"
    return "low"


def _check_completed_only(
    report: Report,
    value: Any,
    paired_path: str,
    paired_rows: Optional[int],
) -> None:
    """v2 paired.completed_only：双方都完成的 rid 交集（敏感性分析，非主结论）。"""
    path = f"{paired_path}.completed_only"
    obj = _object_value(report, value, path)
    if obj is None:
        return
    _check_object_keys(
        report, obj, path, COMPLETED_ONLY_KEYS, COMPLETED_ONLY_REQUIRED_KEYS
    )
    rows = _int_value(report, obj.get("rows"), f"{path}.rows", minimum=0)
    base_accuracy = _number_value(
        report, obj.get("base_accuracy"), f"{path}.base_accuracy", 0.0, 1.0
    )
    tuned_accuracy = _number_value(
        report, obj.get("tuned_accuracy"), f"{path}.tuned_accuracy", 0.0, 1.0
    )
    delta = _number_value(report, obj.get("delta"), f"{path}.delta", -1.0, 1.0)
    if base_accuracy is not None and tuned_accuracy is not None and delta is not None:
        report.tick()
        if not _close(delta, tuned_accuracy - base_accuracy, DEDUCED_TOL):
            report.fail(
                f"{path}.delta: {delta} != tuned_accuracy - base_accuracy = "
                f"{tuned_accuracy - base_accuracy}"
            )
    _check_ci_pair(
        report, obj.get("ci95_group"), f"{path}.ci95_group", delta, (-1.0, 1.0)
    )
    if "ci95_item" in obj:
        _check_ci_pair(
            report, obj.get("ci95_item"), f"{path}.ci95_item", delta, (-1.0, 1.0)
        )
    if "scope" in obj:
        scope = _string_value(report, obj.get("scope"), f"{path}.scope")
        if scope is not None and scope not in SCOPE_VALUES:
            report.fail(f"{path}.scope: unknown scope {scope!r}")
    if rows is not None and paired_rows is not None:
        report.tick()
        if rows > paired_rows:
            report.fail(f"{path}.rows: {rows} > paired.rows {paired_rows}")


def _check_cluster(
    report: Report,
    value: Any,
    paired_path: str,
    paired_delta: Optional[float],
) -> None:
    """v2 paired.cluster：按 rid 前缀聚簇的 group-cluster bootstrap 结果。"""
    path = f"{paired_path}.cluster"
    obj = _object_value(report, value, path)
    if obj is None:
        return
    _check_object_keys(report, obj, path, CLUSTER_KEYS, CLUSTER_KEYS)
    cluster_key = _string_value(report, obj.get("cluster_key"), f"{path}.cluster_key")
    if cluster_key is not None and cluster_key not in CLUSTER_KEY_VALUES:
        report.fail(
            f"{path}.cluster_key: expected one of {CLUSTER_KEY_VALUES}, got {cluster_key!r}"
        )
    clusters = _int_value(report, obj.get("clusters"), f"{path}.clusters", minimum=1)
    _number_value(
        report, obj.get("cluster_size_median"), f"{path}.cluster_size_median", minimum=0.0
    )
    iqr = obj.get("cluster_size_iqr")
    report.tick()
    if not isinstance(iqr, list) or len(iqr) != 2:
        report.fail(
            f"{path}.cluster_size_iqr: expected a two-number array, got {_type_name(iqr)}"
        )
    else:
        q_low = _number_value(
            report, iqr[0], f"{path}.cluster_size_iqr[0]", minimum=0.0
        )
        q_high = _number_value(
            report, iqr[1], f"{path}.cluster_size_iqr[1]", minimum=0.0
        )
        if q_low is not None and q_high is not None:
            report.tick()
            if q_low > q_high + TOL:
                report.fail(
                    f"{path}.cluster_size_iqr: lower {q_low} > upper {q_high}"
                )
    _int_value(
        report, obj.get("cluster_size_max"), f"{path}.cluster_size_max", minimum=0
    )
    kish = _number_value(report, obj.get("kish_neff"), f"{path}.kish_neff", minimum=0.0)
    delta = _number_value(report, obj.get("delta"), f"{path}.delta", -1.0, 1.0)
    _check_ci_pair(report, obj.get("ci95"), f"{path}.ci95", delta, (-1.0, 1.0))
    rounds = _int_value(report, obj.get("rounds"), f"{path}.rounds", minimum=1)
    method = _string_value(report, obj.get("method"), f"{path}.method")
    if method is not None and method not in CLUSTER_METHOD_VALUES:
        report.fail(f"{path}.method: unknown method {method!r}")
    reliability = _string_value(report, obj.get("reliability"), f"{path}.reliability")
    if reliability is not None and reliability not in RELIABILITY_VALUES:
        report.fail(f"{path}.reliability: unknown reliability {reliability!r}")
    if rounds is not None and rounds < MIN_CLUSTER_ROUNDS:
        report.fail(
            f"{path}.rounds: {rounds} < required minimum {MIN_CLUSTER_ROUNDS}"
        )
    if delta is not None and paired_delta is not None:
        report.tick()
        if not _close(delta, paired_delta, DEDUCED_TOL):
            report.fail(
                f"{path}.delta: {delta} != paired.delta {paired_delta}"
            )
    if clusters is not None and reliability is not None:
        expected_reliability = _reliability_for(clusters)
        report.tick()
        if reliability != expected_reliability:
            report.fail(
                f"{path}.reliability: {reliability!r} inconsistent with "
                f"clusters={clusters} (expected {expected_reliability!r})"
            )
    if clusters is not None and kish is not None:
        # Kish 有效样本量不可能超过簇数（Cauchy-Schwarz，(sum w)^2/sum w^2 <= G）。
        report.tick()
        if kish > clusters + TOL:
            report.fail(
                f"{path}.kish_neff: {kish} > clusters {clusters}"
            )


def _check_bins(report: Report, value: Any, path: str) -> Optional[List[int]]:
    """v2 校准分箱：恰好 15 个对象，bin 0..14 各一次；返回各箱 count。"""
    report.tick()
    if not isinstance(value, list):
        report.fail(
            f"{path}: expected an array of {BIN_COUNT} bin objects, got {_type_name(value)}"
        )
        return None
    if len(value) != BIN_COUNT:
        report.fail(f"{path}: expected exactly {BIN_COUNT} bins, got {len(value)}")
        return None
    counts: List[int] = []
    seen: List[int] = []
    valid = True
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        obj = _object_value(report, item, item_path)
        if obj is None:
            valid = False
            continue
        _check_object_keys(report, obj, item_path, BIN_KEYS, BIN_KEYS)
        bin_index = _int_value(
            report, obj.get("bin"), f"{item_path}.bin", minimum=0, maximum=BIN_COUNT - 1
        )
        count = _int_value(report, obj.get("count"), f"{item_path}.count", minimum=0)
        avg_confidence = _number_value(
            report, obj.get("avg_confidence"), f"{item_path}.avg_confidence", 0.0, 1.0
        )
        accuracy = _number_value(
            report, obj.get("accuracy"), f"{item_path}.accuracy", 0.0, 1.0
        )
        gap = _number_value(report, obj.get("gap"), f"{item_path}.gap", -1.0, 1.0)
        if bin_index is None or count is None or avg_confidence is None or accuracy is None:
            valid = False
            continue
        if gap is not None and not _close(gap, abs(accuracy - avg_confidence), 2 * TOL):
            report.fail(
                f"{item_path}.gap: {gap} != |accuracy - avg_confidence| = "
                f"{round(abs(accuracy - avg_confidence), 6)}"
            )
        seen.append(bin_index)
        counts.append(count)
    if not valid:
        return None
    report.tick()
    if sorted(seen) != list(range(BIN_COUNT)):
        duplicates = sorted({value for value in seen if seen.count(value) > 1})
        report.fail(
            f"{path}: bins must cover 0..{BIN_COUNT - 1} exactly once "
            f"(duplicates={duplicates})"
        )
        return None
    return counts


def _check_low_sample_fields(
    report: Report,
    block: Dict[str, Any],
    path: str,
    bins_counts: Optional[List[int]],
) -> None:
    """v2 low_sample_bins / low_sample_flag 与 bins 的一致性。"""
    low_sample_bins: Optional[int] = None
    if "low_sample_bins" in block:
        low_sample_bins = _int_value(
            report, block.get("low_sample_bins"), f"{path}.low_sample_bins", minimum=0
        )
    low_sample_flag: Optional[bool] = None
    if "low_sample_flag" in block:
        low_sample_flag = _bool_value(
            report, block.get("low_sample_flag"), f"{path}.low_sample_flag"
        )
    bins_present = "bins" in block
    if not bins_present:
        report.tick()
        if low_sample_bins is not None or low_sample_flag is not None:
            report.fail(
                f"{path}.bins: required when low_sample_bins/low_sample_flag are present"
            )
        return
    if bins_counts is None:
        return
    expected_low = sum(1 for count in bins_counts if count < LOW_SAMPLE_THRESHOLD)
    if low_sample_bins is not None:
        report.tick()
        if low_sample_bins != expected_low:
            report.fail(
                f"{path}.low_sample_bins: {low_sample_bins} != count(bins.count < "
                f"{LOW_SAMPLE_THRESHOLD}) = {expected_low}"
            )
    if low_sample_flag is not None:
        report.tick()
        if low_sample_flag != (expected_low > 0):
            report.fail(
                f"{path}.low_sample_flag: {low_sample_flag} != (low_sample_bins > 0) = "
                f"{expected_low > 0}"
            )


def _check_calibration_metric_block(
    report: Report,
    block: Dict[str, Any],
    path: str,
    tuned_total: Optional[int],
    tuned_label: Optional[str],
) -> None:
    _check_object_keys(
        report,
        block,
        path,
        CALIBRATION_METRIC_KEYS,
        CALIBRATION_METRIC_REQUIRED_KEYS,
    )
    rows = _int_value(report, block.get("rows"), f"{path}.rows", minimum=0)
    _number_value(report, block.get("accuracy"), f"{path}.accuracy", 0.0, 1.0)
    _number_value(report, block.get("nll"), f"{path}.nll", minimum=0.0)
    _number_value(report, block.get("brier"), f"{path}.brier", minimum=0.0)
    ece = _number_value(report, block.get("ece"), f"{path}.ece", 0.0, 1.0)
    _number_value(report, block.get("mce"), f"{path}.mce", 0.0, 1.0)
    bins_counts: Optional[List[int]] = None
    if "bins" in block:
        bins_counts = _check_bins(report, block.get("bins"), f"{path}.bins")
    _check_low_sample_fields(report, block, path, bins_counts)
    if "ece_ci95_group" in block:
        # ECE 是比值估计（Σ gap·n / N）；簇 bootstrap 的百分位区间**不保证包含**
        # 全样本点估计（ratio estimator 的有限样本偏差，簇大小不均时更明显）。
        # 因此这里只校验区间结构（两个 [0,1] 内、单调），不强制包含 ece 点估计。
        _check_ci_pair(
            report, block.get("ece_ci95_group"), f"{path}.ece_ci95_group", None, (0.0, 1.0)
        )
    if "ece_rounds" in block:
        _int_value(report, block.get("ece_rounds"), f"{path}.ece_rounds", minimum=1)
    if rows is not None and tuned_total is not None:
        report.tick()
        if rows != tuned_total:
            report.fail(
                f"{path}.rows: {rows} != models.{tuned_label or 'tuned'}.total = {tuned_total}"
            )


def _check_calibration(
    report: Report,
    calibration: Dict[str, Any],
    tuned_total: Optional[int],
    tuned_label: Optional[str],
) -> None:
    path = "$.calibration"
    # pending_temperature 的最小形态只写 status；fitted/applied 才要求完整字段。
    _check_object_keys(report, calibration, path, CALIBRATION_KEYS, ("status",))
    status = _string_value(report, calibration.get("status"), f"{path}.status")
    if status is not None and status not in STATUS_VALUES:
        report.fail(f"{path}.status: unknown status {status!r}")

    temperature: Optional[float] = None
    if calibration.get("temperature") is not None:
        temperature = _number_value(report, calibration["temperature"], f"{path}.temperature")
        if temperature is not None and temperature <= 0:
            report.fail(f"{path}.temperature: must be > 0, got {temperature}")
    fit_half: Optional[str] = None
    if calibration.get("fit_half") is not None:
        fit_half = _string_value(report, calibration["fit_half"], f"{path}.fit_half")
        if fit_half is not None and fit_half not in FIT_HALF_VALUES:
            report.fail(f"{path}.fit_half: unknown half {fit_half!r}")
    fit_rows: Optional[int] = None
    if calibration.get("fit_rows") is not None:
        fit_rows = _int_value(report, calibration["fit_rows"], f"{path}.fit_rows", minimum=0)
    fit_method: Optional[str] = None
    if calibration.get("fit_method") is not None:
        fit_method = _string_value(report, calibration["fit_method"], f"{path}.fit_method")
        if fit_method is not None and fit_method not in FIT_METHOD_VALUES:
            report.fail(f"{path}.fit_method: unknown method {fit_method!r}")
    unchanged: Optional[bool] = None
    if "accuracy_unchanged" in calibration:
        unchanged = _bool_value(
            report, calibration.get("accuracy_unchanged"), f"{path}.accuracy_unchanged"
        )
    if "ece_rounds" in calibration:
        _int_value(report, calibration.get("ece_rounds"), f"{path}.ece_rounds", minimum=1)

    if status == "fitted":
        report.tick()
        if temperature is None:
            report.fail(f"{path}.temperature: required when status='fitted'")
        report.tick()
        if fit_rows is None or fit_rows <= 0:
            report.fail(f"{path}.fit_rows: must be > 0 when status='fitted'")
        report.tick()
        if fit_half is None:
            report.fail(f"{path}.fit_half: required when status='fitted'")
        report.tick()
        if fit_method is None:
            report.fail(f"{path}.fit_method: required when status='fitted'")
        report.tick()
        if unchanged is not True:
            report.fail(f"{path}.accuracy_unchanged: must be true when status='fitted'")

    if status == "applied":
        report.tick()
        if temperature is None:
            report.fail(f"{path}.temperature: required when status='applied'")

    if status == "pending_temperature":
        report.tick()
        if temperature is not None:
            report.fail(
                f"{path}.temperature: must be null when status='pending_temperature'"
            )
        report.tick()
        if fit_rows is not None and fit_rows != 0:
            report.fail(
                f"{path}.fit_rows: must be 0 when status='pending_temperature'"
            )

    raw = calibration.get("raw")
    if raw is not None:
        raw_obj = _object_value(report, raw, f"{path}.raw")
        if raw_obj is not None:
            _check_calibration_metric_block(
                report, raw_obj, f"{path}.raw", tuned_total, tuned_label
            )
    elif status in ("fitted", "applied"):
        report.fail(f"{path}.raw: required when status={status!r}")

    calibrated = calibration.get("calibrated")
    if calibrated is None:
        if status in ("fitted", "applied"):
            report.fail(f"{path}.calibrated: required when status={status!r}")
    else:
        calibrated_obj = _object_value(report, calibrated, f"{path}.calibrated")
        if calibrated_obj is not None:
            _check_calibration_metric_block(
                report, calibrated_obj, f"{path}.calibrated", tuned_total, tuned_label
            )


def check_document(document: Any) -> Report:
    """只检查已解析的 JSON 文档（不做体积/原始文本扫描）。"""
    report = Report()
    _check_document(document, report)
    return report


def _check_document(document: Any, report: Report) -> None:
    report.tick()
    if not isinstance(document, dict):
        report.fail("$: top-level JSON value must be an object")
        return
    _check_object_keys(report, document, "$", ROOT_KEYS, ROOT_KEYS)
    schema = _string_value(report, document.get("schema"), "$.schema")
    if schema is not None and schema != SCHEMA_ID:
        report.fail(f"$.schema: expected {SCHEMA_ID!r}, got {schema!r}")
    protocol = _string_value(report, document.get("protocol"), "$.protocol")
    if protocol is not None and protocol != PROTOCOL_ID:
        report.fail(f"$.protocol: expected {PROTOCOL_ID!r}, got {protocol!r}")
    coverage = _object_value(report, document.get("coverage"), "$.coverage")
    coverage_models: Dict[str, Dict[str, Optional[float]]] = {}
    expected_evaluated: Optional[int] = None
    if coverage is not None:
        coverage_models, expected_evaluated = _check_coverage(report, coverage)
    models = _object_value(report, document.get("models"), "$.models")
    model_stats: Dict[str, Dict[str, Optional[float]]] = {}
    if models is not None:
        model_stats = _check_models(report, models, coverage_models, expected_evaluated)
    if coverage_models and model_stats:
        report.tick()
        if set(coverage_models) != set(model_stats):
            report.fail(
                "$.coverage.models labels "
                f"{sorted(coverage_models)} != $.models labels {sorted(model_stats)}"
            )
    base_label: Optional[str] = None
    tuned_label: Optional[str] = None
    paired = _object_value(report, document.get("paired"), "$.paired")
    if paired is not None:
        base_label, tuned_label = _check_paired(
            report, paired, coverage_models, model_stats
        )
    calibration = _object_value(report, document.get("calibration"), "$.calibration")
    if calibration is not None:
        tuned_total = model_stats.get(tuned_label or "", {}).get("total")
        _check_calibration(report, calibration, tuned_total, tuned_label)


def _reject_constant(token: str) -> Any:
    raise ValueError(f"non-finite JSON constant {token!r} is not allowed")


def check_bytes(data: bytes, max_bytes: int = DEFAULT_MAX_BYTES) -> Report:
    """检查聚合 JSON 的原始字节。"""
    report = Report(size=len(data))
    report.tick()
    if max_bytes <= 0:
        report.fail(f"max_bytes must be positive, got {max_bytes}")
    if len(data) > max_bytes:
        report.fail(f"file is {len(data)} bytes > max_bytes {max_bytes}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        report.fail(f"file is not valid UTF-8: {error}")
        return report
    _scan_raw_text(text, report)

    duplicates: List[str] = []

    def pairs_hook(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        obj: Dict[str, Any] = {}
        for key, value in pairs:
            if key in obj:
                duplicates.append(key)
            obj[key] = value
        return obj

    try:
        document = json.loads(
            text, object_pairs_hook=pairs_hook, parse_constant=_reject_constant
        )
    except (json.JSONDecodeError, ValueError) as error:
        report.fail(f"invalid JSON: {error}")
        return report
    for key in sorted(set(duplicates)):
        report.fail(f"$: duplicate JSON key {key!r}")
    _check_document(document, report)
    return report


def check_file(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> Report:
    """读取文件并检查；OSError 由调用方处理。"""
    return check_bytes(Path(path).read_bytes(), max_bytes)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--in", dest="input", type=Path, required=True,
                        help="待检查的 aggregate.json")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"文件字节上限（默认 {DEFAULT_MAX_BYTES}）")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args(argv)
    if args.max_bytes <= 0:
        print("check_aggregate_export failed: --max-bytes must be positive", file=sys.stderr)
        return 2
    try:
        report = check_file(args.input, args.max_bytes)
    except OSError as error:
        print(f"check_aggregate_export failed: {error}", file=sys.stderr)
        return 2
    if report.ok:
        if args.json:
            print(json.dumps(
                {"status": "pass", "checks": report.checks, "bytes": report.size},
                ensure_ascii=False,
            ))
        else:
            print(f"pass: {report.checks} checks, {report.size} bytes")
        return 0
    for violation in report.violations:
        print(f"VIOLATION: {violation}")
    if args.json:
        print(json.dumps(
            {"status": "fail", "violations": report.violations},
            ensure_ascii=False,
        ))
    else:
        print(f"fail: {len(report.violations)} violation(s)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
