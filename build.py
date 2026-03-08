#!/usr/bin/env python3
"""
堆叠江湖 - 打包入口（快捷方式）
实际打包逻辑在 packaging/build.py

使用方法:
    python build.py              # 打包当前平台
    python build.py --clean      # 清理并重新打包
    python build.py --onefile    # 打包为单文件
    python build.py --console    # 保留控制台窗口（调试用）
"""

import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    # 转发所有参数到实际的打包脚本
    packaging_script = Path(__file__).parent / "packaging" / "build.py"
    result = subprocess.run([sys.executable, str(packaging_script)] + sys.argv[1:])
    sys.exit(result.returncode)
