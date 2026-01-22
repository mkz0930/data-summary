"""
价格采集器模块
用于补充和更新产品价格数据
"""

from typing import List, Dict, Any, Optional
from src.database.models import Product
from src.collectors.asin_collector import ASINCollector
from src.utils.logger import get_logger
from src.utils.retry import retry


class PriceCollector:
    """价格采集器"""

    def __init__(self, api_key: str):
        """
        初始化价格采集器

        Args:
            api_key: ScraperAPI密钥
        """
        self.logger = get_logger()
        self.asin_collector = ASINCollector(api_key=api_key, max_concurrent=5)

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

        # 批量抓取产品详情
        try:
            results = self.asin_collector.scraper.scrape_products_batch(
                asins=asins,
                country_code=country_code,
                show_progress=True
            )

            # 更新价格
            updated_count = 0
            for i, result in enumerate(results):
                if result and result.get('price'):
                    asin = asins[i]
                    price = self._parse_price(result.get('price'))

                    # 找到对应的产品并更新价格
                    for product in products:
                        if product.asin == asin:
                            product.price = price
                            updated_count += 1
                            break

            self.logger.info(f"价格补充完成: 成功更新 {updated_count}/{len(missing_price_products)} 个产品")

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

        # 批量抓取产品详情
        try:
            results = self.asin_collector.scraper.scrape_products_batch(
                asins=asins,
                country_code=country_code,
                show_progress=True
            )

            # 更新价格
            updated_count = 0
            for i, result in enumerate(results):
                if result and result.get('price'):
                    asin = asins[i]
                    price = self._parse_price(result.get('price'))

                    # 找到对应的产品并更新价格
                    for product in products:
                        if product.asin == asin and price is not None:
                            product.price = price
                            updated_count += 1
                            break

            self.logger.info(f"价格更新完成: 成功更新 {updated_count}/{len(products)} 个产品")

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
