"""
价格采集器模块
用于补充和更新产品价格数据
使用 Apify API 抓取价格

缓存机制：
- 使用统一缓存管理器 (UnifiedDataCache) 存储产品详情
- 缓存键: asin
- 默认TTL: 24小时
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加external_apis路径到sys.path
external_apis_path = Path(__file__).parent.parent.parent / "external_apis"
sys.path.insert(0, str(external_apis_path))

from apify_scraper import ApifyAmazonScraper

from src.database.models import Product
from src.utils.logger import get_logger
from src.utils.retry import retry
from src.collectors.cache_adapter import CacheAdapter, get_cache_adapter, DataSource


class PriceCollector:
    """价格采集器（使用 Apify API）"""

    def __init__(
        self,
        api_token: str,
        max_concurrent: int = 25,
        rate_limit_delay: float = 0.1,
        cache_adapter: Optional[CacheAdapter] = None
    ):
        """
        初始化价格采集器

        Args:
            api_token: Apify API Token
            max_concurrent: 最大并发数
            rate_limit_delay: 速率限制延迟（秒）
            cache_adapter: 缓存适配器（可选，默认使用全局单例）
        """
        self.logger = get_logger()
        self.scraper = ApifyAmazonScraper(
            api_token=api_token,
            max_concurrent=max_concurrent,
            rate_limit_delay=rate_limit_delay
        )
        self.cache_adapter = cache_adapter or get_cache_adapter()

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def collect_prices(
        self,
        products: List[Product],
        country_code: str = 'us'
    ) -> List[Product]:
        """
        补充产品价格数据

        Args:
            products: 产品列表
            country_code: 国家代码

        Returns:
            更新后的产品列表
        """
        # 筛选出缺少价格的产品
        missing_price_products = [p for p in products if p.price is None]

        if not missing_price_products:
            self.logger.info("所有产品都有价格数据，无需补充")
            return products

        self.logger.info(f"发现 {len(missing_price_products)} 个产品缺少价格，开始补充...")

        # 提取ASIN列表
        asins = [p.asin for p in missing_price_products]

        # 1. 先从统一缓存获取已有数据
        cached_data = self.cache_adapter.get_products_batch(asins, source=DataSource.APIFY_API)
        cached_count = 0

        for asin, data in cached_data.items():
            if data and 'items' in data and data['items']:
                item = data['items'][0]
                price = self._parse_price(item.get('price'))
                if price is not None:
                    for product in products:
                        if product.asin == asin:
                            product.price = price
                            cached_count += 1
                            break

        if cached_count > 0:
            self.logger.info(f"✓ 从统一缓存获取了 {cached_count} 个产品的价格")

        # 2. 获取缺失的ASIN
        missing_asins = self.cache_adapter.get_missing_asins(asins, source=DataSource.APIFY_API)

        if not missing_asins:
            self.logger.info("所有产品价格已从缓存获取，无需网络请求")
            return products

        self.logger.info(f"需要从网络获取 {len(missing_asins)} 个产品的价格...")

        # 3. 使用 Apify 批量抓取产品详情
        try:
            results = self.scraper.scrape_products_by_asins(
                asins=missing_asins,
                country_code=country_code,
                use_cache=True,
                show_progress=True
            )

            # 更新价格并保存到统一缓存
            updated_count = 0
            for i, result in enumerate(results):
                if result and 'items' in result and result['items']:
                    item = result['items'][0]
                    asin = missing_asins[i]
                    price = self._parse_price(item.get('price'))

                    # 保存到统一缓存
                    self.cache_adapter.cache_product(asin, result, source=DataSource.APIFY_API)

                    # 找到对应的产品并更新价格
                    for product in products:
                        if product.asin == asin and price is not None:
                            product.price = price
                            updated_count += 1
                            break

            self.logger.info(f"价格补充完成: 成功更新 {updated_count + cached_count}/{len(missing_price_products)} 个产品")

        except Exception as e:
            self.logger.error(f"批量获取价格失败: {e}")

        return products

    def _parse_price(self, price: Any) -> Optional[float]:
        """
        解析价格

        Args:
            price: 价格（可能是字符串或数字）

        Returns:
            价格数值
        """
        if isinstance(price, (int, float)):
            return float(price)

        if isinstance(price, str):
            # 移除货币符号和逗号
            import re
            price_str = re.sub(r'[^\d.]', '', price)
            try:
                return float(price_str)
            except ValueError:
                return None

        return None

    def update_prices(
        self,
        products: List[Product],
        country_code: str = 'us'
    ) -> List[Product]:
        """
        更新所有产品的价格数据

        Args:
            products: 产品列表
            country_code: 国家代码

        Returns:
            更新后的产品列表
        """
        self.logger.info(f"开始更新 {len(products)} 个产品的价格...")

        # 提取ASIN列表
        asins = [p.asin for p in products]

        # 1. 先从统一缓存获取已有数据
        cached_data = self.cache_adapter.get_products_batch(asins, source=DataSource.APIFY_API)
        cached_count = 0

        for asin, data in cached_data.items():
            if data and 'items' in data and data['items']:
                item = data['items'][0]
                price = self._parse_price(item.get('price'))
                if price is not None:
                    for product in products:
                        if product.asin == asin:
                            product.price = price
                            cached_count += 1
                            break

        if cached_count > 0:
            self.logger.info(f"✓ 从统一缓存获取了 {cached_count} 个产品的价格")

        # 2. 获取缺失的ASIN
        missing_asins = self.cache_adapter.get_missing_asins(asins, source=DataSource.APIFY_API)

        if not missing_asins:
            self.logger.info("所有产品价格已从缓存获取，无需网络请求")
            return products

        self.logger.info(f"需要从网络获取 {len(missing_asins)} 个产品的价格...")

        # 3. 使用 Apify 批量抓取产品详情
        try:
            results = self.scraper.scrape_products_by_asins(
                asins=missing_asins,
                country_code=country_code,
                use_cache=True,
                show_progress=True
            )

            # 更新价格并保存到统一缓存
            updated_count = 0
            for i, result in enumerate(results):
                if result and 'items' in result and result['items']:
                    item = result['items'][0]
                    asin = missing_asins[i]
                    price = self._parse_price(item.get('price'))

                    # 保存到统一缓存
                    self.cache_adapter.cache_product(asin, result, source=DataSource.APIFY_API)

                    # 找到对应的产品并更新价格
                    for product in products:
                        if product.asin == asin and price is not None:
                            product.price = price
                            updated_count += 1
                            break

            self.logger.info(f"价格更新完成: 成功更新 {updated_count + cached_count}/{len(products)} 个产品")

        except Exception as e:
            self.logger.error(f"批量更新价格失败: {e}")

        return products

    def get_price_statistics(self, products: List[Product]) -> Dict[str, Any]:
        """
        获取价格统计信息

        Args:
            products: 产品列表

        Returns:
            统计信息字典
        """
        prices = [p.price for p in products if p.price is not None]

        if not prices:
            return {
                'total': len(products),
                'with_price': 0,
                'min': None,
                'max': None,
                'avg': None,
                'median': None
            }

        import statistics

        return {
            'total': len(products),
            'with_price': len(prices),
            'min': min(prices),
            'max': max(prices),
            'avg': statistics.mean(prices),
            'median': statistics.median(prices)
        }
