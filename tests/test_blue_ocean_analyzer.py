"""
蓝海分析器测试
测试蓝海产品识别和评分功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analyzers.blue_ocean_analyzer import BlueOceanAnalyzer
from src.database.models import Product, SellerSpiritData


def test_competition_index():
    """测试竞争指数计算"""
    print("\n" + "=" * 60)
    print("测试1: 市场竞争指数计算")
    print("=" * 60)

    analyzer = BlueOceanAnalyzer()

    # 创建测试产品列表
    products = [
        Product(
            asin="TEST001",
            name="Test Product 1",
            price=25.99,
            rating=4.2,
            reviews_count=50,
            sales_volume=100,
            bsr_rank=5000,
            brand="Brand A"
        ),
        Product(
            asin="TEST002",
            name="Test Product 2",
            price=27.99,
            rating=4.5,
            reviews_count=150,
            sales_volume=200,
            bsr_rank=3000,
            brand="Brand B"
        ),
        Product(
            asin="TEST003",
            name="Test Product 3",
            price=29.99,
            rating=4.3,
            reviews_count=80,
            sales_volume=150,
            bsr_rank=4000,
            brand="Brand A"
        ),
    ]

    # 计算市场竞争指数
    market_competition = analyzer._calculate_market_competition(products)

    print(f"\n市场竞争分析:")
    print(f"  - 综合竞争指数: {market_competition['competition_index']:.2f}")
    print(f"  - 评论密度得分: {market_competition['review_density_score']:.2f}")
    print(f"  - 评分质量得分: {market_competition['rating_quality_score']:.2f}")
    print(f"  - 品牌集中度: {market_competition['brand_concentration']:.2f}")
    print(f"  - 价格竞争度: {market_competition['price_competition_score']:.2f}")
    print(f"  - 平均评论数: {market_competition['avg_reviews']:.2f}")
    print(f"  - 平均评分: {market_competition['avg_rating']:.2f}")

    # 验证结果
    assert 0 <= market_competition['competition_index'] <= 100, "竞争指数应该在0-100之间"
    assert market_competition['avg_reviews'] > 0, "平均评论数应该大于0"

    print("\n✓ 市场竞争指数计算测试通过")


def test_product_scoring():
    """测试产品评分"""
    print("\n" + "=" * 60)
    print("测试2: 蓝海产品识别")
    print("=" * 60)

    analyzer = BlueOceanAnalyzer(
        competition_threshold=50.0,
        min_sales_volume=50,
        max_sales_volume=500,
        min_reviews=20,
        max_reviews=500,
        min_rating=3.8,
        max_avg_reviews=300
    )

    # 创建测试产品列表
    products = [
        # 蓝海产品候选
        Product(
            asin="TEST001",
            name="Blue Ocean Candidate 1",
            price=25.99,
            rating=4.2,
            reviews_count=80,
            sales_volume=150,
            bsr_rank=5000,
            brand="Brand A"
        ),
        Product(
            asin="TEST002",
            name="Blue Ocean Candidate 2",
            price=30.00,
            rating=4.3,
            reviews_count=120,
            sales_volume=200,
            bsr_rank=3000,
            brand="Brand B"
        ),
        # 高竞争产品（评论数太多）
        Product(
            asin="TEST003",
            name="High Competition Product",
            price=25.99,
            rating=4.5,
            reviews_count=5000,
            sales_volume=1000,
            bsr_rank=100,
            brand="Brand C"
        ),
    ]

    # 计算市场竞争
    market_competition = analyzer._calculate_market_competition(products)

    print(f"\n市场竞争指数: {market_competition['competition_index']:.2f}")

    # 识别蓝海产品
    blue_ocean_products = analyzer._identify_blue_ocean_products(products, market_competition)

    print(f"\n识别结果:")
    print(f"  - 总产品数: {len(products)}")
    print(f"  - 蓝海产品数: {len(blue_ocean_products)}")

    for product in blue_ocean_products:
        print(f"  - {product.asin}: {product.name}")
        print(f"    评论数: {product.reviews_count}, 销量: {product.sales_volume}, 评分: {product.rating}")

    # 验证结果
    assert len(blue_ocean_products) >= 1, "应该至少识别出1个蓝海产品"

    print("\n✓ 蓝海产品识别测试通过")


def test_blue_ocean_identification():
    """测试完整的蓝海分析流程"""
    print("\n" + "=" * 60)
    print("测试3: 完整蓝海分析流程")
    print("=" * 60)

    analyzer = BlueOceanAnalyzer(
        competition_threshold=50.0,
        min_sales_volume=50,
        max_sales_volume=500,
        min_reviews=20,
        max_reviews=500,
        min_rating=3.8,
        max_avg_reviews=300
    )

    # 创建测试产品列表
    products = [
        # 蓝海产品
        Product(
            asin="BLUE001",
            name="Blue Ocean Product 1",
            price=25.99,
            rating=4.2,
            reviews_count=80,
            sales_volume=150,
            bsr_rank=5000,
            brand="Brand A"
        ),
        Product(
            asin="BLUE002",
            name="Blue Ocean Product 2",
            price=28.99,
            rating=4.1,
            reviews_count=100,
            sales_volume=180,
            bsr_rank=4500,
            brand="Brand B"
        ),
        # 红海产品（评论数太多）
        Product(
            asin="RED001",
            name="Red Ocean Product 1",
            price=25.99,
            rating=4.5,
            reviews_count=5000,
            sales_volume=1000,
            bsr_rank=100,
            brand="Brand C"
        ),
        # 不合格产品（评分太低）
        Product(
            asin="BAD001",
            name="Bad Product 1",
            price=25.99,
            rating=3.5,
            reviews_count=100,
            sales_volume=50,
            bsr_rank=8000,
            brand="Brand D"
        ),
    ]

    # 创建卖家精灵数据
    sellerspirit_data = SellerSpiritData(
        keyword="test keyword",
        monthly_searches=10000,
        purchase_rate=0.15,
        click_rate=0.25,
        conversion_rate=0.12,
        monopoly_rate=0.30,
        cr4=0.45
    )

    # 执行分析
    result = analyzer.analyze(products, sellerspirit_data)

    print(f"\n分析结果:")
    print(f"  - 市场竞争指数: {result['market_competition']['competition_index']:.2f}")
    print(f"  - 蓝海产品数: {result['blue_ocean_count']}")
    print(f"  - 蓝海产品占比: {result['blue_ocean_rate']:.1f}%")

    if result['blue_ocean_products']:
        print(f"\n蓝海产品列表:")
        for product_dict in result['blue_ocean_products'][:5]:  # 只显示前5个
            print(f"  - {product_dict['asin']}: {product_dict['name']}")

    # 验证结果
    assert result['blue_ocean_count'] >= 1, "应该至少识别出1个蓝海产品"
    assert 'market_competition' in result, "结果应包含市场竞争数据"
    assert 'opportunity_assessment' in result, "结果应包含机会评估"

    print("\n✓ 完整蓝海分析流程测试通过")


def test_market_analysis():
    """测试市场分析统计"""
    print("\n" + "=" * 60)
    print("测试4: 市场分析统计")
    print("=" * 60)

    analyzer = BlueOceanAnalyzer()

    # 创建多个测试产品
    products = []
    for i in range(10):
        products.append(Product(
            asin=f"TEST{i:03d}",
            name=f"Test Product {i}",
            price=20.0 + i * 5,
            rating=3.8 + i * 0.05,
            reviews_count=50 + i * 50,
            sales_volume=100 + i * 50,
            bsr_rank=1000 + i * 500,
            brand=f"Brand {chr(65 + i % 3)}"  # Brand A, B, C
        ))

    # 创建卖家精灵数据
    sellerspirit_data = SellerSpiritData(
        keyword="test keyword",
        monthly_searches=15000,
        purchase_rate=0.18,
        click_rate=0.28,
        conversion_rate=0.15,
        monopoly_rate=0.25,
        cr4=0.40
    )

    # 执行分析
    result = analyzer.analyze(products, sellerspirit_data)

    print(f"\n市场分析结果:")
    print(f"  - 市场竞争指数: {result['market_competition']['competition_index']:.2f}")
    print(f"  - 蓝海产品数: {result['blue_ocean_count']}")
    print(f"  - 蓝海产品占比: {result['blue_ocean_rate']:.1f}%")

    # 验证结果结构
    assert 'market_competition' in result
    assert 'blue_ocean_count' in result
    assert 'blue_ocean_products' in result
    assert 'opportunity_assessment' in result

    print("\n✓ 市场分析统计测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("蓝海分析器测试套件")
    print("=" * 60)

    try:
        test_competition_index()
        test_product_scoring()
        test_blue_ocean_identification()
        test_market_analysis()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
