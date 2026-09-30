"""PoL2 通用决策回放池（DATA-02 回放数据）。

把本目录放进 sys.path，使两种 discover 起点都能平铺导入 audit/rewrite：
    python -m unittest discover -s datasets/pol2/replay -p "test_*.py" -q
    python -m unittest discover -s datasets -p "test_*.py" -q
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
