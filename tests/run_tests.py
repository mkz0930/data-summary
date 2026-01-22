# 测试运行脚本

import unittest
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 发现并运行所有测试
if __name__ == '__main__':
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回退出码
    sys.exit(0 if result.wasSuccessful() else 1)
