"""
单元测试 - 价格分析器测试
"""

import unittest
from src.analyzers.price_analyzer import PriceAnalyzer
from src.database.models import Product


class TestPriceAnalyzer(unittest.TestCase):
    """测试价格分析器"""

    def setUp(self):
        """设置测试数据"""
        self.analyzer = PriceAnalyzer()
        self.products = [
            Product(asin="B001", name="Product 1", price=15.99, rating=4.5, reviews_count=100),
            Product(asin="B002", name="Product 2", price=25.99, rating=4.0, reviews_count=200),
            Product(asin="B003", name="Product 3", price=35.99, rating=4.8, reviews_count=150),
            Product(asin="B004", name="Product 4", price=55.99, rating=3.5, reviews_count=50),
            Product(asin="B005", name="Product 5", price=75.99, rating=4.2, reviews_count=300),
        ]

    def test_analyze(self):
        """测试综合分析"""
        result = self.analyzer.analyze(self.products)

        self.assertIn('distribution', result)
        self.assertIn('statistics', result)
        self.assertIn('price_bands', result)

    def test_calculate_statistics(self):
        """测试统计计算"""
        result = self.analyzer.analyze(self.products)
        stats = result['statistics']

        self.assertGreater(stats['mean'], 0)
        self.assertGreater(stats['median'], 0)
        self.assertEqual(stats['min'], 15.99)
        self.assertEqual(stats['max'], 75.99)

    def test_price_distribution(self):
        """测试价格分布"""
        result = self.analyzer.analyze(self.products)
        distribution = result['distribution']

        self.assertEqual(distribution['total_products'], 5)
        self.assertIsInstance(distribution['bands'], list)


if __name__ == '__main__':
    unittest.main()
