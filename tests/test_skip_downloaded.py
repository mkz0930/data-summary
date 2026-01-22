"""
测试脚本：验证跳过已下载关键词和已分析关键词的功能

此脚本演示如何使用系统的重复检查功能：
1. ScraperAPI 下载检查
2. AI 分析结果检查
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from external_apis.amazon_scraper import AmazonScraper
from src.core.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager

def test_scraper_skip():
    """测试 ScraperAPI 跳过已下载关键词的功能"""
    print("=" * 60)
    print("测试 1: ScraperAPI 跳过已下载关键词")
    print("=" * 60)

    # 加载配置
    config = ConfigManager()
    api_key = config.scraperapi_key

    if not api_key:
        print("错误: 未找到 SCRAPERAPI_KEY，请在 config/.env 中配置")
        return False

    # 初始化 scraper
    scraper = AmazonScraper(api_key=api_key)

    # 测试关键词
    test_keyword = "camping"
    country_code = "us"

    # 1. 检查关键词是否已下载
    is_downloaded = scraper.has_keyword_been_downloaded(test_keyword, country_code)
    print(f"\n关键词 '{test_keyword}' 是否已下载: {is_downloaded}")

    # 2. 如果已下载，获取下载信息
    if is_downloaded:
        download_info = scraper.get_keyword_download_info(test_keyword, country_code)
        print(f"\n下载信息:")
        print(f"  - 下载时间: {download_info['downloaded_at']}")
        print(f"  - 记录数量: {download_info['record_count']}")
        print(f"  - 国家代码: {download_info['country_code']}")
        print("\n✅ 该关键词已下载，调用 search_keyword_with_smart_stop() 时会自动跳过")
        return True
    else:
        print(f"\n该关键词尚未下载，首次调用会进行下载")
        return False

def test_analysis_skip():
    """测试 AI 分析跳过已分析关键词的功能"""
    print("\n" + "=" * 60)
    print("测试 2: AI 分析跳过已分析关键词")
    print("=" * 60)

    # 加载配置
    config = ConfigManager()
    db = DatabaseManager(config.database_path)

    # 测试关键词
    test_keyword = "camping"

    # 检查是否已经分析过
    existing_result = db.get_analysis_result(test_keyword)

    if existing_result:
        print(f"\n关键词 '{test_keyword}' 已分析过")
        print(f"\n分析信息:")
        print(f"  - 分析时间: {existing_result.created_at}")
        print(f"  - 市场空白指数: {existing_result.market_blank_index}")
        print(f"  - 新品数量: {existing_result.new_product_count}")
        print(f"  - 报告路径: {existing_result.report_path}")
        print("\n✅ 该关键词已分析，调用 orchestrator.run() 时会自动跳过")
        print("提示: 如需重新分析，请使用 --force-reanalysis 参数")
        return True
    else:
        print(f"\n关键词 '{test_keyword}' 尚未分析")
        print("首次运行会执行完整的分析流程")
        return False

def test_full_workflow():
    """测试完整工作流程"""
    print("\n" + "=" * 60)
    print("测试 3: 完整工作流程演示")
    print("=" * 60)

    print("\n工作流程说明:")
    print("1. 首次运行: python main.py --keyword camping")
    print("   - 调用 ScraperAPI 下载数据")
    print("   - 执行 AI 分类校验")
    print("   - 进行市场分析")
    print("   - 生成报告")
    print()
    print("2. 再次运行: python main.py --keyword camping")
    print("   - ✅ 跳过 ScraperAPI 下载（使用缓存）")
    print("   - ✅ 跳过 AI 分析（使用已有结果）")
    print("   - 直接返回分析结果")
    print()
    print("3. 强制重新分析: python main.py --keyword camping --force-reanalysis")
    print("   - ✅ 跳过 ScraperAPI 下载（使用缓存）")
    print("   - 重新执行 AI 分类校验")
    print("   - 重新进行市场分析")
    print("   - 生成新报告")

def main():
    """主测试函数"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║                                                               ║")
    print("║        重复下载/分析检查功能测试                              ║")
    print("║                                                               ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()

    try:
        # 测试 1: ScraperAPI 跳过检查
        scraper_cached = test_scraper_skip()

        # 测试 2: AI 分析跳过检查
        analysis_cached = test_analysis_skip()

        # 测试 3: 完整工作流程说明
        test_full_workflow()

        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"ScraperAPI 缓存状态: {'✅ 已缓存' if scraper_cached else '❌ 未缓存'}")
        print(f"AI 分析缓存状态: {'✅ 已缓存' if analysis_cached else '❌ 未缓存'}")
        print()

        if scraper_cached and analysis_cached:
            print("✅ 所有数据已缓存，再次运行将直接使用缓存结果")
            print("   节省 API 调用成本和时间")
        elif scraper_cached:
            print("⚠️  ScraperAPI 数据已缓存，但尚未完成 AI 分析")
            print("   建议运行: python main.py --keyword camping")
        else:
            print("ℹ️  尚未下载数据，建议运行完整流程")
            print("   运行: python main.py --keyword camping")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
