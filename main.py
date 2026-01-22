"""
亚马逊商品数据分析系统 - 主入口程序
提供CLI接口，支持命令行参数
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import get_config, init_config
from src.core.orchestrator import Orchestrator
from src.utils.logger import get_logger


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='亚马逊商品数据分析系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用配置文件中的关键词运行完整分析
  python main.py

  # 指定关键词运行分析
  python main.py --keyword camping

  # 跳过数据采集，使用数据库中的数据
  python main.py --skip-collection

  # 跳过AI分类校验
  python main.py --skip-validation

  # 强制重新分析已分析过的关键词
  python main.py --keyword camping --force-reanalysis

  # 仅显示分析摘要
  python main.py --summary

  # 指定配置文件路径
  python main.py --config config/config.json --env config/.env
        """
    )

    parser.add_argument(
        '--keyword', '-k',
        type=str,
        help='搜索关键词（如果不指定则使用配置文件中的关键词）'
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        help='配置文件路径（默认: config/config.json）'
    )

    parser.add_argument(
        '--env', '-e',
        type=str,
        help='环境变量文件路径（默认: config/.env）'
    )

    parser.add_argument(
        '--skip-collection',
        action='store_true',
        help='跳过数据采集，使用数据库中的现有数据'
    )

    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='跳过AI分类校验（节省API调用）'
    )

    parser.add_argument(
        '--force-reanalysis',
        action='store_true',
        help='强制重新分析，即使关键词已经分析过'
    )

    parser.add_argument(
        '--summary', '-s',
        action='store_true',
        help='仅显示分析摘要，不运行完整流程'
    )

    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='验证配置文件是否完整'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='亚马逊商品数据分析系统 v1.0.0'
    )

    return parser.parse_args()


def validate_config(config):
    """
    验证配置

    Args:
        config: 配置管理器

    Returns:
        是否有效
    """
    logger = get_logger()

    logger.info("验证配置...")
    if config.validate():
        logger.info("✓ 配置验证通过")
        return True
    else:
        logger.error("✗ 配置验证失败，请检查配置文件和环境变量")
        return False


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        亚马逊商品数据分析系统 v1.0.0                          ║
║        Amazon Product Analysis System                         ║
║                                                               ║
║        数据驱动的产品选型决策工具                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()

    # 打印横幅
    print_banner()

    try:
        # 初始化配置
        if args.config or args.env:
            config = init_config(args.config, args.env)
        else:
            config = get_config()

        logger = get_logger()

        # 如果只是验证配置
        if args.validate_config:
            if validate_config(config):
                print("\n✓ 配置验证通过")
                return 0
            else:
                print("\n✗ 配置验证失败")
                return 1

        # 验证配置
        if not validate_config(config):
            return 1

        # 初始化流程编排器
        orchestrator = Orchestrator(config)

        # 如果只是显示摘要
        if args.summary:
            keyword = args.keyword or config.keyword
            logger.info(f"生成分析摘要: {keyword}")
            summary = orchestrator.get_summary(keyword)
            print(summary)
            return 0

        # 运行完整分析流程
        logger.info("开始运行分析流程...")
        result = orchestrator.run(
            keyword=args.keyword,
            skip_collection=args.skip_collection,
            skip_validation=args.skip_validation,
            force_reanalysis=args.force_reanalysis
        )

        # 输出结果
        if result['success']:
            print("\n" + "=" * 60)
            print("✓ 分析完成!")
            print("=" * 60)
            print(f"\n关键词: {result['keyword']}")

            # 如果是从缓存加载的
            if result.get('from_cache'):
                print(f"状态: 使用已有分析结果 (分析于 {result.get('analyzed_at')})")
                print(f"市场空白指数: {result.get('market_blank_index', 'N/A')}")
                print(f"新品数量: {result.get('new_product_count', 'N/A')}")
            else:
                print(f"总产品数: {result.get('total_products', 'N/A')}")

            print(f"\n报告文件:")
            for name, path in result['report_paths'].items():
                print(f"  - {name}: {path}")
            print("\n" + "=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("✗ 分析失败!")
            print("=" * 60)
            print(f"\n错误: {result.get('error', '未知错误')}")
            print("\n" + "=" * 60)
            return 1

    except KeyboardInterrupt:
        print("\n\n用户中断执行")
        return 130

    except Exception as e:
        logger = get_logger()
        logger.error(f"程序执行失败: {e}", exc_info=True)
        print(f"\n✗ 错误: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
