"""
新分析器测试模块
测试竞品对标、市场细分、趋势预测和综合评分功能
"""

import unittest
from datetime import datetime, timedelta
from src.database.models import Product, SellerSpiritData
from src.analyzers.competitor_analyzer import CompetitorAnalyzer
from src.analyzers.segmentation_analyzer import SegmentationAnalyzer
from src.analyzers.trend_analyzer import TrendAnalyzer
from src.analyzers.scoring_system import ScoringSystem


class TestCompetitorAnalyzer(unittest.TestCase):
    """竞品对标分析器测试"""

    def setUp(self):
        """设置测试数据"""
        self.analyzer = CompetitorAnalyzer()

        # 创建测试产品数据
        self.products = [
            Product(
                asin=f"TEST{i:03d}",
                name=f"Test Product {i}",
                brand="BrandA" if i < 30 else "BrandB" if i < 50 else "BrandC",
                price=20.0 + i,
                rating=4.0 + (i % 10) / 10,
                reviews_count=100 + i * 10,
                bsr_rank=1000 + i * 100
            )
            for i in range(100)
        ]

    def test_analyze_competitors(self):
        """测试竞品分析"""
        result = self.analyzer.analyze(self.products)

        # 验证基本结构
        self.assertIn('top_performers', result)
        self.assertIn('benchmark_products', result)
        self.assertIn('competitor_segments', result)

        # 验证Top表现者
        self.assertGreater(len(result['top_performers']), 0)

        # 验证表现者数据结构
        top_perf = result['top_performers'][0]
        self.assertIn('asin', top_perf)
        self.assertIn('title', top_perf)
        self.assertIn('brand', top_perf)
        self.assertIn('performance_score', top_perf)

    def test_empty_products(self):
        """测试空产品列表"""
        result = self.analyzer.analyze([])

        # 空列表应该返回空结果
        self.assertIn('top_performers', result)
        self.assertEqual(len(result['top_performers']), 0)


class TestSegmentationAnalyzer(unittest.TestCase):
    """市场细分分析器测试"""

    def setUp(self):
        """设置测试数据"""
        self.analyzer = SegmentationAnalyzer()

        # 创建不同价格段的产品
        self.products = []
        for i in range(100):
            price = 10.0 if i < 20 else 25.0 if i < 50 else 50.0 if i < 80 else 100.0
            self.products.append(Product(
                asin=f"TEST{i:03d}",
                name=f"Test Product {i}",
                brand=f"Brand{i % 10}",
                price=price,
                rating=4.0 + (i % 10) / 10,
                reviews_count=100 + i * 10,
                bsr_rank=1000 + i * 100
            ))

    def test_price_segmentation(self):
        """测试价格段分析"""
        result = self.analyzer.analyze(self.products)

        # 验证价格段存在
        self.assertIn('price_segments', result)
        price_seg = result['price_segments']
        self.assertIn('segments', price_seg)

    def test_brand_segmentation(self):
        """测试品牌段分析"""
        result = self.analyzer.analyze(self.products)

        # 验证品牌段存在
        self.assertIn('brand_segments', result)
        brand_seg = result['brand_segments']
        self.assertIn('top_brands', brand_seg)


class TestTrendAnalyzer(unittest.TestCase):
    """趋势预测分析器测试"""

    def setUp(self):
        """设置测试数据"""
        self.analyzer = TrendAnalyzer()

        # 创建不同上架时间的产品
        self.products = []
        base_date = datetime.now()
        for i in range(100):
            days_ago = i * 3  # 每个产品间隔3天
            available_date = (base_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            self.products.append(Product(
                asin=f"TEST{i:03d}",
                name=f"Test Product {i}",
                brand=f"Brand{i % 10}",
                price=20.0 + i,
                rating=4.0 + (i % 10) / 10,
                reviews_count=100 + i * 10,
                bsr_rank=1000 + i * 100,
                available_date=available_date
            ))

        # 创建卖家精灵数据
        self.sellerspirit_data = SellerSpiritData(
            keyword="test keyword",
            monthly_searches=10000,
            purchase_rate=8.5,
            click_rate=12.3,
            conversion_rate=6.8,
            monopoly_rate=35.2,
            cr4=45.5,
            keyword_extensions='["wireless mouse", "bluetooth mouse", "gaming mouse"]'
        )

    def test_market_trend_analysis(self):
        """测试市场趋势分析"""
        result = self.analyzer.analyze(self.products, self.sellerspirit_data)

        # 验证基本结构
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_new_product_growth(self):
        """测试新品增长分析"""
        result = self.analyzer.analyze(self.products, self.sellerspirit_data)

        # 验证基本结构
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_market_maturity(self):
        """测试市场成熟度分析"""
        result = self.analyzer.analyze(self.products, self.sellerspirit_data)

        # 验证基本结构
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)


