"""Run local Ollama models on typed PoL2 knowledge tasks, without training."""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DATA = HERE / "data-v1.3"
DEFAULT_OUT = HERE / "runs-20261026-v1.3"
TYPES = ["concepts_relations", "axioms_propositions", "love_languages", "explicit_governance_rules", "researcher_interpretations"]
def schema_for(qids: list[str]) -> dict:
    return {
    "type": "object",
    "properties": {"answers": {"type": "array", "minItems": len(qids), "maxItems": len(qids), "items": {
        "type": "object",
        "properties": {"qid": {"type": "string", "enum": qids}, "answer": {"type": "string"}},
        "required": ["qid", "answer"],
    }}},
    "required": ["answers"],
    }


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def request(model: str, system: str, prompt: str, num_gpu: int, schema: dict) -> tuple[dict, str, str]:
    payload = json.dumps({
        "model": model, "stream": False, "format": schema, "keep_alive": "10m",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "options": {"temperature": 0, "num_ctx": 16384, "num_predict": 8192, "num_gpu": num_gpu},
    }).encode("utf-8")
    req = urllib.request.Request("http://localhost:11434/api/chat", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as response:
        raw = response.read().decode("utf-8")
    envelope = json.loads(raw)
    content = envelope["message"]["content"]
    return json.loads(content), envelope.get("model", model), content


def canonical_answer(value: str) -> str:
    return "|".join(sorted({x.strip() for x in value.split("|") if x.strip()}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["llama3.1:8b", "qwen2.5:7b"])
    parser.add_argument("--conditions", nargs="+", choices=["closed_book", "source_context"], default=["closed_book", "source_context"])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--num-gpu", type=int, default=0, help="Ollama GPU layers; default 0 keeps this pilot off the active GPU job")
    parser.add_argument("--max-items-per-type", type=int, default=0, help="Optional smoke limit; 0 means all items")
    parser.add_argument("--knowledge-types", nargs="+", choices=TYPES, default=TYPES)
    parser.add_argument("--batch-size", type=int, default=8, help="Checkpoint predictions in small batches")
    args = parser.parse_args()
    items = read_jsonl(DATA / "items.jsonl")
    labels = {x["id"]: x for x in read_jsonl(DATA / "labels.jsonl")}
    if len(items) != len(labels) or {x["id"] for x in items} != set(labels):
        raise SystemExit("items and labels are not a one-to-one id match")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = DATA / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    system = (
        "你在完成一个分类型知识检索评测。逐题独立作答，只根据题干、选项和（若提供）记录上下文。"
        "不得推断未给出的新规则或优先级。每题只输出选项 key；多选题将所有选中的 key 去重后按字典序用 | 连接。"
        "如果依据不足则仍按现有证据选择最有依据的 key；不要输出解释或思维过程。"
    )
    for model in args.models:
        for condition in args.conditions:
            for knowledge_type in args.knowledge_types:
                subset = [x for x in items if x["knowledge_type"] == knowledge_type]
                run_id = f"{model.replace(':','-')}__{condition}__{knowledge_type}.jsonl"
                if (args.output / run_id).exists():
                    print(f"SKIP existing full batch {run_id}", flush=True)
                    continue
                # The opaque IDs are deliberately detached from knowledge IDs so
                # IDs such as REL-001 cannot reveal the answer.
                order = sorted(subset, key=lambda x: uuid.uuid5(uuid.NAMESPACE_URL, f"{manifest['seed']}:{knowledge_type}:{x['id']}").hex)
                if args.max_items_per_type:
                    order = order[:args.max_items_per_type]
                chunks = [order[i:i + args.batch_size] for i in range(0, len(order), args.batch_size)]
                for part, chunk in enumerate(chunks, start=1):
                    part_name = run_id.replace(".jsonl", f".part{part:02d}.jsonl")
                    out_path = args.output / part_name
                    if out_path.exists():
                        print(f"SKIP existing {part_name}", flush=True)
                        continue
                    qid_to_item = {f"Q{i+1:03d}": row for i, row in enumerate(chunk)}
                    task_rows = []
                    for qid, row in qid_to_item.items():
                        task = {"qid": qid, "task_type": row["task_type"], "question": row["question"], "options": row["options"]}
                        if condition == "source_context":
                            task["source_evidence"] = row["source_context"]
                        task_rows.append(task)
                    prompt = (
                        f"知识类型：{knowledge_type}\n评测条件：{condition}\n"
                        "按给定 task_type 完成各自题目，不把不同题型压成同一判断。"
                        "答案输出为选项 key：单选只给一个；多选按字典序用 | 分隔。"
                        f"必须对以下每个 qid 各返回一条答案，不得省略或新增：{','.join(qid_to_item)}\n"
                        + json.dumps(task_rows, ensure_ascii=False)
                    )
                    start = time.perf_counter()
                    try:
                        result, returned_model, raw_content = request(model, system, prompt, args.num_gpu, schema_for(list(qid_to_item)))
                        elapsed = round((time.perf_counter() - start) * 1000, 2)
                        by_qid = {}
                        for ans in result.get("answers", []):
                            qid = str(ans["qid"])
                            if qid in by_qid:
                                raise ValueError(f"duplicate qid: {qid}")
                            by_qid[qid] = str(ans["answer"])
                        if set(by_qid) != set(qid_to_item):
                            raise ValueError(f"qid mismatch; missing={sorted(set(qid_to_item)-set(by_qid))}; extra={sorted(set(by_qid)-set(qid_to_item))}")
                        records = []
                        for qid, row in qid_to_item.items():
                            pred = by_qid[qid]
                            records.append({
                                "id": row["id"], "qid": qid, "knowledge_type": knowledge_type,
                                "task_type": row["task_type"], "model_requested": model,
                                "model_returned": returned_model, "condition": condition,
                                "num_gpu": args.num_gpu, "prediction": canonical_answer(pred),
                                "execution_status": "ok", "batch_latency_ms": elapsed, "batch_n": len(chunk),
                            })
                        out_path.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in records), encoding="utf-8")
                        (args.output / (part_name + ".response.json")).write_text(json.dumps({"response_content": raw_content, "parsed": result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                        print(json.dumps({"model": model, "condition": condition, "type": knowledge_type, "part": part, "n": len(chunk), "elapsed_ms": elapsed}, ensure_ascii=False), flush=True)
                    except Exception as exc:
                        elapsed = round((time.perf_counter() - start) * 1000, 2)
                        error = {"model": model, "condition": condition, "knowledge_type": knowledge_type, "part": part, "elapsed_ms": elapsed, "error": f"{type(exc).__name__}: {exc}"}
                        (args.output / (part_name + ".error.json")).write_text(json.dumps(error, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                        print(json.dumps(error, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
