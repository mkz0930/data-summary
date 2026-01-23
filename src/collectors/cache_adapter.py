"""
统一数据缓存适配器

为现有的4个采集器提供统一缓存接口的适配器。
保持向后兼容，同时将数据统一存储到 raw_data_cache 表。

使用示例:
    from src.collectors.cache_adapter import CacheAdapter, DataSource

    # 创建适配器
    adapter = CacheAdapter()

    # 缓存卖家精灵数据
    adapter.cache_sellerspirit("camping", ss_data.to_dict())

    # 获取缓存
    data = adapter.get_sellerspirit("camping")

    # 缓存产品详情
    adapter.cache_product("B0D4RL8V3H", product_data, source=DataSource.SCRAPER_PRODUCT)

    # 批量检查缺失的ASIN
    missing = adapter.get_missing_asins(["ASIN1", "ASIN2"], source=DataSource.APIFY_API)
"""

from typing import Any, Dict, List, Optional
from src.collectors.unified_data_cache import (
    UnifiedDataCache,
    DataSource,
    get_unified_cache
)
from src.utils.logger import get_logger


class CacheAdapter:
    """
    统一缓存适配器

    为4种数据源提供便捷的缓存接口
    """

    def __init__(self, cache: Optional[UnifiedDataCache] = None):
        """
        初始化适配器

        Args:
            cache: UnifiedDataCache实例，默认使用全局单例
        """
        self.cache = cache or get_unified_cache()
        self.logger = get_logger()

    # ==================== 卖家精灵数据 ====================

    def cache_sellerspirit(
        self,
        keyword: str,
        data: Dict[str, Any],
        ttl_hours: int = 168  # 7天
    ) -> bool:
        """
        缓存卖家精灵数据

        Args:
            keyword: 关键词
            data: 卖家精灵数据字典
            ttl_hours: 缓存有效期（小时）

        Returns:
            是否成功
        """
        return self.cache.set(DataSource.SELLERSPIRIT, keyword, data, ttl_hours)

    def get_sellerspirit(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        获取卖家精灵缓存数据

        Args:
            keyword: 关键词

        Returns:
            缓存数据
        """
        return self.cache.get(DataSource.SELLERSPIRIT, keyword)

    def has_sellerspirit(self, keyword: str) -> bool:
        """
        检查是否有卖家精灵缓存

        Args:
            keyword: 关键词

        Returns:
            是否存在
        """
        return self.cache.exists(DataSource.SELLERSPIRIT, keyword)

    # ==================== ScraperAPI 搜索结果 ====================

    def cache_search_results(
        self,
        keyword: str,
        results: List[Dict[str, Any]],
        ttl_hours: int = 24
    ) -> bool:
        """
        缓存ScraperAPI搜索结果

        Args:
            keyword: 关键词
            results: 搜索结果列表
            ttl_hours: 缓存有效期（小时）

        Returns:
            是否成功
        """
        return self.cache.set(DataSource.SCRAPER_SEARCH, keyword, results, ttl_hours)

    def get_search_results(self, keyword: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取ScraperAPI搜索结果缓存

        Args:
            keyword: 关键词

        Returns:
            搜索结果列表
        """
        return self.cache.get(DataSource.SCRAPER_SEARCH, keyword)

    def has_search_results(self, keyword: str) -> bool:
        """
        检查是否有搜索结果缓存

        Args:
            keyword: 关键词

        Returns:
            是否存在
        """
        return self.cache.exists(DataSource.SCRAPER_SEARCH, keyword)

    # ==================== 产品详情（按ASIN） ====================

    def cache_product(
        self,
        asin: str,
        data: Dict[str, Any],
        source: DataSource = DataSource.SCRAPER_PRODUCT,
        ttl_hours: int = 24
    ) -> bool:
        """
        缓存产品详情

        Args:
            asin: 产品ASIN
            data: 产品数据
            source: 数据源（SCRAPER_PRODUCT 或 APIFY_API）
            ttl_hours: 缓存有效期（小时）

        Returns:
            是否成功
        """
        return self.cache.set(source, asin, data, ttl_hours)

    def get_product(
        self,
        asin: str,
        source: DataSource = DataSource.SCRAPER_PRODUCT
    ) -> Optional[Dict[str, Any]]:
        """
        获取产品详情缓存

        Args:
            asin: 产品ASIN
            source: 数据源

        Returns:
            产品数据
        """
        return self.cache.get(source, asin)

    def has_product(
        self,
        asin: str,
        source: DataSource = DataSource.SCRAPER_PRODUCT
    ) -> bool:
        """
        检查是否有产品缓存

        Args:
            asin: 产品ASIN
            source: 数据源

        Returns:
            是否存在
        """
        return self.cache.exists(source, asin)

    # ==================== 批量操作 ====================

    def cache_products_batch(
        self,
        products: Dict[str, Dict[str, Any]],
        source: DataSource = DataSource.SCRAPER_PRODUCT,
        ttl_hours: int = 24
    ) -> int:
        """
        批量缓存产品详情

        Args:
            products: {asin: data} 字典
            source: 数据源
            ttl_hours: 缓存有效期（小时）

        Returns:
            成功缓存的数量
        """
        return self.cache.set_batch(source, products, ttl_hours)

    def get_products_batch(
        self,
        asins: List[str],
        source: DataSource = DataSource.SCRAPER_PRODUCT
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取产品缓存

        Args:
            asins: ASIN列表
            source: 数据源

        Returns:
            {asin: data} 字典
        """
        return self.cache.get_batch(source, asins)

    def get_missing_asins(
        self,
        asins: List[str],
        source: DataSource = DataSource.SCRAPER_PRODUCT
    ) -> List[str]:
        """
        获取缺失的ASIN（未缓存或已过期）

        Args:
            asins: 要检查的ASIN列表
            source: 数据源

        Returns:
            缺失的ASIN列表
        """
        return self.cache.get_missing_keys(source, asins)

    # ==================== 通用方法 ====================

    def get(
        self,
        source: DataSource,
        key: str
    ) -> Optional[Any]:
        """
        通用获取方法

        Args:
            source: 数据源
            key: 键值

        Returns:
            缓存数据
        """
        return self.cache.get(source, key)

    def set(
        self,
        source: DataSource,
        key: str,
        data: Any,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        通用设置方法

        Args:
            source: 数据源
            key: 键值
            data: 数据
            ttl_hours: 缓存有效期

        Returns:
            是否成功
        """
        return self.cache.set(source, key, data, ttl_hours)

    def exists(self, source: DataSource, key: str) -> bool:
        """
        通用存在性检查

        Args:
            source: 数据源
            key: 键值

        Returns:
            是否存在
        """
        return self.cache.exists(source, key)

    def delete(self, source: DataSource, key: str) -> bool:
        """
        删除缓存

        Args:
            source: 数据源
            key: 键值

        Returns:
            是否成功
        """
        return self.cache.delete(source, key)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息
        """
        return self.cache.get_stats()

    def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的条目数
        """
        return self.cache.cleanup_expired()


# 全局适配器实例
_adapter_instance: Optional[CacheAdapter] = None


def get_cache_adapter() -> CacheAdapter:
    """
    获取全局缓存适配器实例

    Returns:
        CacheAdapter实例
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = CacheAdapter()
    return _adapter_instance
