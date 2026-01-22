"""
ASIN采集器模块
复用ScraperAPI的amazon_scraper.py，提供数据清洗和转换功能
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加external_apis路径到sys.path
external_apis_path = Path(__file__).parent.parent.parent / "external_apis"
sys.path.insert(0, str(external_apis_path))

from amazon_scraper import AmazonScraper

from src.database.models import Product
from src.utils.logger import get_logger
from src.utils.retry import retry


class ASINCollector:
    """ASIN采集器"""

    def __init__(self, api_key: str, max_concurrent: int = 10):
        """
        初始化ASIN采集器

        Args:
            api_key: ScraperAPI密钥
            max_concurrent: 最大并发数
        """
        self.logger = get_logger()
        self.scraper = AmazonScraper(
            api_key=api_key,
            max_concurrent=max_concurrent,
            max_retries=5,
            request_timeout=30
        )

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def collect_asins(
        self,
        keyword: str,
        country_code: str = 'us',
        max_pages: int = 100,
        sales_threshold: int = 10,
        fetch_details: bool = False
    ) -> List[Product]:
        """
        采集关键词相关的ASIN列表

        Args:
            keyword: 搜索关键词
            country_code: 国家代码
            max_pages: 最大页数
            sales_threshold: 销量阈值（低于此值停止）
            fetch_details: 是否抓取产品详情

        Returns:
            产品对象列表
        """
        self.logger.info(f"开始采集关键词 '{keyword}' 的ASIN数据...")

        try:
            # 使用智能搜索功能
            result = self.scraper.search_keyword_with_smart_stop(
                keyword=keyword,
                country_code=country_code,
                max_pages=max_pages,
                sales_threshold=sales_threshold,
                fetch_product_details=fetch_details,
                show_progress=True
            )

            # 提取搜索结果
            search_results = result.get('search_results', [])
            product_details = result.get('product_details', [])

            self.logger.info(
                f"采集完成: 共 {result.get('pages_scraped', 0)} 页, "
                f"{result.get('total_asins', 0)} 个ASIN"
            )

            # 转换为Product对象
            products = self._convert_to_products(search_results, product_details)

            # 数据清洗
            products = self._clean_products(products)

            self.logger.info(f"数据清洗后: {len(products)} 个有效产品")

            return products

        except Exception as e:
            self.logger.error(f"采集ASIN失败: {e}")
            raise

    def _convert_to_products(
        self,
        search_results: List[Dict[str, Any]],
        product_details: Optional[List[Dict[str, Any]]] = None
    ) -> List[Product]:
        """
        将搜索结果和产品详情转换为Product对象

        Args:
            search_results: 搜索结果列表
            product_details: 产品详情列表（可选）

        Returns:
            产品对象列表
        """
        products = []

        # 创建ASIN到详情的映射
        details_map = {}
        if product_details:
            for detail in product_details:
                if detail and detail.get('asin'):
                    details_map[detail['asin']] = detail

        # 转换每个搜索结果
        for result in search_results:
            asin = result.get('asin')
            if not asin:
                continue

            # 获取对应的详情
            detail = details_map.get(asin, {})

            # 提取销量
            sales_volume = self._extract_sales_volume(result.get('purchase_history_message'))

            # 提取上架时间
            available_date = self._extract_available_date(detail)

            # 提取特性列表
            feature_bullets = self._extract_feature_bullets(detail)

            # 创建Product对象
            product = Product(
                asin=asin,
                name=result.get('name') or detail.get('name', ''),
                brand=result.get('brand') or detail.get('brand'),
                category=self._extract_category(result, detail),
                price=self._extract_price(result, detail),
                rating=self._extract_rating(result, detail),
                reviews_count=self._extract_reviews_count(result, detail),
                sales_volume=sales_volume,
                bsr_rank=self._extract_bsr_rank(detail),
                available_date=available_date,
                feature_bullets=feature_bullets,
                has_anomaly=False,
                created_at=datetime.now().isoformat()
            )

            products.append(product)

        return products

    def _extract_sales_volume(self, purchase_message: Optional[str]) -> Optional[int]:
        """
        从购买历史消息中提取销量

        Args:
            purchase_message: 购买历史消息，如 "2K+ bought in past month"

        Returns:
            销量数值
        """
        if not purchase_message:
            return None

        try:
            # 使用scraper的解析方法
            return self.scraper._parse_purchase_count(purchase_message)
        except Exception as e:
            self.logger.warning(f"解析销量失败: {e}")
            return None

    def _extract_available_date(self, detail: Dict[str, Any]) -> Optional[str]:
        """
        从产品详情中提取上架时间

        Args:
            detail: 产品详情

        Returns:
            上架时间字符串
        """
        if not detail:
            return None

        # 尝试从不同字段提取
        date_str = detail.get('first_available') or detail.get('available_date')

        if date_str:
            return date_str

        return None

    def _extract_feature_bullets(self, detail: Dict[str, Any]) -> Optional[str]:
        """
        从产品详情中提取特性列表

        Args:
            detail: 产品详情

        Returns:
            特性列表的JSON字符串
        """
        if not detail:
            return None

        import json

        # 提取feature_bullets
        features = detail.get('feature_bullets', [])
        if features:
            return json.dumps(features, ensure_ascii=False)

        return None

    def _extract_category(
        self,
        result: Dict[str, Any],
        detail: Dict[str, Any]
    ) -> Optional[str]:
        """
        提取产品类别

        Args:
            result: 搜索结果
            detail: 产品详情

        Returns:
            类别名称
        """
        # 优先从详情中获取
        if detail:
            categories = detail.get('categories', [])
            if categories and len(categories) > 0:
                # 返回最后一个类别（通常是最具体的）
                return categories[-1].get('name') if isinstance(categories[-1], dict) else str(categories[-1])

        # 从搜索结果获取
        return result.get('category')

    def _extract_price(
        self,
        result: Dict[str, Any],
        detail: Dict[str, Any]
    ) -> Optional[float]:
        """
        提取产品价格

        Args:
            result: 搜索结果
            detail: 产品详情

        Returns:
            价格
        """
        # 优先从详情获取
        if detail:
            price = detail.get('price')
            if price:
                return self._parse_price(price)

        # 从搜索结果获取
        price = result.get('price')
        if price:
            return self._parse_price(price)

        return None

    def _parse_price(self, price: Any) -> Optional[float]:
        """
        解析价格字符串

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

    def _extract_rating(
        self,
        result: Dict[str, Any],
        detail: Dict[str, Any]
    ) -> Optional[float]:
        """
        提取产品评分

        Args:
            result: 搜索结果
            detail: 产品详情

        Returns:
            评分
        """
        # 优先从详情获取
        if detail:
            rating = detail.get('rating')
            if rating:
                return self._parse_rating(rating)

        # 从搜索结果获取
        rating = result.get('rating')
        if rating:
            return self._parse_rating(rating)

        return None

    def _parse_rating(self, rating: Any) -> Optional[float]:
        """
        解析评分

        Args:
            rating: 评分（可能是字符串或数字）

        Returns:
            评分数值
        """
        if isinstance(rating, (int, float)):
            return float(rating)

        if isinstance(rating, str):
            # 提取数字部分
            import re
            match = re.search(r'(\d+\.?\d*)', rating)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    return None

        return None

    def _extract_reviews_count(
        self,
        result: Dict[str, Any],
        detail: Dict[str, Any]
    ) -> Optional[int]:
        """
        提取评论数量

        Args:
            result: 搜索结果
            detail: 产品详情

        Returns:
            评论数量
        """
        # 优先从详情获取
        if detail:
            count = detail.get('reviews_count') or detail.get('ratings_total')
            if count:
                return self._parse_count(count)

        # 从搜索结果获取
        count = result.get('reviews_count') or result.get('ratings_total')
        if count:
            return self._parse_count(count)

        return None

    def _parse_count(self, count: Any) -> Optional[int]:
        """
        解析数量字符串

        Args:
            count: 数量（可能是字符串或数字）

        Returns:
            数量数值
        """
        if isinstance(count, int):
            return count

        if isinstance(count, str):
            # 移除逗号
            count_str = count.replace(',', '')
            try:
                return int(count_str)
            except ValueError:
                return None

        return None

    def _extract_bsr_rank(self, detail: Dict[str, Any]) -> Optional[int]:
        """
        从产品详情中提取BSR排名

        Args:
            detail: 产品详情

        Returns:
            BSR排名
        """
        if not detail:
            return None

        # 尝试从不同字段提取
        bsr = detail.get('bestsellers_rank')
        if bsr:
            if isinstance(bsr, list) and len(bsr) > 0:
                # 取第一个排名
                first_rank = bsr[0]
                if isinstance(first_rank, dict):
                    rank = first_rank.get('rank')
                    if rank:
                        return self._parse_count(rank)

        return None

    def _clean_products(self, products: List[Product]) -> List[Product]:
        """
        清洗产品数据

        Args:
            products: 产品列表

        Returns:
            清洗后的产品列表
        """
        cleaned = []
        seen_asins = set()

        for product in products:
            # 去重
            if product.asin in seen_asins:
                self.logger.debug(f"跳过重复ASIN: {product.asin}")
                continue

            seen_asins.add(product.asin)

            # 标记异常数据
            if self._is_anomaly(product):
                product.has_anomaly = True
                self.logger.warning(f"产品 {product.asin} 存在异常数据")

            cleaned.append(product)

        return cleaned

    def _is_anomaly(self, product: Product) -> bool:
        """
        检查产品数据是否异常

        Args:
            product: 产品对象

        Returns:
            是否异常
        """
        # 检查必填字段
        if not product.name:
            return True

        # 检查价格异常
        if product.price is not None and product.price <= 0:
            return True

        # 检查评分异常
        if product.rating is not None and (product.rating < 0 or product.rating > 5):
            return True

        # 检查评论数异常
        if product.reviews_count is not None and product.reviews_count < 0:
            return True

        return False

    def get_statistics(self, products: List[Product]) -> Dict[str, Any]:
        """
        获取采集数据的统计信息

        Args:
            products: 产品列表

        Returns:
            统计信息字典
        """
        total = len(products)
        with_price = sum(1 for p in products if p.price is not None)
        with_rating = sum(1 for p in products if p.rating is not None)
        with_sales = sum(1 for p in products if p.sales_volume is not None)
        with_bsr = sum(1 for p in products if p.bsr_rank is not None)
        with_date = sum(1 for p in products if p.available_date is not None)
        anomalies = sum(1 for p in products if p.has_anomaly)

        return {
            'total': total,
            'with_price': with_price,
            'with_rating': with_rating,
            'with_sales': with_sales,
            'with_bsr': with_bsr,
            'with_available_date': with_date,
            'anomalies': anomalies,
            'completeness': {
                'price': f"{with_price/total*100:.1f}%" if total > 0 else "0%",
                'rating': f"{with_rating/total*100:.1f}%" if total > 0 else "0%",
                'sales': f"{with_sales/total*100:.1f}%" if total > 0 else "0%",
                'bsr': f"{with_bsr/total*100:.1f}%" if total > 0 else "0%",
                'available_date': f"{with_date/total*100:.1f}%" if total > 0 else "0%",
            }
        }
