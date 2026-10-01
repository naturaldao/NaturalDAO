#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Laya 本地决策模型微调脚本
================================

目标：
    state -> speech_type + eap_action

两个输出都作为 Laya 原生的 `choice` 问题训练：
    speech_type:
        love_speech
        hate_speech
        non_love_non_hate

    eap_action:
        amplify_love
        block_and_repair
        clarify_and_continue

重要：
    Laya 的 model.scorer 不是一个固定的 N 类 Linear。
    它对每一个 [MASK] 选项输出一个 scalar，然后在同一个 choice
    问题的选项之间做 softmax。因此 3 分类不需要把 scorer 改成
    out_features=3。

    Laya 的 model.act_head 是另外一个内部的 act/escalate 机制，
    不是本项目的 eap_action 三分类。因此本脚本不训练 act_head。

这样做的好处：
    1. 不修改 Laya 的模型结构；
    2. speech_type / eap_action 都是真正的 3-option choice；
    3. 保存后的 model.safetensors 可以直接由原版 laya.Agent 加载；
    4. Agent.predict() 可以直接返回两个 choice 结果。

数据格式：
[
  {
    "state": "你真是个废物，什么都做不好，难怪没人喜欢你。",
    "gold": {
      "speech_type": "hate_speech",
      "eap_action": "block_and_repair"
    }
  }
]

运行：
    python train_custom_gpt.py --data train_3.json --epochs 50 --batch-size 1

建议：
    先用 3 条数据跑 5 epoch 验证流程：
    python train_custom_gpt.py --data train_3.json --epochs 5 --batch-size 1

    流程正常后，再增加真实数据和 epoch。
"""

import os

# 在 torch 初始化 CUDA 前设置，减少显存碎片。
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("USE_TF", "0")

import argparse
import json
import shutil
import warnings

import torch
from torch.optim import AdamW

import laya


KEEP_DIRS = ("tokenizer", "encoder")


QUESTIONS = {
    "speech_type": {
        "type": "choice",
        "instructions": "这句话属于哪一种言语类型？",
        "criteria": {
            "love_speech": "真诚、尊重、共情、肯定、宽恕、平等连接",
            "hate_speech": "羞辱、去人化、敌意、排斥、控制、鼓吹暴力",
            "non_love_non_hate": "误解、打断、缺席等，既不是爱也不是仇恨",
        },
    },
    "eap_action": {
        "type": "choice",
        "instructions": "针对这句话，应该采取哪一种 EAP 行动？",
        "criteria": {
            "amplify_love": "确认并强化爱的表达，增强人与人之间的连接",
            "block_and_repair": "阻止仇恨表达，保护目标，并引导修复",
            "clarify_and_continue": "澄清误解并继续对话",
        },
    },
}


def load_samples(path):
    """读取 JSON 数据。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = raw.get("samples") if isinstance(raw, dict) else raw

    if not isinstance(rows, list) or not rows:
        raise ValueError(
            '%s 必须是 JSON 数组，或者 {"samples": [...]}'
            % path
        )

    return rows


def prepare_questions(agent):
    """
    将公开问题定义转换成 Laya 内部问题定义。

    注意：
    两个问题都属于 choice，因此每个 state 会产生两行训练数据。
    """
    from laya.common import render_options

    for qid, qdef in QUESTIONS.items():
        agent._check_question(qid, qdef)

    internal = {
        qid: agent._to_internal(qdef)
        for qid, qdef in QUESTIONS.items()
    }

    option_keys = {}

    for qid in QUESTIONS:
        crit = internal[qid]["crit"]

        if isinstance(crit, dict):
            keys = list(crit.keys())
        else:
            keys = list(range(len(crit or [])))

        rendered = render_options(internal[qid])

        if len(keys) != len(rendered):
            raise RuntimeError(
                "问题 %s: criteria=%d, rendered options=%d，不一致"
                % (qid, len(keys), len(rendered))
            )

        option_keys[qid] = keys

        print(
            "%s: %d 个选项 -> %s"
            % (qid, len(keys), ", ".join(map(str, keys)))
        )

    return internal, option_keys


