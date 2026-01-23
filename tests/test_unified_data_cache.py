"""
统一数据缓存管理器测试用例

测试 UnifiedDataCache 的核心功能：
- 基本的 get/set/exists/delete 操作
- 批量操作
- TTL 过期机制
- 统计信息
- 4种数据源的缓存场景
"""

import unittest
import tempfile
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.unified_data_cache import (
    UnifiedDataCache,
    DataSource,
    RawDataCacheEntry
)


class TestUnifiedDataCacheBasic(unittest.TestCase):
    """基本功能测试"""

    def setUp(self):
        """每个测试前创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_cache.db"
        self.cache = UnifiedDataCache(db_path=self.db_path)

    def tearDown(self):
        """清理临时文件"""
        if self.db_path.exists():
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_set_and_get(self):
        """测试基本的设置和获取"""
        test_data = {"asin": "B0D4RL8V3H", "name": "Test Product", "price": 29.99}

        # 设置缓存
        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", test_data)

        # 获取缓存
        result = self.cache.get(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H")

        self.assertIsNotNone(result)
        self.assertEqual(result["asin"], "B0D4RL8V3H")
        self.assertEqual(result["name"], "Test Product")
        self.assertEqual(result["price"], 29.99)

    def test_get_nonexistent(self):
        """测试获取不存在的缓存"""
        result = self.cache.get(DataSource.SCRAPER_PRODUCT, "NONEXISTENT")
        self.assertIsNone(result)

    def test_exists(self):
        """测试缓存存在性检查"""
        test_data = {"keyword": "camping", "monthly_searches": 50000}

        # 不存在
        self.assertFalse(self.cache.exists(DataSource.SELLERSPIRIT, "camping"))

        # 设置后存在
        self.cache.set(DataSource.SELLERSPIRIT, "camping", test_data)
        self.assertTrue(self.cache.exists(DataSource.SELLERSPIRIT, "camping"))

    def test_delete(self):
        """测试删除缓存"""
        test_data = {"asin": "B0D4RL8V3H"}

        self.cache.set(DataSource.APIFY_API, "B0D4RL8V3H", test_data)
        self.assertTrue(self.cache.exists(DataSource.APIFY_API, "B0D4RL8V3H"))

        # 删除
        result = self.cache.delete(DataSource.APIFY_API, "B0D4RL8V3H")
        self.assertTrue(result)
        self.assertFalse(self.cache.exists(DataSource.APIFY_API, "B0D4RL8V3H"))

    def test_delete_nonexistent(self):
        """测试删除不存在的缓存"""
        result = self.cache.delete(DataSource.APIFY_API, "NONEXISTENT")
        self.assertFalse(result)

    def test_update_existing(self):
        """测试更新已存在的缓存"""
        # 初始数据
        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", {"price": 29.99})

        # 更新数据
        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", {"price": 39.99})

        result = self.cache.get(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H")
        self.assertEqual(result["price"], 39.99)


class TestUnifiedDataCacheTTL(unittest.TestCase):
    """TTL 过期机制测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_cache.db"
        self.cache = UnifiedDataCache(db_path=self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_default_ttl_by_source(self):
        """测试不同数据源的默认TTL"""
        # sellerspirit 默认 168 小时 (7天)
        self.cache.set(DataSource.SELLERSPIRIT, "camping", {"data": 1})
        entry = self.cache.get_entry(DataSource.SELLERSPIRIT, "camping")
        self.assertEqual(entry.ttl_hours, 168)

        # scraper_product 默认 24 小时
        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", {"data": 1})
        entry = self.cache.get_entry(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H")
        self.assertEqual(entry.ttl_hours, 24)

    def test_custom_ttl(self):
        """测试自定义TTL"""
        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", {"data": 1}, ttl_hours=48)
        entry = self.cache.get_entry(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H")
        self.assertEqual(entry.ttl_hours, 48)

    def test_expired_cache_returns_none(self):
        """测试过期缓存返回None"""
        # 设置一个已过期的缓存（TTL=0 表示立即过期，用于测试）
        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", {"data": 1}, ttl_hours=-1)

        result = self.cache.get(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H")
        self.assertIsNone(result)

    def test_cleanup_expired(self):
        """测试清理过期缓存"""
        # 添加一个过期的和一个未过期的
        self.cache.set(DataSource.SCRAPER_PRODUCT, "EXPIRED", {"data": 1}, ttl_hours=-1)
        self.cache.set(DataSource.SCRAPER_PRODUCT, "VALID", {"data": 2}, ttl_hours=24)

        # 清理过期
        cleaned = self.cache.cleanup_expired()
        self.assertEqual(cleaned, 1)

        # 验证
        self.assertFalse(self.cache.exists(DataSource.SCRAPER_PRODUCT, "EXPIRED"))
        self.assertTrue(self.cache.exists(DataSource.SCRAPER_PRODUCT, "VALID"))


class TestUnifiedDataCacheBatch(unittest.TestCase):
    """批量操作测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_cache.db"
        self.cache = UnifiedDataCache(db_path=self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_batch(self):
        """测试批量获取"""
        # 设置多个缓存
        self.cache.set(DataSource.SCRAPER_PRODUCT, "ASIN1", {"name": "Product 1"})
        self.cache.set(DataSource.SCRAPER_PRODUCT, "ASIN2", {"name": "Product 2"})
        self.cache.set(DataSource.SCRAPER_PRODUCT, "ASIN3", {"name": "Product 3"})

        # 批量获取（包含一个不存在的）
        results = self.cache.get_batch(DataSource.SCRAPER_PRODUCT, ["ASIN1", "ASIN2", "ASIN4"])

        self.assertEqual(len(results), 2)
        self.assertIn("ASIN1", results)
        self.assertIn("ASIN2", results)
        self.assertNotIn("ASIN4", results)

    def test_set_batch(self):
        """测试批量设置"""
        data_dict = {
            "ASIN1": {"name": "Product 1"},
            "ASIN2": {"name": "Product 2"},
            "ASIN3": {"name": "Product 3"}
        }

        count = self.cache.set_batch(DataSource.SCRAPER_PRODUCT, data_dict)
        self.assertEqual(count, 3)

        # 验证
        for asin in data_dict:
            self.assertTrue(self.cache.exists(DataSource.SCRAPER_PRODUCT, asin))

    def test_get_missing_keys(self):
        """测试获取缺失的键"""
        self.cache.set(DataSource.SCRAPER_PRODUCT, "ASIN1", {"name": "Product 1"})
        self.cache.set(DataSource.SCRAPER_PRODUCT, "ASIN2", {"name": "Product 2"})

        missing = self.cache.get_missing_keys(
            DataSource.SCRAPER_PRODUCT,
            ["ASIN1", "ASIN2", "ASIN3", "ASIN4"]
        )

        self.assertEqual(set(missing), {"ASIN3", "ASIN4"})


class TestUnifiedDataCacheDataSources(unittest.TestCase):
    """4种数据源场景测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_cache.db"
        self.cache = UnifiedDataCache(db_path=self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_sellerspirit_cache(self):
        """测试卖家精灵数据缓存"""
        ss_data = {
            "keyword": "camping",
            "monthly_searches": 50000,
            "purchase_rate": 0.15,
            "cr4": 45.5,
            "seasonality_index": 35.0
        }

        self.cache.set(DataSource.SELLERSPIRIT, "camping", ss_data)
        result = self.cache.get(DataSource.SELLERSPIRIT, "camping")

        self.assertEqual(result["monthly_searches"], 50000)
        self.assertEqual(result["cr4"], 45.5)

    def test_apify_api_cache(self):
        """测试Apify API数据缓存"""
        apify_data = {
            "asin": "B0D4RL8V3H",
            "name": "Test Product",
            "pricing": "$31.98",
            "average_rating": 4.5,
            "total_reviews": 518
        }

        self.cache.set(DataSource.APIFY_API, "B0D4RL8V3H", apify_data)
        result = self.cache.get(DataSource.APIFY_API, "B0D4RL8V3H")

        self.assertEqual(result["pricing"], "$31.98")
        self.assertEqual(result["total_reviews"], 518)

    def test_scraper_search_cache(self):
        """测试ScraperAPI搜索结果缓存"""
        search_data = [
            {"asin": "ASIN1", "name": "Product 1", "position": 1},
            {"asin": "ASIN2", "name": "Product 2", "position": 2},
            {"asin": "ASIN3", "name": "Product 3", "position": 3}
        ]

        self.cache.set(DataSource.SCRAPER_SEARCH, "camping", search_data)
        result = self.cache.get(DataSource.SCRAPER_SEARCH, "camping")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["asin"], "ASIN1")

    def test_scraper_product_cache(self):
        """测试ScraperAPI产品详情缓存"""
        product_data = {
            "asin": "B0F28JG95D",
            "name": "THTYBROS Camping Cookware Kit",
            "brand": "THTYBROS",
            "pricing": "$31.98",
            "product_category": "Sports & Outdoors",
            "average_rating": 4.5
        }

        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0F28JG95D", product_data)
        result = self.cache.get(DataSource.SCRAPER_PRODUCT, "B0F28JG95D")

        self.assertEqual(result["brand"], "THTYBROS")
        self.assertEqual(result["average_rating"], 4.5)

    def test_different_sources_same_key(self):
        """测试不同数据源可以使用相同的键"""
        # 同一个ASIN在不同数据源中存储不同数据
        self.cache.set(DataSource.APIFY_API, "B0D4RL8V3H", {"source": "apify", "price": 29.99})
        self.cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", {"source": "scraper", "price": 31.99})

        apify_result = self.cache.get(DataSource.APIFY_API, "B0D4RL8V3H")
        scraper_result = self.cache.get(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H")

        self.assertEqual(apify_result["source"], "apify")
        self.assertEqual(apify_result["price"], 29.99)
        self.assertEqual(scraper_result["source"], "scraper")
        self.assertEqual(scraper_result["price"], 31.99)


class TestUnifiedDataCacheStats(unittest.TestCase):
    """统计信息测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_cache.db"
        self.cache = UnifiedDataCache(db_path=self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_stats(self):
        """测试获取统计信息"""
        # 添加一些数据
        self.cache.set(DataSource.SELLERSPIRIT, "kw1", {"data": 1})
        self.cache.set(DataSource.SELLERSPIRIT, "kw2", {"data": 2})
        self.cache.set(DataSource.SCRAPER_PRODUCT, "asin1", {"data": 3})

        stats = self.cache.get_stats()

        self.assertEqual(stats["total_entries"], 3)
        self.assertEqual(stats["by_source"][DataSource.SELLERSPIRIT.value], 2)
        self.assertEqual(stats["by_source"][DataSource.SCRAPER_PRODUCT.value], 1)

    def test_hit_count_increment(self):
        """测试命中次数递增"""
        self.cache.set(DataSource.SCRAPER_PRODUCT, "ASIN1", {"data": 1})

        # 多次获取
        self.cache.get(DataSource.SCRAPER_PRODUCT, "ASIN1")
        self.cache.get(DataSource.SCRAPER_PRODUCT, "ASIN1")
        self.cache.get(DataSource.SCRAPER_PRODUCT, "ASIN1")

        entry = self.cache.get_entry(DataSource.SCRAPER_PRODUCT, "ASIN1")
        self.assertEqual(entry.hit_count, 3)


class TestRawDataCacheEntry(unittest.TestCase):
    """缓存条目模型测试"""

    def test_is_expired(self):
        """测试过期判断"""
        # 未过期
        future_time = datetime.now() + timedelta(hours=1)
        entry = RawDataCacheEntry(
            source="test",
            key_type="asin",
            key_value="TEST",
            data_json="{}",
            expires_at=future_time.isoformat()
        )
        self.assertFalse(entry.is_expired)

        # 已过期
        past_time = datetime.now() - timedelta(hours=1)
        entry.expires_at = past_time.isoformat()
        self.assertTrue(entry.is_expired)

    def test_to_dict_and_from_dict(self):
        """测试字典转换"""
        entry = RawDataCacheEntry(
            source="scraper_product",
            key_type="asin",
            key_value="B0D4RL8V3H",
            data_json='{"name": "Test"}',
            ttl_hours=24,
            hit_count=5
        )

        data = entry.to_dict()
        restored = RawDataCacheEntry.from_dict(data)

        self.assertEqual(restored.source, entry.source)
        self.assertEqual(restored.key_value, entry.key_value)
        self.assertEqual(restored.hit_count, entry.hit_count)


if __name__ == "__main__":
    unittest.main()
