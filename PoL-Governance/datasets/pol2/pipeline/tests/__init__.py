"""PoL2 pipeline 离线测试包。

把 pipeline 目录与 tests 目录都放进 sys.path，使两种 discover 起点都能平铺导入：
    python -m unittest discover -s datasets/pol2/pipeline -p "test_*.py" -q
    python -m unittest discover -s datasets/pol2/pipeline/tests -p "test_*.py" -q
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for directory in (HERE.parent, HERE):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