def build_inputs(agent, samples, max_len, head_max_len):
    """
    将每个 state 编码成两个 choice rows：

        row 0 -> speech_type
        row 1 -> eap_action

    返回：
        batch
        supervised_count
    """
    from laya.common import collate_items, render_options

    internal, option_keys = prepare_questions(agent)

    items = []
    supervised = 0
    dropped = []

    for sample_index, sample in enumerate(samples):
        state = sample.get("state")

        if not isinstance(state, str) or not state.strip():
            raise ValueError(
                "sample %d 没有有效的 state 字符串"
                % sample_index
            )

        gold = sample.get("gold") or {}

        encoded = agent._encode_state(
            state,
            list(QUESTIONS),
            internal,
            max_len=max_len,
            head_max_len=head_max_len,
        )

        if len(encoded) != len(QUESTIONS):
            raise RuntimeError(
                "sample %d 编码后得到 %d 行，但应该是 %d 行"
                % (sample_index, len(encoded), len(QUESTIONS))
            )

        for qid, item in zip(QUESTIONS, encoded):
            label = gold.get(qid)

            if label is None:
                continue

            keys = option_keys[qid]

            if isinstance(label, str):
                probs = {label: 1.0}
            elif isinstance(label, dict):
                probs = dict(label)
            else:
                raise ValueError(
                    "sample %d: gold.%s 必须是字符串或者 "
                    "{label: probability}，实际是 %r"
                    % (sample_index, qid, label)
                )

            unknown = [k for k in probs if k not in keys]

            if unknown:
                raise ValueError(
                    "sample %d: gold.%s 存在未知标签 %s；允许值=%s"
                    % (
                        sample_index,
                        qid,
                        unknown,
                        keys,
                    )
                )

            target = [float(probs.get(k, 0.0)) for k in keys]
            total = sum(target)

            if total <= 0:
                dropped.append(
                    "sample %d: %s 没有有效概率"
                    % (sample_index, qid)
                )
                continue

            target = [v / total for v in target]

            item["target"] = target
            item["label"] = target.index(max(target))

            supervised += 1

        items.append(encoded)

    if not items:
        raise ValueError("没有可以训练的数据")

    if supervised == 0:
        raise ValueError(
            "没有找到可训练的 gold.speech_type / gold.eap_action"
        )

    print(
        "编码完成: %d 个样本, %d 个带可训练标签"
        % (len(items), supervised)
    )

    for note in dropped:
        print("  跳过标签: %s" % note)

    batch = collate_items(
        items,
        agent.tok.pad_token_id,
    )

    # sample_mask 是“训练行”的 mask。
    # 每个 state 有 speech_type / eap_action 两行。
    sample_mask = []

    for group in items:
        for item in group:
            ok = (
                item.get("target") is not None
                and item.get("label", -1) >= 0
            )
            sample_mask.append(1.0 if ok else 0.0)

    batch["sample_mask"] = torch.tensor(
        sample_mask,
        dtype=torch.float32,
    )

    # target 形状：
    # [训练行数, 3]
    #
    # 注意：它对应的是每一行 choice 问题自己的 3 个 options。
    if "target" not in batch:
        raise RuntimeError("collate_items 没有生成 target")

    return batch, supervised


def move_batch_to_device(batch, device):
    """
    将所有 tensor 一次性移动到模型所在设备。

    这是修复之前：
        index is on cpu, weight is on cuda:0
    的关键。
    """
    out = {}

    for key, value in batch.items():
        if torch.is_tensor(value):
            out[key] = value.to(device)
        else:
            out[key] = value

    return out


