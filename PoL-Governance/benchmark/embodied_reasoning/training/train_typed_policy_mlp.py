"""Train a compact, typed action-choice model from the v0.2 contract.

The contract gate remains the hard safety boundary. This model only ranks the
actions that the gate admits. Labels are programmatically derived, not gold.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
PRIVATE_TEST = Path(r"D:\cache\pol2-embodied-train\private_holdout.jsonl")
RESULTS = HERE / "training_metrics.json"
CHECKPOINT = HERE / "pol2-contract-v0.1.pt"
POLICY = HERE.parent / "pol2-embodied-contract-v0.2.json"
POLICY_SHA256 = hashlib.sha256(POLICY.read_bytes()).hexdigest()
SEED = 20261023
ACTION_ORDER = ("transfer", "inspect", "wait", "done")
PERMISSIONS = ("GRANTED", "DENIED", "UNKNOWN")
SCOPES = ("MATCH", "MISMATCH", "UNKNOWN")
FRESHNESS = ("FRESH", "STALE")
LOCATIONS = ("SOURCE", "TARGET", "OTHER", "UNKNOWN")


class TypedPolicy(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(17, 64), nn.GELU(),
            nn.Linear(64, 32), nn.GELU(),
            nn.Linear(32, len(ACTION_ORDER)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def one_hot(value: str, choices: tuple[str, ...]) -> list[float]:
    if value not in choices:
        raise ValueError(f"unexpected typed field value {value!r}; expected {choices}")
    return [float(value == choice) for choice in choices]


def features(row: dict) -> tuple[list[float], list[float], int]:
    permission, scope, fresh, location, terminal = row["typed_state"]
    candidate_bits = [float(action in row["candidates"]) for action in ACTION_ORDER]
    x = one_hot(permission, PERMISSIONS) + one_hot(scope, SCOPES) + one_hot(fresh, FRESHNESS)
    x += one_hot(location, LOCATIONS) + [float(terminal)] + candidate_bits
    mask = candidate_bits
    return x, mask, ACTION_ORDER.index(row["label"])


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def tensorize(rows: list[dict]):
    items = [features(row) for row in rows]
    x = torch.tensor([item[0] for item in items], dtype=torch.float32)
    mask = torch.tensor([item[1] for item in items], dtype=torch.bool)
    y = torch.tensor([item[2] for item in items], dtype=torch.long)
    return x, mask, y


def score(model: nn.Module, rows: list[dict]) -> dict:
    x, mask, y = tensorize(rows)
    eligible = torch.tensor(
        [[action in row["eligible_actions"] for action in ACTION_ORDER] for row in rows],
        dtype=torch.bool,
    )
    model.eval()
    with torch.no_grad():
        logits = model(x).masked_fill(~mask, -1e9)
        pred = logits.argmax(dim=1)
    correct = pred.eq(y)
    by_action = {}
    for idx, action in enumerate(ACTION_ORDER):
        selected = y.eq(idx)
        by_action[action] = {
            "n": int(selected.sum()),
            "accuracy": float(correct[selected].float().mean()) if bool(selected.any()) else None,
        }
    return {
        "n": len(rows),
        "accuracy": float(correct.float().mean()),
        "predictions_outside_contract_eligible_set": int((~eligible.gather(1, pred[:, None]).squeeze(1)).sum()),
        "gold_action_counts": dict(Counter(row["label"] for row in rows)),
        "by_gold_action": by_action,
    }


def main() -> None:
    random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    train_rows = read_rows(DATA / "train.jsonl")
    validation_rows = read_rows(DATA / "validation.jsonl")
    train_x, train_mask, train_y = tensorize(train_rows)
    train_ds = TensorDataset(train_x, train_mask, train_y)
    loader = DataLoader(train_ds, batch_size=128, shuffle=True, generator=torch.Generator().manual_seed(SEED))

    model = TypedPolicy()
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    best_state, best_val, best_epoch, patience, stale = None, float("inf"), 0, 20, 0
    history = []
    for epoch in range(1, 301):
        model.train()
        for bx, bm, by in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(bx).masked_fill(~bm, -1e9)
            loss = nn.functional.cross_entropy(logits, by)
            loss.backward()
            optimizer.step()
        vx, vm, vy = tensorize(validation_rows)
        model.eval()
        with torch.no_grad():
            val_logits = model(vx).masked_fill(~vm, -1e9)
            val_loss = float(nn.functional.cross_entropy(val_logits, vy))
        history.append({"epoch": epoch, "validation_loss": val_loss})
        if val_loss < best_val - 1e-6:
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            best_val, best_epoch, stale = val_loss, epoch, 0
        else:
            stale += 1
        if stale >= patience:
            break

    model.load_state_dict(best_state)
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": model.state_dict(),
        "architecture": "mlp-17x64x32x4-gelu",
        "action_order": ACTION_ORDER,
        "typed_fields": {"permission": PERMISSIONS, "scope": SCOPES, "freshness": FRESHNESS, "location": LOCATIONS, "terminal": "bool", "candidate_mask": ACTION_ORDER},
        "policy_id": "pol2-embodied-contract-v0.2",
        "policy_sha256": POLICY_SHA256,
        "seed": SEED,
        "label_provenance": "programmatic contract distillation; not human gold",
    }, CHECKPOINT)
    validation_metrics = score(model, validation_rows)

    # Read the outside-repository holdout only after weights and early stopping are frozen.
    test_rows = read_rows(PRIVATE_TEST)
    test_metrics = score(model, test_rows)
    metrics = {
        "experiment": "typed-action-policy contract-distillation v0.1",
        "base_model": "17-field MLP; no pretrained language model",
        "policy_id": "pol2-embodied-contract-v0.2",
        "policy_sha256": POLICY_SHA256,
        "seed": SEED,
        "training_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "private_holdout_rows": len(test_rows),
        "train_family_overlap_with_validation": len({r["family_id"] for r in train_rows} & {r["family_id"] for r in validation_rows}),
        "train_family_overlap_with_private_holdout": len({r["family_id"] for r in train_rows} & {r["family_id"] for r in test_rows}),
        "validation": validation_metrics,
        "private_holdout": test_metrics,
        "best_epoch": best_epoch,
        "epochs_run": len(history),
        "checkpoint_path": CHECKPOINT.name,
        "checkpoint_sha256": hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest(),
        "class_counts_train": dict(Counter(r["label"] for r in train_rows)),
        "history": history,
        "limits": [
            "all states and labels are synthetic and generated from the same operationalized contract",
            "input is already typed; model does not parse natural-language instructions or perceive images",
            "hard candidate gate is still required; zero invalid outputs are guaranteed by masking, not learned behavior",
            "results measure rule distillation on held-out factor combinations, not causal PoL2 benefit",
        ],
    }
    RESULTS.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k not in {"history", "limits"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
