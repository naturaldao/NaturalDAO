# 数据共享

先用 [公开 20 例](../benchmark/pilot.jsonl) 和 [标注工具](../benchmark/README.md)。它们是未审定的助手合成样例，不能当正式金标准或隐藏测试。

提交数据时：
1. 在 `datasets/<名称>/` 放 [数据卡](CARD.template.md)、小型公开样例和生成/处理脚本。
2. 大文件放公开数据托管站，固定 revision/hash；在 [registry.json](registry.json) 加一条，便于发现。
3. 记录来源、许可、场景族、教师/人工审阅、划分数量；禁止训练/测试跨族重复。

正式 PoL 数据按族 70/20/5/5：train / public_test / validation / private_holdout。validation 内如需选模型和校准，应事先分出互斥子集。**混合训练只用 train**；公开试例及其衍生不能进入 private_holdout。

保留集由独立评测者存放在仓库和协作者训练环境之外；仓库只登记版本、规模与汇总评测，不提交内容、逐例答案或生成提示。`.gitignore` 只是防误提交，不是保密机制。

新增数据/标签与修订保持可追溯，不把待审标签直接改名为 verified。
