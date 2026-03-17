"""pytest 配置 - 测试夹具和路径设置."""

import sys
from pathlib import Path

# 添加 src 到路径，使其可作为包导入
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path.parent))
