"""
生命周期分析器模块
识别新品机会，分析产品生命周期趋势
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from src.database.models import Product
from src.utils.logger import get_logger


class LifecycleAnalyzer:
    """生命周期分析器"""

    def __init__(
        self,
        new_product_days: int = 180,
        new_product_min_reviews: int = 50,
        new_product_max_bsr: int = 10000
    ):
        """
        初始化生命周期分析器

        Args:
            new_product_days: 新品定义天数阈值
            new_product_min_reviews: 新品最小评论数（证明有销量）
            new_product_max_bsr: 新品最大BSR排名
        """
        self.logger = get_logger()
        self.new_product_days = new_product_days
        self.new_product_min_reviews = new_product_min_reviews
        self.new_product_max_bsr = new_product_max_bsr

    def analyze(self, products: List[Product]) -> Dict[str, Any]:
        """
        综合生命周期分析

        Args:
            products: 产品列表

        Returns:
            生命周期分析结果
        """
        self.logger.info(f"开始生命周期分析，产品数量: {len(products)}")

        # 识别新品
        new_products = self.identify_new_products(products)

        # 分析新品趋势
        trend = self._analyze_new_product_trend(new_products)

        # 分析新品特征
        characteristics = self._analyze_new_product_characteristics(new_products)

        # 对比新品与老品
        comparison = self._compare_new_vs_old(products, new_products)

        result = {
            'new_products': [p.to_dict() for p in new_products],
            'new_product_count': len(new_products),
            'trend': trend,
            'characteristics': characteristics,
            'comparison': comparison
        }

        self.logger.info(f"生命周期分析完成，发现 {len(new_products)} 个新品机会")
        return result

    def identify_new_products(self, products: List[Product]) -> List[Product]:
        """
        识别新品机会

        定义：上架时间 < new_product_days 且 评论数 > new_product_min_reviews
              且 BSR排名 < new_product_max_bsr

        Args:
            products: 产品列表

        Returns:
            新品列表
        """
        new_products = []
        cutoff_date = datetime.now() - timedelta(days=self.new_product_days)

        for product in products:
            if not product.available_date:
                continue

            try:
                # 解析上架时间
                available_date = datetime.fromisoformat(
                    product.available_date.replace('Z', '+00:00')
                )

                # 检查是否符合新品条件
                is_new = available_date >= cutoff_date
                has_sales = (product.reviews_count or 0) >= self.new_product_min_reviews
                good_rank = (product.bsr_rank or float('inf')) <= self.new_product_max_bsr

                if is_new and has_sales and good_rank:
                    new_products.append(product)

            except Exception as e:
                self.logger.warning(f"解析上架时间失败 {product.asin}: {e}")
                continue

        # 按评论数排序
        new_products.sort(key=lambda p: p.reviews_count or 0, reverse=True)

        return new_products

    def _analyze_new_product_trend(self, new_products: List[Product]) -> Dict[str, Any]:
        """
        分析新品趋势

        Args:
            new_products: 新品列表

        Returns:
            趋势分析结果
        """
        if not new_products:
            return {
                'monthly_counts': {},
                'trend_direction': '无数据',
                'growth_rate': 0
            }

        # 按月统计新品数量
        monthly_counts = defaultdict(int)

        for product in new_products:
            try:
                available_date = datetime.fromisoformat(
                    product.available_date.replace('Z', '+00:00')
                )
                month_key = available_date.strftime('%Y-%m')
                monthly_counts[month_key] += 1
            except:
                continue

        # 排序
        sorted_months = sorted(monthly_counts.items())

        # 计算趋势
        if len(sorted_months) >= 2:
            first_half = sum(count for _, count in sorted_months[:len(sorted_months)//2])
            second_half = sum(count for _, count in sorted_months[len(sorted_months)//2:])

            if second_half > first_half * 1.2:
                trend_direction = "上升"
            elif second_half < first_half * 0.8:
                trend_direction = "下降"
            else:
                trend_direction = "平稳"

            growth_rate = ((second_half - first_half) / first_half * 100
                          if first_half > 0 else 0)
        else:
            trend_direction = "数据不足"
            growth_rate = 0

        return {
            'monthly_counts': dict(sorted_months),
            'trend_direction': trend_direction,
            'growth_rate': round(growth_rate, 2)
        }

    def _analyze_new_product_characteristics(
        self,
        new_products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析新品特征

        Args:
            new_products: 新品列表

        Returns:
            特征分析结果
        """
        if not new_products:
            return {
                'average_price': 0,
                'average_rating': 0,
                'average_reviews': 0,
                'price_range': {'min': 0, 'max': 0},
                'common_features': []
            }

        # 价格统计
        prices = [p.price for p in new_products if p.price]
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        # 评分统计
        ratings = [p.rating for p in new_products if p.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        # 评论数统计
        reviews = [p.reviews_count for p in new_products if p.reviews_count]
        avg_reviews = sum(reviews) / len(reviews) if reviews else 0

        # 提取常见特性关键词（简化版）
        common_features = self._extract_common_features(new_products)

        return {
            'average_price': round(avg_price, 2),
            'average_rating': round(avg_rating, 2),
            'average_reviews': round(avg_reviews, 2),
            'price_range': {
                'min': round(min_price, 2),
                'max': round(max_price, 2)
            },
            'common_features': common_features
        }

    def _extract_common_features(self, products: List[Product]) -> List[str]:
        """
        提取常见特性关键词

        Args:
            products: 产品列表

        Returns:
            常见特性列表
        """
        # 简化版：从产品名称中提取常见词汇
        word_counter = defaultdict(int)

        for product in products:
            if not product.name:
                continue

            # 简单分词（按空格和常见分隔符）
            words = product.name.lower().replace(',', ' ').replace('-', ' ').split()

            # 过滤停用词和短词
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                         'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is'}

            for word in words:
                if len(word) > 3 and word not in stop_words:
                    word_counter[word] += 1

        # 返回Top 10高频词
        common_features = [word for word, _ in
                          sorted(word_counter.items(), key=lambda x: x[1], reverse=True)[:10]]

        return common_features

    def _compare_new_vs_old(
        self,
        all_products: List[Product],
        new_products: List[Product]
    ) -> Dict[str, Any]:
        """
        对比新品与老品

        Args:
            all_products: 所有产品列表
            new_products: 新品列表

        Returns:
            对比结果
        """
        new_asins = {p.asin for p in new_products}
        old_products = [p for p in all_products if p.asin not in new_asins]

        if not old_products:
            return {
                'new_count': len(new_products),
                'old_count': 0,
                'comparison': {}
            }

        # 计算新品指标
        new_avg_price = (sum(p.price for p in new_products if p.price) /
                        len([p for p in new_products if p.price])
                        if any(p.price for p in new_products) else 0)

        new_avg_rating = (sum(p.rating for p in new_products if p.rating) /
                         len([p for p in new_products if p.rating])
                         if any(p.rating for p in new_products) else 0)

        new_avg_reviews = (sum(p.reviews_count for p in new_products if p.reviews_count) /
                          len([p for p in new_products if p.reviews_count])
                          if any(p.reviews_count for p in new_products) else 0)

        # 计算老品指标
        old_avg_price = (sum(p.price for p in old_products if p.price) /
                        len([p for p in old_products if p.price])
                        if any(p.price for p in old_products) else 0)

        old_avg_rating = (sum(p.rating for p in old_products if p.rating) /
                         len([p for p in old_products if p.rating])
                         if any(p.rating for p in old_products) else 0)

        old_avg_reviews = (sum(p.reviews_count for p in old_products if p.reviews_count) /
                          len([p for p in old_products if p.reviews_count])
                          if any(p.reviews_count for p in old_products) else 0)

        return {
            'new_count': len(new_products),
            'old_count': len(old_products),
            'comparison': {
                'price': {
                    'new': round(new_avg_price, 2),
                    'old': round(old_avg_price, 2),
                    'difference': round(new_avg_price - old_avg_price, 2)
                },
                'rating': {
                    'new': round(new_avg_rating, 2),
                    'old': round(old_avg_rating, 2),
                    'difference': round(new_avg_rating - old_avg_rating, 2)
                },
                'reviews': {
                    'new': round(new_avg_reviews, 2),
                    'old': round(old_avg_reviews, 2),
                    'difference': round(new_avg_reviews - old_avg_reviews, 2)
                }
            }
        }

    def get_top_new_products(
        self,
        new_products: List[Product],
        limit: int = 100
    ) -> List[Product]:
        """
        获取Top新品列表

        Args:
            new_products: 新品列表
            limit: 返回数量限制

        Returns:
            Top新品列表
        """
        # 按评论数排序
        sorted_products = sorted(
            new_products,
            key=lambda p: p.reviews_count or 0,
            reverse=True
        )

        return sorted_products[:limit]

    def get_lifecycle_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成生命周期分析摘要

        Args:
            analysis_result: 生命周期分析结果

        Returns:
            摘要文本
        """
        new_count = analysis_result.get('new_product_count', 0)
        trend = analysis_result.get('trend', {})
        characteristics = analysis_result.get('characteristics', {})
        comparison = analysis_result.get('comparison', {})

        summary = f"""
生命周期分析摘要
{'=' * 50}

新品机会:
- 新品数量: {new_count}
- 趋势方向: {trend.get('trend_direction', '未知')}
- 增长率: {trend.get('growth_rate', 0)}%

新品特征:
- 平均价格: ${characteristics.get('average_price', 0)}
- 平均评分: {characteristics.get('average_rating', 0)}
- 平均评论数: {characteristics.get('average_reviews', 0)}
- 价格区间: ${characteristics.get('price_range', {}).get('min', 0)} - ${characteristics.get('price_range', {}).get('max', 0)}

新品 vs 老品:
- 新品数量: {comparison.get('new_count', 0)}
- 老品数量: {comparison.get('old_count', 0)}
- 价格差异: ${comparison.get('comparison', {}).get('price', {}).get('difference', 0)}
- 评分差异: {comparison.get('comparison', {}).get('rating', {}).get('difference', 0)}
"""

        return summary
