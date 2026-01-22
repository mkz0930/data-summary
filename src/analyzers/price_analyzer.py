"""
价格分析器模块
分析价格分布、价格带、定价策略等
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict

from src.database.models import Product
from src.utils.logger import get_logger


class PriceAnalyzer:
    """价格分析器"""

    def __init__(self, price_ranges: List[float] = None, main_band_threshold: float = 0.3):
        """
        初始化价格分析器

        Args:
            price_ranges: 价格区间边界列表，如 [0, 20, 50, 100, 999999]
            main_band_threshold: 主流价格带阈值（占比）
        """
        self.logger = get_logger()
        self.price_ranges = price_ranges or [0, 20, 50, 100, 999999]
        self.main_band_threshold = main_band_threshold

    def analyze(self, products: List[Product]) -> Dict[str, Any]:
        """
        综合价格分析

        Args:
            products: 产品列表

        Returns:
            价格分析结果
        """
        self.logger.info(f"开始价格分析，产品数量: {len(products)}")

        result = {
            'distribution': self._analyze_distribution(products),
            'statistics': self._calculate_statistics(products),
            'price_bands': self._analyze_price_bands(products),
            'price_rating_correlation': self._analyze_price_rating_correlation(products),
            'top_products_pricing': self._analyze_top_products_pricing(products)
        }

        self.logger.info("价格分析完成")
        return result

    def _analyze_distribution(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析价格分布

        Args:
            products: 产品列表

        Returns:
            价格分布结果
        """
        # 统计各价格区间的产品数量
        band_counts = defaultdict(int)
        total_with_price = 0

        for product in products:
            if not product.price or product.price <= 0:
                continue

            total_with_price += 1
            band = self._get_price_band(product.price)
            band_counts[band] += 1

        # 计算占比
        distribution = []
        for i in range(len(self.price_ranges) - 1):
            band_name = self._format_price_band(i)
            count = band_counts.get(band_name, 0)
            percentage = (count / total_with_price * 100) if total_with_price > 0 else 0

            distribution.append({
                'band': band_name,
                'count': count,
                'percentage': round(percentage, 2)
            })

        return {
            'total_products': total_with_price,
            'bands': distribution
        }

    def _calculate_statistics(self, products: List[Product]) -> Dict[str, float]:
        """
        计算价格统计指标

        Args:
            products: 产品列表

        Returns:
            统计指标
        """
        prices = [p.price for p in products if p.price and p.price > 0]

        if not prices:
            return {
                'min': 0,
                'max': 0,
                'mean': 0,
                'median': 0,
                'std_dev': 0
            }

        prices.sort()
        n = len(prices)

        # 基本统计
        min_price = prices[0]
        max_price = prices[-1]
        mean_price = sum(prices) / n

        # 中位数
        if n % 2 == 0:
            median_price = (prices[n//2 - 1] + prices[n//2]) / 2
        else:
            median_price = prices[n//2]

        # 标准差
        variance = sum((p - mean_price) ** 2 for p in prices) / n
        std_dev = variance ** 0.5

        return {
            'min': round(min_price, 2),
            'max': round(max_price, 2),
            'mean': round(mean_price, 2),
            'median': round(median_price, 2),
            'std_dev': round(std_dev, 2)
        }

    def _analyze_price_bands(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析价格带

        Args:
            products: 产品列表

        Returns:
            价格带分析结果
        """
        distribution = self._analyze_distribution(products)
        bands = distribution['bands']

        # 找出主流价格带（占比 > threshold）
        main_bands = [b for b in bands if b['percentage'] >= self.main_band_threshold * 100]

        # 找出最大占比的价格带
        dominant_band = max(bands, key=lambda b: b['percentage']) if bands else None

        return {
            'main_bands': main_bands,
            'dominant_band': dominant_band,
            'band_count': len([b for b in bands if b['count'] > 0])
        }

    def _analyze_price_rating_correlation(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析价格与评分的相关性

        Args:
            products: 产品列表

        Returns:
            相关性分析结果
        """
        # 筛选有价格和评分的产品
        valid_products = [p for p in products
                         if p.price and p.price > 0 and p.rating]

        if len(valid_products) < 2:
            return {
                'correlation': 0,
                'interpretation': '数据不足'
            }

        # 计算皮尔逊相关系数
        prices = [p.price for p in valid_products]
        ratings = [p.rating for p in valid_products]

        n = len(prices)
        mean_price = sum(prices) / n
        mean_rating = sum(ratings) / n

        numerator = sum((prices[i] - mean_price) * (ratings[i] - mean_rating)
                       for i in range(n))
        denominator_price = sum((p - mean_price) ** 2 for p in prices) ** 0.5
        denominator_rating = sum((r - mean_rating) ** 2 for r in ratings) ** 0.5

        if denominator_price == 0 or denominator_rating == 0:
            correlation = 0
        else:
            correlation = numerator / (denominator_price * denominator_rating)

        # 解释相关性
        if abs(correlation) < 0.3:
            interpretation = "弱相关"
        elif abs(correlation) < 0.7:
            interpretation = "中等相关"
        else:
            interpretation = "强相关"

        if correlation > 0:
            interpretation += "（正相关）"
        elif correlation < 0:
            interpretation += "（负相关）"

        return {
            'correlation': round(correlation, 3),
            'interpretation': interpretation,
            'sample_size': n
        }

    def _analyze_top_products_pricing(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析Top产品的定价策略

        Args:
            products: 产品列表

        Returns:
            Top产品定价分析
        """
        # 按评论数排序，取Top 10
        sorted_products = sorted(
            [p for p in products if p.reviews_count],
            key=lambda p: p.reviews_count,
            reverse=True
        )[:10]

        if not sorted_products:
            return {
                'top10_avg_price': 0,
                'top10_price_range': {'min': 0, 'max': 0},
                'top10_products': []
            }

        # 计算Top 10的价格统计
        top10_prices = [p.price for p in sorted_products if p.price and p.price > 0]

        avg_price = sum(top10_prices) / len(top10_prices) if top10_prices else 0
        min_price = min(top10_prices) if top10_prices else 0
        max_price = max(top10_prices) if top10_prices else 0

        # 产品详情
        top10_details = [
            {
                'asin': p.asin,
                'name': p.name[:50] + '...' if len(p.name) > 50 else p.name,
                'price': p.price,
                'rating': p.rating,
                'reviews': p.reviews_count
            }
            for p in sorted_products
        ]

        return {
            'top10_avg_price': round(avg_price, 2),
            'top10_price_range': {
                'min': round(min_price, 2),
                'max': round(max_price, 2)
            },
            'top10_products': top10_details
        }

    def _get_price_band(self, price: float) -> str:
        """
        获取价格所属的价格带

        Args:
            price: 价格

        Returns:
            价格带名称
        """
        for i in range(len(self.price_ranges) - 1):
            if self.price_ranges[i] <= price < self.price_ranges[i + 1]:
                return self._format_price_band(i)

        # 如果超出最大范围
        return self._format_price_band(len(self.price_ranges) - 2)

    def _format_price_band(self, index: int) -> str:
        """
        格式化价格带名称

        Args:
            index: 价格区间索引

        Returns:
            格式化的价格带名称
        """
        if index >= len(self.price_ranges) - 1:
            return f"${self.price_ranges[-2]}+"

        lower = self.price_ranges[index]
        upper = self.price_ranges[index + 1]

        if upper >= 999999:
            return f"${lower}+"
        else:
            return f"${lower}-${upper}"

    def get_recommended_price_band(self, analysis_result: Dict[str, Any]) -> str:
        """
        推荐切入价格带

        Args:
            analysis_result: 价格分析结果

        Returns:
            推荐的价格带
        """
        price_bands = analysis_result.get('price_bands', {})
        dominant_band = price_bands.get('dominant_band')

        if dominant_band:
            return dominant_band['band']
        else:
            return "未知"

    def get_price_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成价格分析摘要

        Args:
            analysis_result: 价格分析结果

        Returns:
            摘要文本
        """
        stats = analysis_result.get('statistics', {})
        distribution = analysis_result.get('distribution', {})
        price_bands = analysis_result.get('price_bands', {})
        correlation = analysis_result.get('price_rating_correlation', {})
        top_pricing = analysis_result.get('top_products_pricing', {})

        summary = f"""
价格分析摘要
{'=' * 50}

价格统计:
- 最低价: ${stats.get('min', 0)}
- 最高价: ${stats.get('max', 0)}
- 平均价: ${stats.get('mean', 0)}
- 中位数: ${stats.get('median', 0)}
- 标准差: ${stats.get('std_dev', 0)}

价格分布:
"""
        for band in distribution.get('bands', []):
            summary += f"- {band['band']}: {band['count']} 个产品 ({band['percentage']}%)\n"

        dominant = price_bands.get('dominant_band')
        if dominant:
            summary += f"\n主流价格带: {dominant['band']} ({dominant['percentage']}%)\n"

        summary += f"""
价格与评分相关性:
- 相关系数: {correlation.get('correlation', 0)}
- 解释: {correlation.get('interpretation', '未知')}

Top 10产品定价:
- 平均价格: ${top_pricing.get('top10_avg_price', 0)}
- 价格区间: ${top_pricing.get('top10_price_range', {}).get('min', 0)} - ${top_pricing.get('top10_price_range', {}).get('max', 0)}
"""

        return summary
