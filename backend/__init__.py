# Rewind Backend Package

import sys
from pathlib import Path

# 将 rewind_backend 目录添加到 sys.path 中
# 这样可以让包内的 "from core.xxx" 导入正常工作
_backend_dir = Path(__file__).parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