def forward_scorer(agent, batch):
    """
    使用 Laya 真正的 DecisionModel.forward。

    返回：
        logits: [rows, max_options]
        act_logits: Laya 自己的内部 act/escalate 输出

    本项目只训练 logits 对应的 choice scorer。
    """
    from laya.agent import _amp_context

    device = next(agent.model.parameters()).device

    batch = move_batch_to_device(batch, device)

    with _amp_context(
        agent.device,
        agent.dtype,
        agent.amp_enabled,
    ):
        logits, act_logits = agent.model(
            batch["input_ids"],
            batch["attention_mask"],
            batch["marker_pos"],
            batch["marker_mask"],
            batch["qtype"],
        )

    return logits, act_logits


def masked_choice_ce(
    logits,
    target,
    marker_mask,
    sample_mask,
):
    """
    对 Laya choice scorer 做 masked cross entropy。

    Laya 的 scorer 每个 marker 输出一个 scalar。
    例如 3 个 options：

        logits = [z0, z1, z2]

    softmax 后就是三个类别概率。

    marker_mask 用来忽略 padding / 不存在的 option。
    sample_mask 用来忽略没有 gold 的训练行。
    """
    selected = sample_mask > 0

    if not bool(selected.any()):
        return None

    logits = logits.float()
    target = target.float()

    selected_logits = logits[selected]
    selected_target = target[selected]
    selected_mask = marker_mask[selected]

    # target 中不存在的 option 归零。
    selected_target = torch.where(
        selected_mask,
        selected_target,
        torch.zeros_like(selected_target),
    )

    denom = selected_target.sum(
        dim=-1,
        keepdim=True,
    ).clamp_min(1e-9)

    selected_target = selected_target / denom

    selected_logits = selected_logits.masked_fill(
        ~selected_mask,
        -1e4,
    )

    logp = torch.log_softmax(
        selected_logits,
        dim=-1,
    )

    loss = -(
        selected_target * logp
    ).sum(dim=-1).mean()

    return loss


@torch.no_grad()
def evaluate_training_rows(
    agent,
    batch,
    title,
):
    """
    在训练数据本身上做一次直接 forward。

    这个检查非常重要：
    如果这里都不能学会，问题就在训练路径；
    如果这里能学会，而 Agent.predict() 不对，则问题在推理/加载路径。
    """
    was_training = agent.model.training
    agent.model.eval()

    device = next(agent.model.parameters()).device
    b = move_batch_to_device(batch, device)

    logits, _ = forward_scorer(agent, b)

    logits = logits.float()
    marker_mask = b["marker_mask"]
    sample_mask = b["sample_mask"]
    target = b["target"]

    rows = []

    for i in range(logits.shape[0]):
        if sample_mask[i].item() <= 0:
            continue

        valid = marker_mask[i]
        z = logits[i][valid]

        p = torch.softmax(z, dim=-1)

        gold = int(
            torch.argmax(
                target[i][valid]
            ).item()
        )

        pred = int(
            torch.argmax(p).item()
        )

        rows.append(
            {
                "row": i,
                "gold": gold,
                "pred": pred,
                "confidence": float(p[pred].item()),
                "probabilities": [
                    round(float(x), 4)
                    for x in p.detach().cpu()
                ],
            }
        )

    correct = sum(
        1 for x in rows
        if x["gold"] == x["pred"]
    )

    accuracy = (
        correct / len(rows)
        if rows
        else 0.0
    )

    print("")
    print("---- %s ----" % title)

    for x in rows:
        print(
            "row=%d gold=%d pred=%d conf=%.4f probs=%s"
            % (
                x["row"],
                x["gold"],
                x["pred"],
                x["confidence"],
                x["probabilities"],
            )
        )

    print(
        "训练行直接 forward 准确率: %d/%d = %.2f%%"
        % (
            correct,
            len(rows),
            accuracy * 100.0,
        )
    )

    if was_training:
        agent.model.train()

    return accuracy


