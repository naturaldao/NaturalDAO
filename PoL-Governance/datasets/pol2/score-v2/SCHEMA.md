# Schema 与 canonical 映射

## Laya 训练导出

```json
{
  "state": "JSON string",
  "questions": "JSON string: {qid: question}",
  "gold": "JSON string: {qid: {label, probabilities}}",
  "case_id": "...",
  "family_id": "...",
  "unit_id": "...:a"
}
```

## Kev 训练导出

```json
{
  "state": "JSON string",
  "questions": {
    "decision": {
      "type": "choice|noul|score",
      "instructions": "...",
      "criteria": "...",
      "label": "...",
      "target": {"option": 1.0, "other": 0.0}
    }
  },
  "case_id": "...",
  "family_id": "...",
  "unit_id": "...:a"
}
```

## Canonical PoL2 映射

本实验数据尚未完全转换为 `case / question / answer / label` 四层 canonical 文件。转换时必须：

- `case_id` → `id`；
- `family_id` 保持同一族；
- `state.fixed_facts`、`judgment_actor`、`observer_cutoff`、`candidate_action` 映射到 `input` 的上下文、对象和政策字段；
- question type/instructions/criteria 映射到 question 的 `kind/prompt/options|scale`；
- 已裁决答案作为 label；
- 保留原始 array unit 与 pair 关联。

不得为了满足 canonical 格式而丢弃 A/B 世界或补写原始事实。

## 概率语义

现有 `probabilities` / `target` 是从离散答案生成的 one-hot 目标，不是多人投票或校准概率。
