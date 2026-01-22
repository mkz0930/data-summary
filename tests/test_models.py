"""
单元测试 - 数据模型测试
"""

import unittest
from datetime import datetime

from src.database.models import Product, CategoryValidation, SellerSpiritData, AnalysisResult


class TestProductModel(unittest.TestCase):
    """测试Product模型"""

    def test_product_creation(self):
        """测试产品创建"""
        product = Product(
            asin="B001TEST",
            name="Test Product",
            price=29.99,
            rating=4.5,
            reviews_count=100
        )

        self.assertEqual(product.asin, "B001TEST")
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, 29.99)
        self.assertEqual(product.rating, 4.5)
        self.assertEqual(product.reviews_count, 100)

    def test_product_to_dict(self):
        """测试产品转字典"""
        product = Product(
            asin="B001TEST",
            name="Test Product",
            price=29.99
        )

        data = product.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['asin'], "B001TEST")
        self.assertEqual(data['name'], "Test Product")
        self.assertEqual(data['price'], 29.99)

    def test_product_from_dict(self):
        """测试从字典创建产品"""
        data = {
            'asin': 'B001TEST',
            'name': 'Test Product',
            'price': 29.99,
            'rating': 4.5
        }

        product = Product.from_dict(data)
        self.assertEqual(product.asin, "B001TEST")
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, 29.99)
        self.assertEqual(product.rating, 4.5)


class TestCategoryValidation(unittest.TestCase):
    """测试CategoryValidation模型"""

    def test_validation_creation(self):
        """测试验证创建"""
        validation = CategoryValidation(
            asin="B001TEST",
            is_relevant=True,
            category_is_correct=False,
            suggested_category="New Category"
        )

        self.assertEqual(validation.asin, "B001TEST")
        self.assertTrue(validation.is_relevant)
        self.assertFalse(validation.category_is_correct)
        self.assertEqual(validation.suggested_category, "New Category")


if __name__ == '__main__':
    unittest.main()
