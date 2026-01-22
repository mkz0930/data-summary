"""
测试Gemini分类验证器
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.validators.gemini_validator import GeminiCategoryValidator
from src.database.db_manager import DatabaseManager
from src.core.config_manager import ConfigManager
from src.utils.logger import get_logger

def test_gemini_validator():
    """测试Gemini验证器"""
    logger = get_logger()

    # 初始化配置
    logger.info("初始化配置...")
    config = ConfigManager()

    # 检查API密钥
    api_key = config.google_api_key
    if not api_key:
        logger.error("未找到GOOGLE_API_KEY，请在.env文件中配置")
        return

    logger.info(f"Google API Key: {api_key[:10]}...")

    # 初始化数据库
    logger.info("初始化数据库...")
    db = DatabaseManager(config.database_path)

    # 初始化Gemini验证器
    logger.info("初始化Gemini验证器...")
    validator = GeminiCategoryValidator(api_key, db_manager=db)

    # 测试关键词
    keyword = "婴喜爱"
    logger.info(f"测试关键词: {keyword}")

    # 从数据库获取产品
    logger.info("从数据库获取产品...")
    products = db.get_all_products()

    if not products:
        logger.warning("数据库中没有产品数据")
        logger.info("请先运行主程序采集数据")
        return

    logger.info(f"找到 {len(products)} 个产品")

    # 测试单个产品验证
    logger.info("\n" + "="*60)
    logger.info("测试1: 单个产品验证")
    logger.info("="*60)

    test_product = products[0]
    logger.info(f"测试产品: {test_product.asin} - {test_product.name[:50]}...")

    result = validator.validate_product(test_product, keyword)
    if result:
        logger.info(f"验证结果:")
        logger.info(f"  - 相关性: {'相关' if result.is_relevant else '不相关'}")
        logger.info(f"  - 分类正确: {'是' if result.category_is_correct else '否'}")
        logger.info(f"  - 推理: {result.validation_reason[:100]}...")

    # 测试批量验证（前5个产品）
    logger.info("\n" + "="*60)
    logger.info("测试2: 批量验证（前5个产品）")
    logger.info("="*60)

    batch_products = products[:5]
    logger.info(f"批量验证 {len(batch_products)} 个产品...")

    results = validator.validate_batch(batch_products, keyword)

    logger.info(f"\n批量验证完成，成功验证 {len(results)} 个产品")

    # 统计结果
    relevant_count = sum(1 for r in results if r.is_relevant)
    correct_category_count = sum(1 for r in results if r.category_is_correct)

    logger.info(f"\n验证统计:")
    logger.info(f"  - 相关产品: {relevant_count}/{len(results)} ({relevant_count/len(results)*100:.1f}%)")
    logger.info(f"  - 分类正确: {correct_category_count}/{len(results)} ({correct_category_count/len(results)*100:.1f}%)")

    # 显示详细结果
    logger.info(f"\n详细结果:")
    for i, result in enumerate(results, 1):
        product = batch_products[i-1]
        logger.info(f"\n产品 {i}: {product.asin}")
        logger.info(f"  名称: {product.name[:50]}...")
        logger.info(f"  分类: {product.category}")
        logger.info(f"  相关性: {'✓ 相关' if result.is_relevant else '✗ 不相关'}")
        logger.info(f"  分类: {'✓ 正确' if result.category_is_correct else '✗ 错误'}")
        logger.info(f"  推理: {result.validation_reason[:100]}...")

    # 测试CSV导出
    logger.info("\n" + "="*60)
    logger.info("测试3: CSV导出功能")
    logger.info("="*60)

    csv_path = validator.save_results_to_csv(results, batch_products, keyword)
    if csv_path:
        logger.info(f"✓ CSV文件已保存: {csv_path}")
    else:
        logger.error("✗ CSV保存失败")

    # 测试一体化功能（验证并保存）
    logger.info("\n" + "="*60)
    logger.info("测试4: 验证并保存（前10个产品）")
    logger.info("="*60)

    batch_products_2 = products[:10]
    logger.info(f"验证并保存 {len(batch_products_2)} 个产品...")

    results_2, csv_path_2 = validator.validate_and_save(
        batch_products_2,
        keyword,
        skip_validated=False,  # 不跳过已验证的，以便测试
        save_to_db=True,
        save_to_csv=True
    )

    logger.info(f"\n验证并保存完成:")
    logger.info(f"  - 验证结果数: {len(results_2)}")
    logger.info(f"  - CSV文件: {csv_path_2}")

    # 统计结果
    if results_2:
        relevant_count_2 = sum(1 for r in results_2 if r.is_relevant)
        correct_category_count_2 = sum(1 for r in results_2 if r.category_is_correct)
        logger.info(f"  - 相关产品: {relevant_count_2}/{len(results_2)} ({relevant_count_2/len(results_2)*100:.1f}%)")
        logger.info(f"  - 分类正确: {correct_category_count_2}/{len(results_2)} ({correct_category_count_2/len(results_2)*100:.1f}%)")

if __name__ == "__main__":
    test_gemini_validator()
