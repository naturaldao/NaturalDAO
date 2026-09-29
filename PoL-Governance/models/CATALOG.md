# 共同维护的模型清单

初始核查日期：2026-09-29；来源为公开模型卡、训练代码及此前研究。未在本工程训练或验证中文 PoL 效果。按 PR 增补/修正条目，注明日期与证据，不靠名称或热度排强弱。

## 优先实验入口

| 模型 | 适配入口 | 主要待验证项 |
|---|---|---|
| [Shieldstral-3B](https://huggingface.co/mistralai/Shieldstral-1.0-3B) | [Axolotl](https://docs.axolotl.ai/docs/models/shieldstral.html)，政策 yes/no，LoRA 等 | 三态映射、中文边界、多政策成本 |
| [Kev-4B / 0.8B](https://github.com/jaredpalmer/kev) | 原生 kev.train，已有 adapter/head 继续训练 | 中文迁移、遗忘和真实部署成本 |
| [Intern-Decision](https://github.com/InternLM/Intern-Decision) | XTuner/FSDP，决策位置 masked CE | 发布权重继续训练、单卡资源；LoRA 尚待验证 |
| [Laya multilingual](https://huggingface.co/convaiinnovations/laya-multilingual) | 小编码器，原生训练路线待匹配 checkpoint | 校准、标签顺序偏差、任务迁移；条件备选 |

四者模型卡声明 Apache-2.0，完整使用许可需连同底座/训练数据检查。路线不限于 Jev 类，治理效果与性价比优先。

## 扩展与对照

| 模型 / 路线 | 参考入口与关注点 |
|---|---|
| JevK5 | [实现](https://github.com/allebee/jevk5)；候选 token logits / LoRA；核查中文与多选项成本 |
| Mica | [模型卡](https://huggingface.co/sky7350/Mica-v0.1-4B)；继续训练与中文证据待补 |
| AlexWortega/openjev | [模型卡](https://huggingface.co/AlexWortega/openjev)；NLI，按具体版本追踪测试污染 |
| GLiNER2.5 / Verdict | [GLiNER](https://huggingface.co/fastino/GLiNER2.5-multi-Decide) / [Verdict](https://huggingface.co/heman10x/rlcd-modernbert-151m)；轻量路线，适配收益待测 |
| CLM | [模型卡](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B)；对比投影头 |
| 普通小 LLM / SemIf | [SemIf](https://github.com/TheoLeeCJ/SemIf-OpenJev)；必须保留的简单基线 |
| Qwen3Guard / Llama Guard | [Qwen3Guard](https://github.com/QwenLM/Qwen3Guard) / [Llama Guard](https://huggingface.co/meta-llama/Llama-Guard-4-12B)；主流安全对照，许可分别核查 |
| 官方 Jev | [文档](https://docs.typesafe.ai/models)；不提供客户微调/LoRA，排除可训练短名单，可作外部基线 |
| openjev/openjev | [模型卡](https://huggingface.co/openjev/openjev)；非商业权重，不作为默认公共工程底座 |

## 如何补充

一条新记录回答：模型/版本、许可、本地运行条件、适配代码、中文/PoL 证据、速度测试条件、已知失败和来源日期。区分作者宣称、独立复现与本工程实测；找不到就写未知。

详细调研可用 [research prompt](../research/model-research-example.md)。阶段性报告与相反证据都欢迎合并。
