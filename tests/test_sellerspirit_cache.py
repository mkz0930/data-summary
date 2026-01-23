"""
测试卖家精灵数据缓存功能
验证避免重复下载的逻辑
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.sellerspirit_collector import SellerSpiritCollector
from src.database.db_manager import DatabaseManager
from src.utils.logger import get_logger


def test_cache_logic():
    """测试缓存逻辑"""
    logger = get_logger()

    logger.info("=" * 60)
    logger.info("测试卖家精灵数据缓存功能")
    logger.info("=" * 60)

    # 初始化数据库管理器
    db_manager = DatabaseManager()

    # 初始化采集器（传入数据库管理器）
    collector = SellerSpiritCollector(db_manager=db_manager)

    # 测试关键词
    test_keyword = "test keyword"

    logger.info(f"\n测试关键词: {test_keyword}")

    # 第一次调用：应该检查并使用已有数据（如果存在）
    logger.info("\n第一次调用 collect_data (force_download=False):")
    logger.info("-" * 60)
    try:
        data1 = collector.collect_data(test_keyword, force_download=False)
        if data1:
            logger.info(f"✓ 获取到数据")
            logger.info(f"  - 月搜索量: {data1.monthly_searches}")
            logger.info(f"  - CR4: {data1.cr4}")
        else:
            logger.info(f"⚠ 未获取到数据")
    except Exception as e:
        logger.error(f"✗ 出错: {e}")

    # 第二次调用：应该使用缓存数据，不会重新下载
    logger.info("\n第二次调用 collect_data (force_download=False):")
    logger.info("-" * 60)
    try:
        data2 = collector.collect_data(test_keyword, force_download=False)
        if data2:
            logger.info(f"✓ 获取到数据（应该来自缓存）")
            logger.info(f"  - 月搜索量: {data2.monthly_searches}")
            logger.info(f"  - CR4: {data2.cr4}")
        else:
            logger.info(f"⚠ 未获取到数据")
    except Exception as e:
        logger.error(f"✗ 出错: {e}")

    # 强制下载：应该重新下载
    logger.info("\n第三次调用 collect_data (force_download=True):")
    logger.info("-" * 60)
    logger.info("注意：这将强制重新下载数据")
    # 注释掉实际下载，避免真的触发下载
    # try:
    #     data3 = collector.collect_data(test_keyword, force_download=True)
    #     if data3:
    #         logger.info(f"✓ 获取到数据（重新下载）")
    #     else:
    #         logger.info(f"⚠ 未获取到数据")
    # except Exception as e:
    #     logger.error(f"✗ 出错: {e}")
    logger.info("（已跳过实际下载测试）")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_cache_logic()
