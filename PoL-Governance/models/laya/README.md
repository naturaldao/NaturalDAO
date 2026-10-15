# Laya 本地决策模型脚本

对 [模型清单](../CATALOG.md) 中 `laya-multilingual` 的本地微调与测试脚本，以及 Kev 本地服务的 API 冒烟脚本。原先放在仓库根目录，2026-10 移入此处，内容未改。

| 文件 | 用途 |
| :--- | :--- |
| `train_custom_gpt.py` | 微调 Laya：`state -> speech_type + eap_action` |
| `test_custom_laya.py` | 加载微调后的模型，统计 `speech_type` / `eap_action` 准确率 |
| `kev_test_api.py` | 测试 Kev 本地服务（默认 `http://localhost:8009`）的 API |

脚本按工作目录解析数据与模型路径，请在本目录运行，例如：

```powershell
python train_custom_gpt.py --data train_data.json --epochs 5 --batch-size 1
python test_custom_laya.py --model ./my_custom_laya_model
```

训练数据、模型权重和配置不提交到仓库；提交结果按 [results](../../results/README.md) 的规则。
