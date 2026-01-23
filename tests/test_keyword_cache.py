"""
测试关键词缓存管理器
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from src.collectors.keyword_cache_manager import KeywordCacheManager


class TestKeywordCacheManager:
    """测试关键词缓存管理器"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """创建缓存管理器实例"""
        return KeywordCacheManager(cache_dir=temp_cache_dir)

    @pytest.fixture
    def sample_search_results(self):
        """示例搜索结果"""
        return [
            {
                'asin': 'B001',
                'name': 'Test Product 1',
                'brand': 'Test Brand',
                'category': 'Test Category',
                'price': '19.99',
                'rating': 4.5,
                'reviews_count': 100,
                'purchase_history_message': '500+ bought in past month',
                'page': 1,
                'position': 1,
                'url': 'https://amazon.com/dp/B001',
                'image': 'https://example.com/image1.jpg'
            },
            {
                'asin': 'B002',
                'name': 'Test Product 2',
                'brand': 'Test Brand 2',
                'category': 'Test Category',
                'price': '29.99',
                'rating': 4.8,
                'reviews_count': 200,
                'purchase_history_message': '1K+ bought in past month',
                'page': 1,
                'position': 2,
                'url': 'https://amazon.com/dp/B002',
                'image': 'https://example.com/image2.jpg'
            }
        ]

    def test_init(self, cache_manager, temp_cache_dir):
        """测试初始化"""
        assert cache_manager.cache_dir == Path(temp_cache_dir)
        assert cache_manager.cache_dir.exists()
        assert cache_manager.metadata_file.exists()

    def test_save_and_load_cache(self, cache_manager, sample_search_results):
        """测试保存和加载缓存"""
        keyword = "camping tent"

        # 保存缓存
        csv_path = cache_manager.save_to_cache(
            keyword=keyword,
            search_results=sample_search_results,
            country_code='us'
        )

        assert Path(csv_path).exists()

        # 检查缓存是否存在
        assert cache_manager.has_cache(keyword, 'us')

        # 加载缓存
        loaded_results = cache_manager.load_from_cache(keyword, 'us')

        assert loaded_results is not None
        assert len(loaded_results) == len(sample_search_results)

        # 验证数据
        assert loaded_results[0]['asin'] == 'B001'
        assert loaded_results[0]['name'] == 'Test Product 1'
        assert loaded_results[0]['sales_volume'] == 500
        assert loaded_results[1]['sales_volume'] == 1000

    def test_cache_info(self, cache_manager, sample_search_results):
        """测试获取缓存信息"""
        keyword = "camping tent"

        # 保存缓存
        cache_manager.save_to_cache(
            keyword=keyword,
            search_results=sample_search_results,
            country_code='us',
            additional_info={'pages_scraped': 5, 'total_asins': 100}
        )

        # 获取缓存信息
        cache_info = cache_manager.get_cache_info(keyword, 'us')

        assert cache_info is not None
        assert cache_info['keyword'] == keyword
        assert cache_info['country_code'] == 'us'
        assert cache_info['record_count'] == 2
        assert 'cached_at' in cache_info
        assert cache_info['additional_info']['pages_scraped'] == 5

    def test_has_cache(self, cache_manager, sample_search_results):
        """测试检查缓存是否存在"""
        keyword = "camping tent"

        # 缓存不存在
        assert not cache_manager.has_cache(keyword, 'us')

        # 保存缓存
        cache_manager.save_to_cache(
            keyword=keyword,
            search_results=sample_search_results,
            country_code='us'
        )

        # 缓存存在
        assert cache_manager.has_cache(keyword, 'us')

    def test_clear_cache_single(self, cache_manager, sample_search_results):
        """测试清除单个缓存"""
        keyword = "camping tent"

        # 保存缓存
        cache_manager.save_to_cache(
            keyword=keyword,
            search_results=sample_search_results,
            country_code='us'
        )

        assert cache_manager.has_cache(keyword, 'us')

        # 清除缓存
        cache_manager.clear_cache(keyword, 'us')

        assert not cache_manager.has_cache(keyword, 'us')

    def test_clear_cache_all(self, cache_manager, sample_search_results):
        """测试清除所有缓存"""
        # 保存多个缓存
        cache_manager.save_to_cache(
            keyword="camping tent",
            search_results=sample_search_results,
            country_code='us'
        )
        cache_manager.save_to_cache(
            keyword="hiking backpack",
            search_results=sample_search_results,
            country_code='us'
        )

        assert cache_manager.has_cache("camping tent", 'us')
        assert cache_manager.has_cache("hiking backpack", 'us')

        # 清除所有缓存
        cache_manager.clear_cache()

        assert not cache_manager.has_cache("camping tent", 'us')
        assert not cache_manager.has_cache("hiking backpack", 'us')

    def test_list_cached_keywords(self, cache_manager, sample_search_results):
        """测试列出所有缓存的关键词"""
        # 保存多个缓存
        cache_manager.save_to_cache(
            keyword="camping tent",
            search_results=sample_search_results,
            country_code='us'
        )
        cache_manager.save_to_cache(
            keyword="hiking backpack",
            search_results=sample_search_results,
            country_code='us'
        )

        # 列出缓存
        cached_keywords = cache_manager.list_cached_keywords()

        assert len(cached_keywords) == 2
        keywords = [info['keyword'] for info in cached_keywords]
        assert "camping tent" in keywords
        assert "hiking backpack" in keywords

    def test_get_cache_statistics(self, cache_manager, sample_search_results):
        """测试获取缓存统计信息"""
        # 保存缓存
        cache_manager.save_to_cache(
            keyword="camping tent",
            search_results=sample_search_results,
            country_code='us'
        )

        # 获取统计信息
        stats = cache_manager.get_cache_statistics()

        assert stats['total_keywords'] == 1
        assert stats['total_records'] == 2
        assert stats['total_size_mb'] > 0
        assert 'camping tent_us' in stats['keywords']

    def test_parse_purchase_count(self, cache_manager):
        """测试解析购买数量"""
        test_cases = [
            ('500+ bought in past month', 500),
            ('1K+ bought in past month', 1000),
            ('2.5K+ bought in past month', 2500),
            ('1M+ bought in past month', 1000000),
            ('100+ bought', 100),
            (None, None),
            ('', None),
            ('No purchase info', None)
        ]

        for message, expected in test_cases:
            result = cache_manager._parse_purchase_count(message)
            assert result == expected, f"Failed for message: {message}"

    def test_special_characters_in_keyword(self, cache_manager, sample_search_results):
        """测试关键词中包含特殊字符"""
        keyword = "camping/tent & gear (outdoor)"

        # 保存缓存
        csv_path = cache_manager.save_to_cache(
            keyword=keyword,
            search_results=sample_search_results,
            country_code='us'
        )

        # 验证文件名安全
        assert Path(csv_path).exists()
        assert '/' not in Path(csv_path).name
        assert '&' not in Path(csv_path).name

        # 验证可以加载
        assert cache_manager.has_cache(keyword, 'us')
        loaded_results = cache_manager.load_from_cache(keyword, 'us')
        assert loaded_results is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
