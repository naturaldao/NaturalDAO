# V2 容量复算与支撑

[返回存储研究入口](../README.md) · [V2 技术报告](../02-技术方案/PoL2存储技术方案.md)

| 文件 | 用途 |
|---|---|
| [scenarios.json](scenarios.json) | 假设容量情景与参数 |
| [capacity_model.py](capacity_model.py) | 容量算术程序，不是性能基准 |
| [capacity_results.json](capacity_results.json) · [容量情景结果](容量情景结果.md) | 已保存的机器可读结果与阅读版 |
| [test_capacity_model.py](test_capacity_model.py) | 参数与计算检查 |
| [架构图](figures/architecture-overview.png) | 技术报告使用的结构示意 |
| [improve_readability.py](improve_readability.py) · [check_readability.py](check_readability.py) | 历史排版处理与保真检查；检查器针对固定 Git 基线，非通用验收工具 |

从仓库根目录运行，使用项目适用的 Python 环境：

```powershell
python Research/Storage/03-复算与支撑/capacity_model.py --scenarios Research/Storage/03-复算与支撑/scenarios.json --json-out Research/Storage/03-复算与支撑/capacity_results.json --markdown-out Research/Storage/03-复算与支撑/容量情景结果.md
python -m unittest discover -s Research/Storage/03-复算与支撑 -p test_capacity_model.py -v
```

这些结果只验证给定假设下的容量算术，不代表工程吞吐、可靠性或轨道验证。
