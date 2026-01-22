"""
单元测试 - 市场分析器测试
"""

import unittest
from src.analyzers.market_analyzer import MarketAnalyzer
from src.database.models import Product, SellerSpiritData


class TestMarketAnalyzer(unittest.TestCase):
    """测试市场分析器"""

    def setUp(self):
        """设置测试数据"""
        self.analyzer = MarketAnalyzer()
        self.products = [
            Product(asin="B001", name="Product 1", brand="Brand A", price=29.99, rating=4.5, reviews_count=100),
            Product(asin="B002", name="Product 2", brand="Brand A", price=39.99, rating=4.0, reviews_count=200),
            Product(asin="B003", name="Product 3", brand="Brand B", price=49.99, rating=4.8, reviews_count=150),
            Product(asin="B004", name="Product 4", brand="Brand C", price=59.99, rating=3.5, reviews_count=50),
            Product(asin="B005", name="Product 5", brand="Brand A", price=69.99, rating=4.2, reviews_count=300),
        ]
        self.sellerspirit_data = SellerSpiritData(
            keyword="test",
            monthly_searches=50000,
            cr4=45.5
        )

    def test_analyze(self):
        """测试综合分析"""
        result = self.analyzer.analyze(self.products, self.sellerspirit_data)

        self.assertIn('market_size', result)
        self.assertIn('competition', result)
        self.assertIn('brand_concentration', result)
        self.assertIn('market_blank_index', result)

    def test_market_size(self):
        """测试市场规模分析"""
        result = self.analyzer.analyze(self.products, self.sellerspirit_data)
        market_size = result['market_size']

        self.assertEqual(market_size['total_asins'], 5)
        self.assertEqual(market_size['monthly_searches'], 50000)

    def test_brand_concentration(self):
        """测试品牌集中度"""
        result = self.analyzer.analyze(self.products, self.sellerspirit_data)
        brand_conc = result['brand_concentration']

        self.assertEqual(brand_conc['total_brands'], 3)
        self.assertGreater(brand_conc['cr4'], 0)
        self.assertIsInstance(brand_conc['top_brands'], list)

    def test_market_blank_index(self):
        """测试市场空白指数"""
        result = self.analyzer.analyze(self.products, self.sellerspirit_data)
        blank_index = result['market_blank_index']

        # 50000 / 5 = 10000
        self.assertEqual(blank_index, 10000.0)


if __name__ == '__main__':
    unittest.main()
