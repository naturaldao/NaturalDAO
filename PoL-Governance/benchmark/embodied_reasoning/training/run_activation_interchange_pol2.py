"""Causal interchange interventions on Kev typed-choice PoL2 state representations.

The intervention exchanges residual activations at one trusted-field value between exact
minimal counterfactuals. This is a mechanistic diagnostic on one frozen operational
contract, not evidence of unrestricted or subjective theory possession.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_kev_pol2_internalization as pilot

RUN = HERE / "results" / "kev-pol2-counterfactual-causal-20261026"
DEFAULT_OUT = RUN / "activation_interchange"
SEEDS = (20261026, 20261027, 20261028)
FACTORS = {
    "authorization": ("GRANTED", "DENIED", "transfer"),
    "scope": ("MATCH", "MISMATCH", "transfer"),
    "freshness": ("FRESH", "STALE", "transfer"),
    "location": ("SOURCE", "OTHER", "transfer"),
    "terminal": ("True", "False", "done"),
}
FIELD_PREFIX = {
    "authorization": "授权账本=",
    "scope": "登记范围=",
    "freshness": "观测新鲜度=",
    "location": "物体位置=",
    "terminal": "仿真完成谓词=",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def get_cases():
    rows = pilot.build_rows()["test"]
    out = {}
    base_state = ("GRANTED", "MATCH", "FRESH", "SOURCE", False)
    base = next(r for r in rows if r["instruction_family"] == "move" and tuple(r["typed_state"]) == base_state)
    for factor, (positive, negative, action) in FACTORS.items():
        pos = list(FACTORS).index(factor)
        a, b = list(base_state), list(base_state)
        if factor == "terminal":
            a[pos], b[pos] = True, False
        else:
            a[pos], b[pos] = positive, negative
        ra, rb = dict(base), dict(base)
        ra["typed_state"], rb["typed_state"] = a, b
        ra["state_family"], rb["state_family"] = "|".join(map(str, a)), "|".join(map(str, b))
        ra["id"], rb["id"] = f"mechanism-{factor}-positive", f"mechanism-{factor}-negative"
        old = str(base_state[pos]).lower() if factor == "terminal" else str(base_state[pos])
        new_a = str(a[pos]).lower() if factor == "terminal" else str(a[pos])
        new_b = str(b[pos]).lower() if factor == "terminal" else str(b[pos])
        field_marker = FIELD_PREFIX[factor]
        ra["state_text"] = ra["state_text"].replace(field_marker + old, field_marker + new_a, 1)
        rb["state_text"] = rb["state_text"].replace(field_marker + old, field_marker + new_b, 1)
        ra["options"], rb["options"] = list(pilot.ACTION_ORDER), list(pilot.ACTION_ORDER)
        ra["policy_action"], rb["policy_action"] = action, pilot.policy_target(tuple(b))[0]
        ra["policy_action_index"] = ra["options"].index(ra["policy_action"])
        rb["policy_action_index"] = rb["options"].index(rb["policy_action"])
        if ra["state_text"].replace(field_marker + new_a, field_marker + "<VALUE>", 1) != rb["state_text"].replace(field_marker + new_b, field_marker + "<VALUE>", 1):
            raise RuntimeError(f"{factor}: minimal pair differs outside the selected field")
        # Same state and selected fact, but alternate request wording after all state fields.
        paraphrase = dict(rb)
        alt = "請將登記物品移至指定托盤。"
        paraphrase["instruction"] = alt
        paraphrase["state_text"] = paraphrase["state_text"].rsplit("当前用户任务文本：", 1)[0] + "当前用户任务文本：" + alt
        out[factor] = {"positive": ra, "negative": rb, "control": paraphrase, "action": action}
    return out


def encode(model, tok, row, arm):
    return pilot.encode_row(model, tok, row, arm)


def action_margin(logits, action):
    z = logits.float()
    idx = pilot.ACTION_ORDER.index(action)
    other = torch.cat((z[:idx], z[idx + 1:]))
    return float((z[idx] - torch.logsumexp(other, dim=0)).detach().cpu())


def top_action(logits):
    return pilot.ACTION_ORDER[int(torch.argmax(logits.float()).detach().cpu())]


def value_span(tok, row, factor, enc):
    """Token indices overlapping only the changed trusted-field value (offset 0 is <state>)."""
    text = row["state_text"]
    marker = FIELD_PREFIX[factor]
    start = text.index(marker) + len(marker)
    end = start + len(str(row["typed_state"][list(FACTORS).index(factor)]))
    offsets = tok(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
    span = [i + 1 for i, (a, b) in enumerate(offsets) if a < end and b > start]
    if not span or max(span) >= enc["state_tokens"]:
        raise RuntimeError(f"could not align {factor} value span for {row['id']}: {span}")
    return span


def layers_of(model):
    layers = model.lm.base_model.model.layers
    if len(layers) != 24:
        raise RuntimeError(f"Expected pinned Qwen3.5-0.8B 24 blocks, found {len(layers)}")
    return layers


def capture(model, enc):
    saved = {}
    layers = layers_of(model)
    handles = []
    for i, layer in enumerate(layers):
        def hook(_module, _inputs, output, i=i):
            tensor = output[0] if isinstance(output, tuple) else output
            saved[i] = tensor.detach()
        handles.append(layer.register_forward_hook(hook))
    with torch.inference_mode():
        logits = model.forward(enc)[0]
    for handle in handles:
        handle.remove()
    return logits, saved


def patched_forward(model, enc, donor, donor_indices, target_indices, layer_indices):
    layers = layers_of(model)
    handles = []
    for i in layer_indices:
        def hook(_module, _inputs, output, i=i):
            tensor = output[0] if isinstance(output, tuple) else output
            changed = tensor.clone()
            donor_value = donor[i][0, donor_indices].float()
            if len(donor_indices) == len(target_indices):
                aligned = donor_value
            else:
                aligned = F.interpolate(donor_value.T.unsqueeze(0), size=len(target_indices), mode="linear", align_corners=True)[0].T
            changed[0, target_indices] = aligned.to(changed.dtype)
            return (changed, *output[1:]) if isinstance(output, tuple) else changed
        handles.append(layers[i].register_forward_hook(hook))
    try:
        with torch.inference_mode():
            logits = model.forward(enc)[0]
    finally:
        for handle in handles:
            handle.remove()
    return logits


def run_seed(seed: int, cases: dict, device: str, arm: str):
    from kev.checkpoint import Checkpoint, LoadOptions
    adapter = RUN / "adapters" / arm / f"seed-{seed}"
    tok, model = Checkpoint(str(adapter)).load(device, LoadOptions(dtype=torch.bfloat16, merge=False))
    model.eval()
    results = []
    n_layers = len(layers_of(model))
    for factor, case in cases.items():
        enc_pos, enc_neg, enc_ctl = (encode(model, tok, case[k], arm) for k in ("positive", "negative", "control"))
        pos_idx = value_span(tok, case["positive"], factor, enc_pos)
        neg_idx = value_span(tok, case["negative"], factor, enc_neg)
        ctl_idx = value_span(tok, case["control"], factor, enc_ctl)
        lp, hp = capture(model, enc_pos)
        ln, hn = capture(model, enc_neg)
        lc, hc = capture(model, enc_ctl)
        action = case["action"]
        target_pos, target_neg = case["positive"]["policy_action"], case["negative"]["policy_action"]
        m_pos, m_neg, m_ctl = action_margin(lp, action), action_margin(ln, action), action_margin(lc, action)
        # Interchange every block's state-endpoint residual to estimate total causal transfer.
        pos_into_neg = patched_forward(model, enc_neg, hp, pos_idx, neg_idx, range(n_layers))
        neg_into_pos = patched_forward(model, enc_pos, hn, neg_idx, pos_idx, range(n_layers))
        # The clause value is unchanged; the donor differs only in later request wording.
        # Causal token ordering predicts a near-zero effect at this field position.
        control_into_neg = patched_forward(model, enc_neg, hc, ctl_idx, neg_idx, range(n_layers))
        full_pos_to_neg = action_margin(pos_into_neg, action) - m_neg
        full_neg_to_pos = action_margin(neg_into_pos, action) - m_pos
        ctrl_effect = action_margin(control_into_neg, action) - m_neg
        results.append({
            "arm": arm, "factor": factor, "seed": seed, "action_margin": action,
            "positive_policy_target": target_pos, "negative_policy_target": target_neg,
            "positive_clean_prediction": top_action(lp), "negative_clean_prediction": top_action(ln),
            "positive_to_negative_prediction": top_action(pos_into_neg),
            "negative_to_positive_prediction": top_action(neg_into_pos),
            "same_value_placebo_prediction": top_action(control_into_neg),
            "positive_clean_margin": m_pos, "negative_clean_margin": m_neg,
            "positive_state_into_negative_delta": full_pos_to_neg,
            "negative_state_into_positive_delta": full_neg_to_pos,
            "same_state_paraphrase_control_delta": ctrl_effect,
            "same_state_control_field_activation_max_abs_diff_by_layer": [
                float((hc[i][0, ctl_idx].float().mean(dim=0) - hn[i][0, neg_idx].float().mean(dim=0)).abs().max().cpu())
                for i in range(n_layers)
            ],
            "field_token_span_lengths": {"positive": len(pos_idx), "negative": len(neg_idx), "control": len(ctl_idx)},
            "positive_to_negative_layer_sweep": [], "negative_to_positive_layer_sweep": [],
        })
        # Single-block localization on authorization only; other factors get the full-path test.
        if factor == "authorization":
            for layer in range(n_layers):
                p2n = patched_forward(model, enc_neg, hp, pos_idx, neg_idx, [layer])
                n2p = patched_forward(model, enc_pos, hn, neg_idx, pos_idx, [layer])
                results[-1]["positive_to_negative_layer_sweep"].append(action_margin(p2n, action) - m_neg)
                results[-1]["negative_to_positive_layer_sweep"].append(action_margin(n2p, action) - m_pos)
        del enc_pos, enc_neg, enc_ctl, lp, ln, lc, hp, hn, hc
        if str(device).startswith("cuda"):
            torch.cuda.empty_cache()
    del model, tok
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="cuda")
    p.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    p.add_argument("--arms", choices=("pol2_sft", "task_only"), nargs="+", default=["pol2_sft", "task_only"])
    p.add_argument("--output", type=Path, default=DEFAULT_OUT / "results.json")
    args = p.parse_args()
    cases = get_cases()
    all_rows = []
    for arm in args.arms:
        for seed in args.seeds:
            print(f"[activation interchange] arm={arm} seed={seed}", flush=True)
            all_rows.extend(run_seed(seed, cases, args.device, arm))
    factors = {arm: {} for arm in args.arms}
    for arm in args.arms:
        for factor in FACTORS:
            subset = [r for r in all_rows if r["arm"] == arm and r["factor"] == factor]
            factors[arm][factor] = {
                "positive_state_into_negative_mean": statistics.mean(r["positive_state_into_negative_delta"] for r in subset),
                "negative_state_into_positive_mean": statistics.mean(r["negative_state_into_positive_delta"] for r in subset),
                "same_state_control_mean": statistics.mean(r["same_state_paraphrase_control_delta"] for r in subset),
                "n_seed_pairs": len(subset),
            }
    payload = {
        "experiment": "Bidirectional state-token activation interchange for PoL2 contract variables",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "design": {
            "checkpoint": "Kev 0.8B + matched PoL2-contract SFT and task-only LoRA arms; three existing seeds per arm",
            "intervention": "exchange only residual activations overlapping the changed trusted-field value token(s), at all transformer blocks",
            "minimal_pairs": {k: {"positive": v["positive"]["typed_state"], "negative": v["negative"]["typed_state"], "target_action": v["action"]} for k, v in cases.items()},
            "controls": ["reverse-direction field-value interchange", "same clause value with a later alternate request as causal-position placebo"],
            "comparison": "task_only is a matched SFT objective control; both arms use the same base, state pairs, seeds, and evaluation procedure",
            "primary_metric": "target-action logit minus logsumexp of the other three candidate logits",
            "unit": "seed x one exact one-field minimal pair per contract factor; exploratory mechanistic diagnostic",
            "limitations": [
                "The tested contract is a narrow synthetic operationalization, not complete PoL2.",
                "Activation exchange at the state boundary does not establish a unique or complete internal algorithm.",
                "The same deterministic contract generated supervision and test targets.",
                "Three seeds and one canonical pair per factor do not support population-level inference.",
                "The result is evidence about this model, checkpoint, and specific intervention distribution only."
            ],
            "adapter_sha256": {f"{arm}:{s}": sha256(RUN / "adapters" / arm / f"seed-{s}" / "adapter_model.safetensors") for arm in args.arms for s in args.seeds},
        },
        "factor_summary": factors,
        "seed_results": all_rows,
        "authorization_layer_sweep": [r for r in all_rows if r["factor"] == "authorization"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(factors, ensure_ascii=False, indent=2), flush=True)
    print(f"wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
