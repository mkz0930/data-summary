#!/usr/bin/env python3
"""
批量产品分类验证测试脚本
快速测试Claude API批量验证功能
"""

import os
import sys
import time
from anthropic import Anthropic

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db_manager import DatabaseManager
from src.database.models import Product
from src.validators.category_validator import CategoryValidator
from src.core.config_manager import ConfigManager

def test_batch_validation(sample_size=5):
    """
    测试批量验证功能

    Args:
        sample_size: 测试样本数量（默认5个产品）
    """
    print("=" * 60)
    print("批量产品分类验证测试")
    print("=" * 60)

    # 1. 加载配置
    print("\n[1/5] 加载配置...")
    config = ConfigManager()

    if not config.anthropic_api_key:
        print("❌ 错误: 未找到ANTHROPIC_API_KEY")
        print("请在 config/.env 文件中设置 ANTHROPIC_API_KEY")
        return

    print(f"✓ API密钥已加载: {config.anthropic_api_key[:10]}...")

    # 2. 连接数据库
    print("\n[2/5] 连接数据库...")
    db = DatabaseManager()

    # 3. 获取测试产品
    print(f"\n[3/5] 获取测试产品（前{sample_size}个）...")
    products = db.get_all_products(limit=sample_size)

    if not products:
        print("❌ 数据库中没有产品数据")
        print("请先运行主程序采集数据: python main.py --keyword camping")
        return

    print(f"✓ 找到 {len(products)} 个产品")
    for i, p in enumerate(products, 1):
        print(f"  {i}. {p.asin} - {p.name[:50]}...")

    # 4. 初始化验证器
    print("\n[4/5] 初始化分类验证器...")
    validator = CategoryValidator(api_key=config.anthropic_api_key, db_manager=db)
    print(f"✓ 使用模型: {validator.model}")
    print(f"✓ API限流延迟: {validator.rate_limit_delay}秒")
    print(f"✓ 已验证ASIN数量: {len(validator.validated_asins)}")

    # 5. 执行批量验证
    print(f"\n[5/5] 开始批量验证...")
    print("-" * 60)

    keyword = "camping"  # 测试关键词
    start_time = time.time()

    try:
        validations = validator.validate_batch(products, keyword)

        elapsed_time = time.time() - start_time

        # 显示结果
        print("\n" + "=" * 60)
        print("验证结果")
        print("=" * 60)

        for i, (product, validation) in enumerate(zip(products, validations), 1):
            print(f"\n产品 {i}: {product.asin}")
            print(f"  名称: {product.name[:60]}")
            print(f"  分类: {product.category or '未知'}")
            print(f"  是否相关: {'✓ 是' if validation.is_relevant else '✗ 否'}")
            print(f"  分类正确: {'✓ 是' if validation.category_is_correct else '✗ 否'}")
            if validation.suggested_category:
                print(f"  建议分类: {validation.suggested_category}")
            if validation.validation_reason:
                print(f"  理由: {validation.validation_reason}")

        # 统计信息
        stats = validator.get_statistics(validations)
        print("\n" + "=" * 60)
        print("统计信息")
        print("=" * 60)
        print(f"总产品数: {stats['total']}")
        print(f"相关产品: {stats['relevant']} ({stats['relevant']/stats['total']*100:.1f}%)")
        print(f"分类正确: {stats['correct_category']} ({stats['correct_category']/stats['total']*100:.1f}%)")
        print(f"处理时间: {elapsed_time:.2f}秒")
        print(f"平均速度: {elapsed_time/len(products):.2f}秒/产品")

        print("\n✅ 测试完成！")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_single_validation():
    """测试单个产品验证"""
    print("=" * 60)
    print("单个产品验证测试")
    print("=" * 60)

    config = ConfigManager()
    db = DatabaseManager()

    products = db.get_all_products(limit=1)
    if not products:
        print("❌ 数据库中没有产品数据")
        return

    product = products[0]
    print(f"\n测试产品: {product.asin}")
    print(f"名称: {product.name}")
    print(f"分类: {product.category or '未知'}")

    validator = CategoryValidator(api_key=config.anthropic_api_key, db_manager=db)

    print("\n调用Claude API验证...")
    start_time = time.time()

    validation = validator.validate_product(product, "camping")

    elapsed_time = time.time() - start_time

    print(f"\n验证结果:")
    print(f"  是否相关: {'✓ 是' if validation.is_relevant else '✗ 否'}")
    print(f"  分类正确: {'✓ 是' if validation.category_is_correct else '✗ 否'}")
    print(f"  建议分类: {validation.suggested_category or '无'}")
    print(f"  理由: {validation.validation_reason or '无'}")
    print(f"  处理时间: {elapsed_time:.2f}秒")

    print("\n✅ 测试完成！")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="批量产品分类验证测试")
    parser.add_argument(
        '--mode',
        choices=['single', 'batch'],
        default='batch',
        help='测试模式: single=单个产品, batch=批量验证'
    )
    parser.add_argument(
        '--size',
        type=int,
        default=5,
        help='批量测试的产品数量（默认5）'
    )

    args = parser.parse_args()

    if args.mode == 'single':
        test_single_validation()
    else:
        test_batch_validation(args.size)