def save_checkpoint(
    agent,
    args,
    samples,
    trainable,
):
    """
    保存训练后的模型。

    这里刻意保持 Laya 原始模型结构不变：
        scorer -> 1 scalar / option

    因此保存后可以直接由：
        laya.Agent(args.out)
    加载。
    """
    from safetensors.torch import save_file

    os.makedirs(
        args.out,
        exist_ok=True,
    )

    state = {
        k: v.detach()
        .to("cpu", torch.float16)
        .contiguous()
        for k, v in agent.model.state_dict().items()
    }

    weights_path = os.path.join(
        args.out,
        "model.safetensors",
    )

    size_mb = (
        sum(v.numel() for v in state.values())
        * 2
        / 1e6
    )

    print(
        "  正在保存: model.safetensors (%.0f MB)"
        % size_mb
    )

    save_file(
        state,
        weights_path,
    )

    # tokenizer / encoder 必须跟随保存。
    for name in KEEP_DIRS:
        src = os.path.join(
            args.base,
            name,
        )

        if os.path.isdir(src):
            print(
                "  正在保存: %s/"
                % name
            )

            shutil.copytree(
                src,
                os.path.join(args.out, name),
                dirs_exist_ok=True,
            )

    # 复制原配置，不修改 act_costs。
    #
    # 这是关键：
    # 我们不改变 Laya 的 act_head 宽度。
    # eap_action 是第二个 choice 问题，而不是 act_head。
    base_cfg_path = os.path.join(
        args.base,
        "rl_agent_config.json",
    )

    with open(
        base_cfg_path,
        "r",
        encoding="utf-8",
    ) as f:
        cfg = json.load(f)

    cfg["finetuned"] = True
    cfg["finetune_task"] = (
        "speech_type + eap_action "
        "as two choice questions"
    )
    cfg["finetune_samples"] = len(samples)
    cfg["finetune_epochs"] = args.epochs
    cfg["finetune_lr"] = args.lr
    cfg["finetune_trainable_params"] = int(
        sum(p.numel() for p in trainable)
    )
    cfg["finetune_frozen_encoder"] = (
        not args.train_encoder
    )
    cfg["finetune_questions"] = list(
        QUESTIONS.keys()
    )

    with open(
        os.path.join(
            args.out,
            "rl_agent_config.json",
        ),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            cfg,
            f,
            ensure_ascii=False,
            indent=2,
        )


