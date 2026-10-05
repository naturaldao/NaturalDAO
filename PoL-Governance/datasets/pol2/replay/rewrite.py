"""PoL2 回放池：英译中改写 + 教师重判流水线（默认离线，真实调用需 Lead 批准）。

为什么必须重判（SPEC 明文）：英文标签是英语语境的产物，直接当中文真值等于把别人的
判断当成我们的判断。因此本流水线把「改写」与「重判」拆成两次独立调用：

    prepare   读入规范化后的英文决策样本，产出改写请求包（教师看不到英文标签）
    run       改写 →（另一个血缘的）教师对中文版独立作答 → 生成 zh.records.jsonl
    verify    校验溯源、许可、分区、血缘独立、去重键与「未照搬英文标签」

默认与安全约束：
- 不带 --live 时 run 只跑 --fixture 的确定性离线链路，产物标记 fixture=true、usable_for_training=false
  （离线链路仍使用两个不同 lineage 的伪模型，以保持「改写与重判必须独立」这条门禁始终生效）；
- --live 必须同时给出 --endpoint/--rewrite-model/--judge-model/密钥来源与 --approved-by-lead，
  缺任何一项直接退出码 2，绝不静默降级或伪造结果；
- 只接受 candidates.json 中 tier=admit 的数据集、只接受 train 分区、只接受许可白名单；
- 改写教师看不到英文标签（prepare 不把 target 写进 prompt），重判教师也看不到；
- 每条记录保留 dataset/revision/行号/许可/group_id，并写入去重键（中文 state+question+options 的 sha256）。

只用标准库，可 `uv run --no-project --offline` 运行。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOOL = "pol2-replay-rewrite"
PIPELINE_VERSION = "pol2-replay-rewrite-v0.1"
REWRITE_PROMPT_VERSION = "rewrite-en-zh-v0.1"
JUDGE_PROMPT_VERSION = "judge-zh-typed-v0.1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_LICENSES = ("cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "mit", "apache-2.0", "bsd-2-clause",
                    "bsd-3-clause")
ALLOWED_KINDS = ("choice", "noul", "score")
ALLOWED_SPLITS = ("train",)
USER_AGENT = "PoL2-replay-rewrite/0.1 (+https://github.com/naturaldao/NaturalDAO)"

REWRITE_SYSTEM = ("你是中文改写编辑。把给定的英文决策场景改写成自然、具体、可独立阅读的简体中文语境，"
                  "保留全部关键事实与不确定性，不要补充原文没有的信息，不要给出结论或标签。")
JUDGE_SYSTEM = ("你是独立的判断者。只根据给定的中文场景与问题作答，输出一个 JSON："
                "{\"answer\": <选项 key 或数值>, \"probs\": {<选项 key>: <概率>}}。"
                "不得参考任何英文原文或他人答案；信息不足时必须如实反映在概率里。")


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_text(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(text))).strip()


def normalize_options(options):
    """Return [(key, label)] and keep the original order (option order is part of the task)."""
    pairs = []
    for index, option in enumerate(options or []):
        if isinstance(option, dict):
            key = str(option.get("key", index))
            pairs.append((key, normalize_text(option.get("label", option.get("text", "")))))
        else:
            pairs.append((chr(65 + index) if index < 26 else str(index), normalize_text(option)))
    return pairs


def dedup_key(state, question, options):
    body = "\u0001".join([normalize_text(state).lower(), normalize_text(question).lower(),
                          "\u0002".join(f"{key}={label}" for key, label in normalize_options(options))])
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load_admitted(candidates_path):
    payload = load_json(candidates_path)
    rows = payload["candidates"] if isinstance(payload, dict) else payload
    return {row["id"]: row for row in rows}


def source_problems(row, admitted):
    """Validate one normalized English source row against the pool contract."""
    problems = []
    dataset = row.get("dataset")
    if dataset not in admitted:
        problems.append(f"{dataset}: 不在候选审计表里，拒绝处理")
        return problems
    candidate = admitted[dataset]
    if candidate.get("tier") != "admit":
        problems.append(f"{dataset}: tier={candidate.get('tier')}，只有 admit 的候选能进回放池")
    if not SHA_RE.match(str(row.get("revision", ""))):
        problems.append(f"{dataset}: revision 必须是固定 40 位 sha")
    if str(row.get("revision")) != str(candidate.get("revision")):
        problems.append(f"{dataset}: revision {row.get('revision')} 与审计表 "
                        f"{candidate.get('revision')} 不一致")
    license_name = str(row.get("license", "")).lower()
    if license_name not in ALLOWED_LICENSES:
        problems.append(f"{dataset}: 许可 {row.get('license')!r} 不在白名单 {ALLOWED_LICENSES}")
    if str(row.get("split")) not in ALLOWED_SPLITS:
        problems.append(f"{dataset}: split={row.get('split')!r} 不是 train，禁止进入回放池")
    if not isinstance(row.get("line_number"), int) or row["line_number"] < 1:
        problems.append(f"{dataset}: 缺少原始行号 line_number")
    if row.get("kind") not in ALLOWED_KINDS:
        problems.append(f"{dataset}: kind={row.get('kind')!r} 不是 choice/noul/score")
    if not normalize_text(row.get("state")) or not normalize_text(row.get("question")):
        problems.append(f"{dataset}: state/question 不能为空")
    if not normalize_options(row.get("options")):
        problems.append(f"{dataset}: options 不能为空")
    if str(row.get("source_language", "en")).lower() != "en":
        problems.append(f"{dataset}: 只有英译中改写走本流水线，source_language="
                        f"{row.get('source_language')!r}")
    return problems


def record_id(row, index):
    return (f"{row['dataset']}#{row['revision'][:12]}#L{row['line_number']}#"
            f"{row.get('group_id', row.get('id', 'row'))}#{row['kind']}#{index}")


def cmd_prepare(args):
    admitted = load_admitted(args.candidates)
    rows = read_jsonl(args.source)
    problems = []
    plan = []
    for row in rows:
        problems.extend(source_problems(row, admitted))
    if problems:
        for problem in problems[:20]:
            print(f"PROBLEM {problem}", file=sys.stderr)
        print(json.dumps({"status": "failed", "problems": len(problems), "examples": problems[:5]},
                         ensure_ascii=False))
        return 1
    seen = set()
    for row in rows:
        pair = normalize_options(row["options"])
        key = dedup_key(row["state"], row["question"], row["options"])
        if key in seen:
            print(f"PROBLEM 源内重复：dedup_key 相同，{row.get('id')}", file=sys.stderr)
            problems.append(f"duplicate source row {row.get('id')}")
            continue
        seen.add(key)
        plan.append({
            "record_id": record_id(row, len(plan)),
            "source": {"dataset": row["dataset"], "revision": row["revision"],
                       "line_number": row["line_number"], "license": row["license"],
                       "split": row["split"], "group_id": row.get("group_id", row.get("id")),
                       "source_row_id": row.get("id")},
            "kind": row["kind"],
            "en": {"state": row["state"], "question": row["question"],
                   "options": [{"key": k, "label": v} for k, v in pair]},
            "original_target_ref": row.get("target"),
            "source_dedup_key": key,
        })
    if problems:
        print(json.dumps({"status": "failed", "problems": len(problems)}, ensure_ascii=False))
        return 1
    out = Path(args.out)
    write_jsonl(out / "rewrite-plan.jsonl", plan)
    manifest = {"tool": TOOL, "pipeline": PIPELINE_VERSION, "state": "prepared",
                "source": str(args.source), "candidates": str(args.candidates),
                "records": len(plan), "rewrite_prompt_version": REWRITE_PROMPT_VERSION,
                "judge_prompt_version": JUDGE_PROMPT_VERSION,
                "target_visible_to_teachers": False, "created_at": iso_now()}
    write_json(out / "plan.json", manifest)
    print(json.dumps({"status": "ok", "out": str(out), "records": len(plan),
                      "target_visible_to_teachers": False}, ensure_ascii=False))
    return 0


def fixture_rewrite(plan_row):
    """Deterministic offline pseudo-rewrite: clearly marked, never mistaken for a real translation."""
    state = plan_row["en"]["state"]
    question = plan_row["en"]["question"]
    return {"state": f"【fixture 伪改写，非真实翻译】{state}",
            "question": f"【fixture 伪改写，非真实翻译】{question}",
            "model": "fixture-rewriter", "lineage": "fixture-rewrite"}


def fixture_judge(plan_row, zh):
    """Deterministic offline pseudo-judgement derived from the record hash (never ground truth)."""
    digest = hashlib.sha256((plan_row["record_id"] + zh["question"]).encode("utf-8")).digest()
    keys = [option["key"] for option in plan_row["en"]["options"]]
    weights = [1 + digest[index % len(digest)] for index in range(len(keys))]
    total = float(sum(weights))
    probs = {key: round(weight / total, 6) for key, weight in zip(keys, weights)}
    answer = max(probs, key=probs.get)
    return {"answer": answer, "probs": probs, "model": "fixture-judge", "lineage": "fixture-judge"}


def build_record(plan_row, zh, judgement, fixture, created_at, rewrite_model, judge_model):
    return {
        "record_id": plan_row["record_id"],
        "source": plan_row["source"],
        "kind": plan_row["kind"],
        "zh": {"state": zh["state"], "question": zh["question"], "options": plan_row["en"]["options"]},
        "original": {"state": plan_row["en"]["state"], "question": plan_row["en"]["question"],
                     "options": plan_row["en"]["options"], "target": plan_row["original_target_ref"]},
        "label": {"answer": judgement["answer"], "probs": judgement.get("probs")},
        "label_source": "judge",
        "judge": {"model": judge_model, "lineage": judgement["lineage"],
                  "prompt_version": JUDGE_PROMPT_VERSION, "answered_without_original_target": True},
        "rewrite": {"model": rewrite_model, "lineage": zh["lineage"],
                    "prompt_version": REWRITE_PROMPT_VERSION},
        "dedup_key": dedup_key(zh["state"], zh["question"], plan_row["en"]["options"]),
        "fixture": fixture,
        "usable_for_training": not fixture,
        "created_at": created_at,
    }


def chat_completion(endpoint, model, system, user, key, timeout=120.0, max_tokens=1024):
    payload = {"model": model, "max_tokens": max_tokens,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": USER_AGENT, "Authorization": "Bearer " + key},
        method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    message = body["choices"][0]["message"]
    return message.get("content") or message.get("reasoning_content")


def render_rewrite_prompt(plan_row):
    options = "\n".join(f"- {option['key']}: {option['label']}" for option in plan_row["en"]["options"])
    return (f"【英文场景】\n{plan_row['en']['state']}\n\n【英文问题】\n{plan_row['en']['question']}\n\n"
            f"【选项】\n{options}\n\n请输出 JSON：{{\"state\": <中文场景>, \"question\": <中文问题>}}")


def render_judge_prompt(plan_row, zh):
    options = "\n".join(f"- {option['key']}: {option['label']}" for option in plan_row["en"]["options"])
    return (f"【中文场景】\n{zh['state']}\n\n【中文问题】\n{zh['question']}\n\n【选项】\n{options}")


def parse_json_object(text):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start:end + 1])


def cmd_run(args):
    out = Path(args.out)
    plan_path = out / "rewrite-plan.jsonl"
    if not plan_path.exists():
        print(json.dumps({"status": "failed", "problems": ["先跑 prepare 生成改写请求包"]},
                         ensure_ascii=False))
        return 2
    plan = read_jsonl(plan_path)
    if args.limit:
        plan = plan[:args.limit]
    created_at = iso_now()
    if args.fixture:
        records = []
        for plan_row in plan:
            zh = fixture_rewrite(plan_row)
            judgement = fixture_judge(plan_row, zh)
            records.append(build_record(plan_row, zh, judgement, True, created_at,
                                        zh["model"], judgement["model"]))
        write_jsonl(out / "zh.records.jsonl", records)
        calls = [{"record_id": row["record_id"], "stage": "fixture", "ok": True} for row in records]
        write_jsonl(out / "calls.jsonl", calls)
        print(json.dumps({"status": "ok", "mode": "fixture", "records": len(records),
                          "usable_for_training": False,
                          "note": "fixture 产物不是翻译也不是真值，只能用来跑通链路"},
                         ensure_ascii=False))
        return 0

    # ---- live：默认拒绝，必须显式批准 ----
    required = {"--endpoint": args.endpoint, "--rewrite-model": args.rewrite_model,
                "--judge-model": args.judge_model,
                "--approved-by-lead": args.approved_by_lead}
    missing = [flag for flag, value in required.items() if not value]
    if missing:
        print(json.dumps({"status": "refused", "missing": missing,
                          "note": "真实改写会调用付费 API，须 Lead 批准；缺任何一项都不执行"},
                         ensure_ascii=False))
        return 2
    if args.rewrite_lineage == args.judge_lineage:
        print(json.dumps({"status": "refused",
                          "note": "改写与重判必须不同血缘，否则不是独立判断"}, ensure_ascii=False))
        return 2
    key = os.environ.get(args.key_env, "")
    if not key and args.key_file:
        key = Path(args.key_file).read_text(encoding="utf-8").strip()
    if not key:
        print(json.dumps({"status": "refused", "missing": [args.key_env]}, ensure_ascii=False))
        return 2
    records, calls = [], []
    for plan_row in plan:
        try:
            rewrite_raw = chat_completion(args.endpoint, args.rewrite_model, REWRITE_SYSTEM,
                                          render_rewrite_prompt(plan_row), key, timeout=args.timeout)
            parsed = parse_json_object(rewrite_raw)
            zh = {"state": parsed["state"], "question": parsed["question"],
                  "model": args.rewrite_model, "lineage": args.rewrite_lineage}
            judge_raw = chat_completion(args.endpoint, args.judge_model, JUDGE_SYSTEM,
                                        render_judge_prompt(plan_row, zh), key, timeout=args.timeout)
            judgement = parse_json_object(judge_raw)
            judgement.setdefault("lineage", args.judge_lineage)
            judgement["lineage"] = args.judge_lineage
            records.append(build_record(plan_row, zh, judgement, False, created_at,
                                        args.rewrite_model, args.judge_model))
            calls.append({"record_id": plan_row["record_id"], "stage": "live", "ok": True,
                          "rewrite_model": args.rewrite_model, "judge_model": args.judge_model})
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError,
                ValueError, OSError) as error:
            calls.append({"record_id": plan_row["record_id"], "stage": "live", "ok": False,
                          "error": str(error)[:300]})
    write_jsonl(out / "zh.records.jsonl", records)
    write_jsonl(out / "calls.jsonl", calls)
    ok = sum(1 for call in calls if call["ok"])
    print(json.dumps({"status": "ok" if ok == len(calls) else "partial", "mode": "live",
                      "records": len(records), "calls": len(calls), "ok": ok},
                     ensure_ascii=False))
    return 0 if ok == len(calls) else 1


def verify_records(records):
    """Return (problems, stats). 硬规则：重判、独立血缘、不照搬英文标签、分区与许可合规。"""
    problems = []
    stats = {"records": len(records), "agree_with_english_target": 0, "fixture": 0}
    seen = {}
    for record in records:
        rid = record.get("record_id", "?")
        source = record.get("source") or {}
        for field in ("dataset", "revision", "line_number", "license", "split"):
            if field not in source:
                problems.append(f"{rid}: 溯源缺字段 {field}")
        if source.get("split") not in ALLOWED_SPLITS:
            problems.append(f"{rid}: split={source.get('split')!r} 不是 train")
        if str(source.get("license", "")).lower() not in ALLOWED_LICENSES:
            problems.append(f"{rid}: 许可 {source.get('license')!r} 不在白名单")
        if not SHA_RE.match(str(source.get("revision", ""))):
            problems.append(f"{rid}: revision 不是固定 sha")
        if record.get("label_source") != "judge":
            problems.append(f"{rid}: label_source={record.get('label_source')!r}，真值只能来自重判")
        judge = record.get("judge") or {}
        rewrite = record.get("rewrite") or {}
        if not judge.get("model"):
            problems.append(f"{rid}: 缺重判模型信息")
        if judge.get("model") == rewrite.get("model"):
            problems.append(f"{rid}: 改写与重判同模型，不是独立判断")
        if judge.get("lineage") == rewrite.get("lineage"):
            problems.append(f"{rid}: 改写与重判同血缘")
        if judge.get("answered_without_original_target") is not True:
            problems.append(f"{rid}: 重判教师看到了英文标签或缺少声明")
        zh = record.get("zh") or {}
        original = record.get("original") or {}
        if not zh.get("state") or not zh.get("question"):
            problems.append(f"{rid}: 缺中文 state/question")
        if normalize_text(zh.get("state")) == normalize_text(original.get("state")):
            problems.append(f"{rid}: 中文 state 与英文原文完全相同，未真正改写")
        expected = dedup_key(zh.get("state", ""), zh.get("question", ""), zh.get("options"))
        if record.get("dedup_key") != expected:
            problems.append(f"{rid}: dedup_key 与中文内容不一致（改写后未重算）")
        if expected in seen:
            problems.append(f"{rid}: 与 {seen[expected]} 中文内容重复（去重门）")
        seen[expected] = rid
        label = record.get("label") or {}
        if label.get("answer") in (None, ""):
            problems.append(f"{rid}: 缺重判答案")
        target = original.get("target")
        if target is not None and label.get("answer") is not None:
            if isinstance(target, dict) and target:
                best = max(target, key=target.get)
                if str(best) == str(label["answer"]) :
                    stats["agree_with_english_target"] += 1
            elif isinstance(target, list) and target:
                if len(target) == len(zh.get("options") or []):
                    best = max(range(len(target)), key=lambda i: target[i])
                    keys = [option["key"] for option in zh.get("options") or []]
                    if str(keys[best]) == str(label["answer"]):
                        stats["agree_with_english_target"] += 1
        if record.get("fixture"):
            stats["fixture"] += 1
            if record.get("usable_for_training"):
                problems.append(f"{rid}: fixture 记录不得 usable_for_training")
        if record.get("usable_for_training") is not True and not record.get("fixture"):
            problems.append(f"{rid}: 非 fixture 记录的 usable_for_training 必须是 true")
    return problems, stats


def cmd_verify(args):
    records = read_jsonl(args.records)
    problems, stats = verify_records(records)
    result = {"status": "ok" if not problems else "failed", "records": str(args.records),
              "stats": stats, "problems": problems[:50], "problem_count": len(problems)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not problems else 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="读英文决策样本，产出改写请求包（教师看不到标签）")
    prepare.add_argument("--source", type=Path, required=True, help="规范化英文样本 JSONL")
    prepare.add_argument("--candidates", type=Path,
                         default=Path(__file__).with_name("candidates.json"))
    prepare.add_argument("--out", type=Path, required=True)
    prepare.set_defaults(func=cmd_prepare)

    run = sub.add_parser("run", help="改写 + 重判（默认只跑 --fixture 离线链路）")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--fixture", action="store_true", help="离线确定性伪改写/伪重判")
    run.add_argument("--limit", type=int)
    run.add_argument("--endpoint")
    run.add_argument("--rewrite-model")
    run.add_argument("--judge-model")
    run.add_argument("--rewrite-lineage", default="rewrite-a")
    run.add_argument("--judge-lineage", default="judge-b")
    run.add_argument("--key-env", default="REWRITE_API_KEY")
    run.add_argument("--key-file", type=Path)
    run.add_argument("--timeout", type=float, default=120.0)
    run.add_argument("--approved-by-lead", action="store_true",
                     help="确认 Lead 已批准本次真实调用")
    run.set_defaults(func=cmd_run)

    verify = sub.add_parser("verify", help="校验溯源、血缘独立、去重与未照搬英文标签")
    verify.add_argument("--records", type=Path, required=True)
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"rewrite: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