class TestScoringSystem(unittest.TestCase):
    """综合评分系统测试"""

    def setUp(self):
        """设置测试数据"""
        self.scoring_system = ScoringSystem()

        # 创建测试产品
        self.products = [
            Product(
                asin=f"TEST{i:03d}",
                name=f"Test Product {i}",
                brand=f"Brand{i % 10}",
                price=20.0 + i,
                rating=4.0 + (i % 10) / 10,
                reviews_count=100 + i * 10,
                bsr_rank=1000 + i * 100
            )
            for i in range(100)
        ]

        # 创建卖家精灵数据
        self.sellerspirit_data = SellerSpiritData(
            keyword="test keyword",
            monthly_searches=10000,
            purchase_rate=8.5,
            click_rate=12.3,
            conversion_rate=6.8,
            monopoly_rate=35.2,
            cr4=45.5,
            keyword_extensions='["wireless mouse", "bluetooth mouse", "gaming mouse"]'
        )

    def test_market_scoring(self):
        """测试市场评分"""
        result = self.scoring_system.score_market(self.products, self.sellerspirit_data)

        # 验证评分结构
        self.assertIn('total_score', result)
        self.assertIn('grade', result)

        # 验证分数范围
        self.assertGreaterEqual(result['total_score'], 0)
        self.assertLessEqual(result['total_score'], 100)

    def test_key_factors(self):
        """测试关键因素"""
        result = self.scoring_system.score_market(self.products, self.sellerspirit_data)

        # 验证基本结构
        self.assertIsNotNone(result)
        self.assertIn('total_score', result)

    def test_product_scoring(self):
        """测试产品评分"""
        product = self.products[0]
        result = self.scoring_system.score_product(product)

        # 验证返回结构
        self.assertIn('total_score', result)
        self.assertIn('grade', result)
        self.assertIn('scores', result)

        # 验证分数范围
        score = result['total_score']
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_empty_products(self):
        """测试空产品列表"""
        result = self.scoring_system.score_market([], None)

        # 应该返回最低分
        self.assertEqual(result['total_score'], 0)
        self.assertEqual(result['grade'], 'F')


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """设置测试数据"""
        # 创建真实场景的测试数据
        self.products = []
        base_date = datetime.now()

        # 模拟真实市场：不同品牌、价格、评分、上架时间
        brands = ['BrandA', 'BrandB', 'BrandC', 'BrandD', 'BrandE']
        for i in range(200):
            days_ago = i * 2
            available_date = (base_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')

            self.products.append(Product(
                asin=f"TEST{i:04d}",
                name=f"Test Product {i}",
                brand=brands[i % len(brands)],
                price=10.0 + (i % 50) * 2,
                rating=3.5 + (i % 15) / 10,
                reviews_count=50 + i * 5,
                bsr_rank=500 + i * 50,
                available_date=available_date
            ))

        self.sellerspirit_data = SellerSpiritData(
            keyword="test keyword",
            monthly_searches=15000,
            purchase_rate=9.2,
            click_rate=13.5,
            conversion_rate=7.5,
            monopoly_rate=40.0,
            cr4=55.0,
            keyword_extensions='["wireless mouse", "bluetooth mouse", "gaming mouse", "ergonomic mouse"]'
        )

    def test_full_analysis_pipeline(self):
        """测试完整分析流程"""
        # 1. 竞品分析
        competitor_analyzer = CompetitorAnalyzer()
        competitor_result = competitor_analyzer.analyze(self.products)
        self.assertIsNotNone(competitor_result)

        # 2. 市场细分
        segmentation_analyzer = SegmentationAnalyzer()
        segmentation_result = segmentation_analyzer.analyze(self.products)
        self.assertIsNotNone(segmentation_result)

        # 3. 趋势预测
        trend_analyzer = TrendAnalyzer()
        trend_result = trend_analyzer.analyze(self.products, self.sellerspirit_data)
        self.assertIsNotNone(trend_result)

        # 4. 综合评分
        scoring_system = ScoringSystem()
        score_result = scoring_system.score_market(self.products, self.sellerspirit_data)
        self.assertIsNotNone(score_result)

        # 验证所有分析结果都有数据
        self.assertGreater(len(competitor_result['top_performers']), 0)
        self.assertIn('price_segments', segmentation_result)
        self.assertIsNotNone(trend_result)
        self.assertGreater(score_result['total_score'], 0)


if __name__ == '__main__':
    unittest.main()
