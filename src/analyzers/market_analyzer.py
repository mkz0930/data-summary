"""
市场分析器模块
分析市场规模、竞争强度、市场集中度等指标
"""

from typing import List, Dict, Any, Optional
from collections import Counter

from src.database.models import Product, SellerSpiritData
from src.utils.logger import get_logger


class MarketAnalyzer:
    """市场分析器"""

    def __init__(self):
        """初始化市场分析器"""
        self.logger = get_logger()

    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        综合市场分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场分析结果
        """
        self.logger.info(f"开始市场分析，产品数量: {len(products)}")

        result = {
            'market_size': self._analyze_market_size(products, sellerspirit_data),
            'competition': self._analyze_competition(products),
            'brand_concentration': self._analyze_brand_concentration(products),
            'market_blank_index': self._calculate_market_blank_index(products, sellerspirit_data)
        }

        self.logger.info("市场分析完成")
        return result

    def _analyze_market_size(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        分析市场规模

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场规模分析结果
        """
        total_asins = len(products)

        # 计算总销量
        total_sales = sum(p.sales_volume for p in products if p.sales_volume)
        avg_sales = total_sales / total_asins if total_asins > 0 else 0

        # 月搜索量
        monthly_searches = sellerspirit_data.monthly_searches if sellerspirit_data else None

        # 市场规模评级
        if monthly_searches:
            if monthly_searches > 100000:
                size_rating = "大型市场"
            elif monthly_searches > 50000:
                size_rating = "中型市场"
            elif monthly_searches > 10000:
                size_rating = "小型市场"
            else:
                size_rating = "利基市场"
        else:
            size_rating = "未知"

        return {
            'total_asins': total_asins,
            'monthly_searches': monthly_searches,
            'total_sales': total_sales,
            'average_sales': round(avg_sales, 2),
            'size_rating': size_rating
        }

    def _analyze_competition(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析竞争强度

        Args:
            products: 产品列表

        Returns:
            竞争分析结果
        """
        if not products:
            return {
                'intensity': '未知',
                'average_reviews': 0,
                'average_rating': 0,
                'top10_avg_reviews': 0,
                'competition_score': 0
            }

        # 平均评论数（反映市场成熟度）
        products_with_reviews = [p for p in products if p.reviews_count]
        avg_reviews = (sum(p.reviews_count for p in products_with_reviews) /
                      len(products_with_reviews) if products_with_reviews else 0)

        # 平均评分
        products_with_rating = [p for p in products if p.rating]
        avg_rating = (sum(p.rating for p in products_with_rating) /
                     len(products_with_rating) if products_with_rating else 0)

        # Top 10产品的平均评论数
        sorted_products = sorted(products,
                                key=lambda p: p.reviews_count or 0,
                                reverse=True)
        top10 = sorted_products[:10]
        top10_avg_reviews = (sum(p.reviews_count for p in top10 if p.reviews_count) /
                            len([p for p in top10 if p.reviews_count])
                            if any(p.reviews_count for p in top10) else 0)

        # 竞争强度评分（0-100）
        competition_score = self._calculate_competition_score(
            avg_reviews, top10_avg_reviews, len(products)
        )

        # 竞争强度等级
        if competition_score >= 80:
            intensity = "极高"
        elif competition_score >= 60:
            intensity = "高"
        elif competition_score >= 40:
            intensity = "中等"
        elif competition_score >= 20:
            intensity = "低"
        else:
            intensity = "极低"

        return {
            'intensity': intensity,
            'average_reviews': round(avg_reviews, 2),
            'average_rating': round(avg_rating, 2),
            'top10_avg_reviews': round(top10_avg_reviews, 2),
            'competition_score': round(competition_score, 2)
        }

    def _calculate_competition_score(
        self,
        avg_reviews: float,
        top10_avg_reviews: float,
        total_products: int
    ) -> float:
        """
        计算竞争强度分数

        Args:
            avg_reviews: 平均评论数
            top10_avg_reviews: Top10平均评论数
            total_products: 总产品数

        Returns:
            竞争分数（0-100）
        """
        score = 0.0

        # 评论数维度（40分）
        if avg_reviews > 1000:
            score += 40
        elif avg_reviews > 500:
            score += 30
        elif avg_reviews > 100:
            score += 20
        else:
            score += 10

        # Top10评论数维度（30分）
        if top10_avg_reviews > 5000:
            score += 30
        elif top10_avg_reviews > 2000:
            score += 20
        elif top10_avg_reviews > 500:
            score += 10
        else:
            score += 5

        # 产品数量维度（30分）
        if total_products > 500:
            score += 30
        elif total_products > 200:
            score += 20
        elif total_products > 100:
            score += 10
        else:
            score += 5

        return min(100.0, score)

    def _analyze_brand_concentration(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析品牌集中度

        Args:
            products: 产品列表

        Returns:
            品牌集中度分析结果
        """
        if not products:
            return {
                'total_brands': 0,
                'top_brands': [],
                'cr4': 0,
                'cr10': 0,
                'concentration_level': '未知'
            }

        # 统计品牌
        brand_counter = Counter()
        for product in products:
            brand = product.brand or "Unknown"
            brand_counter[brand] += 1

        total_brands = len(brand_counter)
        total_products = len(products)

        # Top品牌
        top_brands = [
            {'brand': brand, 'count': count, 'share': round(count / total_products * 100, 2)}
            for brand, count in brand_counter.most_common(10)
        ]

        # CR4（前4名市场份额）
        cr4_count = sum(count for _, count in brand_counter.most_common(4))
        cr4 = round(cr4_count / total_products * 100, 2) if total_products > 0 else 0

        # CR10（前10名市场份额）
        cr10_count = sum(count for _, count in brand_counter.most_common(10))
        cr10 = round(cr10_count / total_products * 100, 2) if total_products > 0 else 0

        # 集中度等级
        if cr4 >= 60:
            concentration_level = "高度集中"
        elif cr4 >= 40:
            concentration_level = "中度集中"
        elif cr4 >= 20:
            concentration_level = "低度集中"
        else:
            concentration_level = "分散"

        return {
            'total_brands': total_brands,
            'top_brands': top_brands,
            'cr4': cr4,
            'cr10': cr10,
            'concentration_level': concentration_level
        }

    def _calculate_market_blank_index(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> float:
        """
        计算市场空白指数

        公式: 月搜索量 / 竞品数量
        >100为高机会，50-100为中等机会，<50为低机会

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场空白指数
        """
        if not sellerspirit_data or not sellerspirit_data.monthly_searches:
            return 0.0

        total_products = len(products)
        if total_products == 0:
            return 0.0

        index = sellerspirit_data.monthly_searches / total_products
        return round(index, 2)

    def get_market_opportunity_level(
        self,
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        评估市场机会等级

        Args:
            analysis_result: 市场分析结果

        Returns:
            机会等级（高/中/低）
        """
        blank_index = analysis_result.get('market_blank_index', 0)
        competition_score = analysis_result.get('competition', {}).get('competition_score', 0)
        cr4 = analysis_result.get('brand_concentration', {}).get('cr4', 0)

        # 综合评分
        opportunity_score = 0

        # 市场空白指数（40分）
        if blank_index > 100:
            opportunity_score += 40
        elif blank_index > 50:
            opportunity_score += 25
        elif blank_index > 20:
            opportunity_score += 10

        # 竞争强度（30分，竞争越低分数越高）
        opportunity_score += (100 - competition_score) * 0.3

        # 品牌集中度（30分，集中度越低分数越高）
        if cr4 < 30:
            opportunity_score += 30
        elif cr4 < 50:
            opportunity_score += 20
        elif cr4 < 70:
            opportunity_score += 10

        # 评级
        if opportunity_score >= 70:
            return "高机会"
        elif opportunity_score >= 40:
            return "中等机会"
        else:
            return "低机会"

    def get_market_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成市场分析摘要

        Args:
            analysis_result: 市场分析结果

        Returns:
            摘要文本
        """
        market_size = analysis_result.get('market_size', {})
        competition = analysis_result.get('competition', {})
        brand_conc = analysis_result.get('brand_concentration', {})
        blank_index = analysis_result.get('market_blank_index', 0)
        opportunity = self.get_market_opportunity_level(analysis_result)

        summary = f"""
市场分析摘要
{'=' * 50}

市场规模:
- 总ASIN数: {market_size.get('total_asins', 0)}
- 月搜索量: {market_size.get('monthly_searches', '未知')}
- 市场类型: {market_size.get('size_rating', '未知')}

竞争强度:
- 竞争等级: {competition.get('intensity', '未知')}
- 平均评论数: {competition.get('average_reviews', 0)}
- 平均评分: {competition.get('average_rating', 0)}
- Top10平均评论数: {competition.get('top10_avg_reviews', 0)}

品牌集中度:
- 总品牌数: {brand_conc.get('total_brands', 0)}
- CR4: {brand_conc.get('cr4', 0)}%
- CR10: {brand_conc.get('cr10', 0)}%
- 集中度: {brand_conc.get('concentration_level', '未知')}

市场机会:
- 市场空白指数: {blank_index}
- 机会等级: {opportunity}
"""

        return summary