def reload_and_validate(args, batch):
    """
    用真正的 laya.Agent 从磁盘重新加载。

    因为模型结构没有修改，这里应该可以 strict load。
    """
    print("")
    print("正在重新加载保存后的模型...")

    reloaded = laya.Agent(
        args.out,
        device=args.device,
    )

    print(
        "重新加载完成: device=%s dtype=%s"
        % (
            reloaded.device,
            reloaded.dtype,
        )
    )

    # 检查重新加载后的 scorer。
    with torch.no_grad():
        logits, _ = forward_scorer(
            reloaded,
            batch,
        )

    if logits.shape[-1] < 3:
        raise RuntimeError(
            "重新加载后 scorer 的 option 宽度不足 3: %s"
            % (tuple(logits.shape),)
        )

    print(
        "重新加载后 scorer 输出宽度: %d"
        % logits.shape[-1]
    )

    accuracy = evaluate_training_rows(
        reloaded,
        batch,
        "重新加载后的训练集验证",
    )

    return reloaded, accuracy


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Laya 本地 speech_type + eap_action 微调"
        )
    )

    parser.add_argument(
        "--base",
        default="./laya_base_cache",
    )

    parser.add_argument(
        "--out",
        default="./my_custom_laya_model",
    )

    parser.add_argument(
        "--data",
        default="train_data.json",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--lr",
        type=float,
        default=2e-5,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--device",
        default=None,
        help="cuda / cpu / mps；默认由 Laya 自动选择",
    )

    parser.add_argument(
        "--max-len",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--head-max-len",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--train-encoder",
        action="store_true",
        help=(
            "同时训练 ModernBERT encoder；"
            "显存和训练时间会显著增加"
        ),
    )

    args = parser.parse_args()

    if not os.path.isdir(args.base):
        raise FileNotFoundError(
            "找不到基座模型目录: %s"
            % args.base
        )

    if not os.path.exists(args.data):
        raise FileNotFoundError(
            "找不到训练数据: %s"
            % args.data
        )

    print("=" * 60)
    print("Laya 决策引擎本地微调")
    print("=" * 60)

    print(
        "CUDA 可用: %s | 设备数: %d"
        % (
            torch.cuda.is_available(),
            torch.cuda.device_count(),
        )
    )

    print(
        "正在加载基座模型: %s"
        % args.base
    )

    agent = laya.Agent(
        args.base,
        device=args.device,
    )

    model = agent.model

    print(
        "加载完成: device=%s dtype=%s"
        % (
            agent.device,
            agent.dtype,
        )
    )

    max_len = (
        args.max_len
        or agent.cfg.get("max_len", 512)
    )

    head_max_len = (
        args.head_max_len
        or agent.cfg.get(
            "head_max_len",
            192,
        )
    )

    samples = load_samples(
        args.data
    )

    print(
        "读取训练集: %s (%d 条)"
        % (
            args.data,
            len(samples),
        )
    )

    batch, supervised = build_inputs(
        agent,
        samples,
        max_len,
        head_max_len,
    )

    print(
        "每个 state 训练两个 choice："
        "speech_type + eap_action"
    )

    print(
        "训练矩阵: input rows=%d, target shape=%s"
        % (
            batch["input_ids"].shape[0],
            tuple(batch["target"].shape),
        )
    )

    # ---------------------------------------------------------
    # 设备统一
    # ---------------------------------------------------------
    #
    # batch 先保持 CPU，真正 forward 前统一移动。
    # 这样不会再出现：
    #
    #   index is on cpu
    #   weight is on cuda:0
    #
    # 的错误。
    #
    device = next(
        model.parameters()
    ).device

    print(
        "模型实际 device: %s"
        % device
    )

    # ---------------------------------------------------------
    # 冻结 encoder
    # ---------------------------------------------------------
    if not args.train_encoder:
        for p in model.encoder.parameters():
            p.requires_grad = False

    # 不训练 Laya 内部 act_head。
    # eap_action 已经作为第二个 choice 问题训练。
    for p in model.act_head.parameters():
        p.requires_grad = False

    # 训练：
    #   head
    #   type_emb
    #   scorer
    #
    # 如果 --train-encoder：
    #   encoder 也会加入。
    trainable = [
        p
        for p in model.parameters()
        if p.requires_grad
    ]

    print(
        "可训练参数: %.2fM / %.2fM"
        % (
            sum(
                p.numel()
                for p in trainable
            ) / 1e6,
            sum(
                p.numel()
                for p in model.parameters()
            ) / 1e6,
        )
    )

    print(
        "scorer: 每个 [MASK] 输出 1 个 scalar；"
        "3 个 option -> 3 个 choice logits"
    )

    print(
        "Laya act_head: %d 类（不参与 eap_action 训练）"
        % model.act_head[-1].out_features
    )

    optimizer = AdamW(
        trainable,
        lr=args.lr,
        weight_decay=0.01,
    )

    targets = batch["target"]
    sample_mask = batch["sample_mask"]
    marker_mask = batch["marker_mask"]

    print("")
    print("训练前直接 forward 检查...")

    with torch.no_grad():
        probe_logits, _ = forward_scorer(
            agent,
            batch,
        )

    print(
        "scorer forward 输出 shape: %s"
        % (tuple(probe_logits.shape),)
    )

    if probe_logits.shape[-1] < 3:
        raise RuntimeError(
            "Laya scorer forward 没有至少 3 个 option：%s"
            % (tuple(probe_logits.shape),)
        )

    # ---------------------------------------------------------
    # 训练
    # ---------------------------------------------------------
    n_rows = batch["input_ids"].shape[0]
    batch_size = max(
        1,
        args.batch_size,
    )

    print("")
    print(
        "开始训练: epochs=%d batch=%d lr=%g"
        % (
            args.epochs,
            batch_size,
            args.lr,
        )
    )

    for epoch in range(args.epochs):
        model.train()

        # encoder 是否冻结由 requires_grad 决定。
        epoch_loss = 0.0
        steps = 0

        for start in range(
            0,
            n_rows,
            batch_size,
        ):
            stop = min(
                start + batch_size,
                n_rows,
            )

            batch_cpu = {
                k: (
                    v[start:stop]
                    if torch.is_tensor(v)
                    else v
                )
                for k, v in batch.items()
            }

            # -------------------------------------------------
            # 这里统一移动整个 batch
            # -------------------------------------------------
            mini = move_batch_to_device(
                batch_cpu,
                device,
            )

            optimizer.zero_grad(
                set_to_none=True
            )

            logits, _ = forward_scorer(
                agent,
                mini,
            )

            # 训练 scorer：
            # speech_type 和 eap_action 都走同一个 choice scorer，
            # 只是对应不同的 row。
            loss = masked_choice_ce(
                logits,
                mini["target"],
                mini["marker_mask"],
                mini["sample_mask"],
            )

            if loss is None:
                continue

            if not torch.isfinite(loss):
                raise RuntimeError(
                    "第 %d epoch 出现非有限 loss: %s"
                    % (
                        epoch + 1,
                        loss.item(),
                    )
                )

            loss.backward()

            torch.nn.utils.clip_grad_norm_(
                trainable,
                1.0,
            )

            optimizer.step()

            epoch_loss += float(
                loss.detach().item()
            )
            steps += 1

        if steps == 0:
            raise RuntimeError(
                "epoch %d 没有执行任何训练 step"
                % (epoch + 1)
            )

        avg_loss = (
            epoch_loss / steps
        )

        print(
            "Epoch %d/%d 完成 | 平均 loss = %.6f | steps = %d"
            % (
                epoch + 1,
                args.epochs,
                avg_loss,
                steps,
            )
        )

        # 每 10 epoch 检查一次，最后一个 epoch 一定检查。
        if (
            (epoch + 1) % 10 == 0
            or epoch + 1 == args.epochs
        ):
            evaluate_training_rows(
                agent,
                batch,
                "Epoch %d 训练集直接 forward"
                % (epoch + 1),
            )

    # ---------------------------------------------------------
    # 保存前验证
    # ---------------------------------------------------------
    before_save_acc = evaluate_training_rows(
        agent,
        batch,
        "保存前训练集直接 forward",
    )

    # ---------------------------------------------------------
    # 保存
    # ---------------------------------------------------------
    save_checkpoint(
        agent,
        args,
        samples,
        trainable,
    )

    print("")
    print(
        "训练完成, 新权重已保存至: %s"
        % os.path.abspath(args.out)
    )

    print(
        "已冻结 encoder: %s"
        % (not args.train_encoder)
    )

    # ---------------------------------------------------------
    # 重新加载验证
    # ---------------------------------------------------------
    reloaded, after_reload_acc = (
        reload_and_validate(
            args,
            batch,
        )
    )

    print("")
    print("=" * 60)
    print("最终验证")
    print("=" * 60)

    print(
        "保存前训练集准确率: %.2f%%"
        % (before_save_acc * 100)
    )

    print(
        "重新加载后训练集准确率: %.2f%%"
        % (after_reload_acc * 100)
    )

    if after_reload_acc + 1e-9 < before_save_acc - 0.05:
        print(
            "警告：重新加载后准确率明显下降，"
            "请检查权重保存/加载。"
        )
    else:
        print(
            "OK：保存后的模型可以重新加载，"
            "训练权重与模型结构匹配。"
        )

    print("")
    print(
        "下一步测试："
    )
    print(
        "python test_custom_laya.py"
    )

    print("=" * 60)


if __name__ == "__main__":
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        message="laya:.*temperature",
    )
    main()
