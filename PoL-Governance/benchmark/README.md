# 公共评估工具

已有公开试例 20 条、10 个场景族，均为助手生成的待审标签。工具可运行，真实模型与正式 benchmark 尚未完成。下列命令均在 `PoL-Governance/` 执行。

## 数据与标注

原始试例：[pilot.jsonl](pilot.jsonl)。独立审阅者分别填写 [A 表](reviewer-a.blank.jsonl) 和 [B 表](reviewer-b.blank.jsonl) 的副本，不看 proposal 或彼此答案。填自己的 annotator_id、status、issues、acceptable_actions、理由和 policy_dispute，再将 completion 设为 complete。

```powershell
uv run --no-project --offline python benchmark/annotations.py compare --left path/to/a.completed.jsonl --right path/to/b.completed.jsonl
```

汇总工具只显示分歧和完成覆盖率，不投票生成金标准。待人工审定的数据继续标待审。

## 模型输入与预测

```powershell
uv run --no-project --offline python benchmark/export_inputs.py --output path/to/inputs.jsonl
uv run --no-project --offline python benchmark/evaluate.py --predictions path/to/predictions.jsonl
```

导出器只提供 id/input，不提供参考标签。预测每行包含 `id, status, issues, action, latency_ms, execution_status`，可选 `status_probs`。详细口径见 [协议](PROTOCOL.md)。所有输出路径使用新文件/新目录，不覆盖别人结果。

## Kev 接口示例

```powershell
uv run --no-project --offline python benchmark/kev_adapter.py prepare --inputs path/to/inputs.jsonl --out path/to/new-request-dir
uv run --no-project --offline python benchmark/kev_adapter.py run --inputs path/to/inputs.jsonl --out path/to/new-run-dir --checkpoint MODEL_ID@REVISION
```

prepare 不访问模型；run 需要已启动的回环 Kev 服务，默认 `http://127.0.0.1:8009/v1/systemone`。脚本不安装或下载模型；服务版本为自报，需保留实际启动证据。需要鉴权时从 KEV_API_KEY 环境变量读取，不写入运行记录。

两道 choice 分别预测 status/action，保留矛盾输出供评测，不暗中修正。当前不预测 issues。四位小数概率仅在舍入容差内归一化；原始响应另存。此适配器不是线上插件。

**当前边界**：评估器仅接受公开 pilot，报告始终不具备排名资格。正式数据读取、保留集评测、通用及主流安全测试接入由 EVAL-01 实现，不能把现有工具称为完整 benchmark。

外部入口：[WildGuard](https://github.com/allenai/wildguard)、[ToxicChat](https://huggingface.co/datasets/lmsys/toxic-chat)、[HarmBench](https://github.com/centerforaisafety/HarmBench)、[XSTest](https://github.com/paul-rottger/xstest)。
