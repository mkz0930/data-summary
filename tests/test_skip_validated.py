#!/usr/bin/env python3
"""
快速测试"跳过已验证ASIN"功能
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db_manager import DatabaseManager
from src.core.config_manager import ConfigManager
from src.validators.category_validator import CategoryValidator

def test_skip_validated():
    """测试跳过已验证ASIN的功能"""

    print("=" * 60)
    print("测试：跳过已验证ASIN功能")
    print("=" * 60)

    # 1. 初始化
    print("\n[1/4] 初始化组件...")
    config = ConfigManager()
    db = DatabaseManager()

    # 2. 检查数据库中的验证记录
    print("\n[2/4] 检查数据库中的验证记录...")
    validated_asins = db.get_validated_asins()
    print(f"✓ 数据库中已有 {len(validated_asins)} 个已验证的ASIN")

    if validated_asins:
        print(f"  示例ASIN: {list(validated_asins)[:5]}")

    # 3. 获取测试产品
    print("\n[3/4] 获取测试产品...")
    all_products = db.get_all_products(limit=20)

    if not all_products:
        print("❌ 数据库中没有产品数据")
        print("请先运行: python main.py --keyword camping")
        return

    print(f"✓ 获取了 {len(all_products)} 个产品")

    # 统计已验证和未验证的产品
    validated_count = sum(1 for p in all_products if p.asin in validated_asins)
    unvalidated_count = len(all_products) - validated_count

    print(f"  - 已验证: {validated_count} 个")
    print(f"  - 未验证: {unvalidated_count} 个")

    # 4. 测试验证器的跳过功能
    print("\n[4/4] 测试验证器的跳过功能...")
    validator = CategoryValidator(
        api_key=config.anthropic_api_key,
        db_manager=db
    )

    print(f"✓ 验证器已加载 {len(validator.validated_asins)} 个已验证的ASIN")

    # 模拟批量验证（不实际调用API）
    print("\n模拟批量验证过程:")
    print("-" * 60)

    for i, product in enumerate(all_products, 1):
        if product.asin in validator.validated_asins:
            print(f"[{i}/{len(all_products)}] ⏭️  跳过: {product.asin} - {product.name[:40]}...")
        else:
            print(f"[{i}/{len(all_products)}] 🔍 需验证: {product.asin} - {product.name[:40]}...")

    print("-" * 60)
    print(f"\n统计:")
    print(f"  总产品数: {len(all_products)}")
    print(f"  跳过数量: {validated_count}")
    print(f"  需验证数量: {unvalidated_count}")

    if validated_count > 0:
        saved_time = validated_count * 4  # 假设每个产品验证需要4秒
        saved_cost = validated_count * 0.003  # 假设每次API调用$0.003
        print(f"  节省时间: 约{saved_time}秒")
        print(f"  节省成本: 约${saved_cost:.3f}")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)

    # 5. 测试单个ASIN检查
    if all_products:
        print("\n额外测试：检查单个ASIN是否已验证")
        test_asin = all_products[0].asin
        is_validated = db.is_asin_validated(test_asin)
        print(f"  ASIN: {test_asin}")
        print(f"  是否已验证: {'✓ 是' if is_validated else '✗ 否'}")

        if is_validated:
            validation = db.get_category_validation(test_asin)
            if validation:
                print(f"  验证结果:")
                print(f"    - 是否相关: {'是' if validation.is_relevant else '否'}")
                print(f"    - 分类正确: {'是' if validation.category_is_correct else '否'}")
                if validation.suggested_category:
                    print(f"    - 建议分类: {validation.suggested_category}")

if __name__ == "__main__":
    test_skip_validated()
