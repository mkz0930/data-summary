"""
蓝海产品分析模块
识别和评估腰部蓝海产品机会
基于4大AI选品方法论优化
继承 BaseAnalyzer 基类
"""

from typing import List, Dict, Any, Optional
import statistics
import json

from src.database.models import Product, SellerSpiritData
from src.analyzers.base_analyzer import BaseAnalyzer


class BlueOceanAnalyzer(BaseAnalyzer):
    """
    蓝海产品分析器

    继承 BaseAnalyzer，提供蓝海产品识别、评分、细分市场分析等功能。
    """

    def __init__(
        self,
        competition_threshold: float = 50.0,
        min_sales_volume: int = 600,  # 日销20单 * 30天
        max_sales_volume: int = 1800,  # 日销60单 * 30天
        min_reviews: int = 20,
        max_reviews: int = 500,  # 对齐文档: 首页平均Review<500
        min_rating: float = 3.8,
        max_avg_reviews: int = 500,
        min_search_volume: int = 5000,  # 对齐文档: 月搜索量5000-12000
        max_search_volume: int = 50000,
        target_gross_margin: float = 0.35,  # 对齐文档: 毛利率≥35%
        max_cpc: float = 1.5,  # 对齐文档: CPC<$1.5
        min_weak_listings: int = 4  # 对齐文档: 前10名≥4个弱listing
    ):
        """
        初始化蓝海产品分析器

        Args:
            competition_threshold: 竞争指数阈值（低于此值认为是蓝海）
            min_sales_volume: 最小月销量（腰部产品下限）
            max_sales_volume: 最大月销量（腰部产品上限）
            min_reviews: 最小评论数
            max_reviews: 最大评论数（避免成熟市场）
            min_rating: 最小评分要求
            max_avg_reviews: 市场平均评论数上限
            min_search_volume: 最小月搜索量
            max_search_volume: 最大月搜索量
            target_gross_margin: 目标毛利率
            max_cpc: 最大CPC出价
            min_weak_listings: 最小弱listing数量
        """
        super().__init__(name="BlueOceanAnalyzer")
        self.competition_threshold = competition_threshold
        self.min_sales_volume = min_sales_volume
        self.max_sales_volume = max_sales_volume
        self.min_reviews = min_reviews
        self.max_reviews = max_reviews
        self.min_rating = min_rating
        self.max_avg_reviews = max_avg_reviews
        self.min_search_volume = min_search_volume
        self.max_search_volume = max_search_volume
        self.target_gross_margin = target_gross_margin
        self.max_cpc = max_cpc
        self.min_weak_listings = min_weak_listings

    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        执行蓝海产品分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            分析结果字典
        """
        if not products:
            return self._empty_result()

        self.log_info("开始蓝海产品分析...")

        # 1. 计算市场竞争指数
        market_competition = self._calculate_market_competition(products)

        # 2. 识别蓝海产品
        blue_ocean_products = self._identify_blue_ocean_products(
            products, market_competition
        )

        # 3. 对蓝海产品进行评分
        scored_products = self._score_blue_ocean_products(
            blue_ocean_products, market_competition, sellerspirit_data
        )

        # 4. 分析蓝海细分市场
        segments = self._analyze_blue_ocean_segments(scored_products)

        # 5. 生成市场机会评估
        opportunity_assessment = self._assess_market_opportunity(
            products, blue_ocean_products, market_competition, sellerspirit_data
        )

        return {
            'market_competition': market_competition,
            'blue_ocean_products': [p.to_dict() for p in scored_products],
            'blue_ocean_count': len(scored_products),
            'blue_ocean_rate': round(len(scored_products) / len(products) * 100, 2),
            'segments': segments,
            'opportunity_assessment': opportunity_assessment,
            'top_opportunities': self._get_top_opportunities(scored_products, top_n=10)
        }

    def _calculate_market_competition(self, products: List[Product]) -> Dict[str, Any]:
        """
        计算市场竞争指数

        竞争指数 = 评论密度 * 0.3 + 评分质量 * 0.25 + 品牌集中度 * 0.25 + 价格竞争度 * 0.2

        Args:
            products: 产品列表

        Returns:
            竞争指数数据
        """
        if not products:
            return {}

        # 1. 评论密度指数 (0-100)
        reviews_list = [p.reviews_count for p in products if p.reviews_count]
        avg_reviews = statistics.mean(reviews_list) if reviews_list else 0
        median_reviews = statistics.median(reviews_list) if reviews_list else 0

        # 评论数越多，竞争越激烈
        review_density_score = min(100, (avg_reviews / 10))  # 1000评论 = 100分

        # 2. 评分质量指数 (0-100)
        ratings_list = [p.rating for p in products if p.rating]
        avg_rating = statistics.mean(ratings_list) if ratings_list else 0
        high_rating_count = len([r for r in ratings_list if r >= 4.0])
        high_rating_rate = (high_rating_count / len(ratings_list) * 100) if ratings_list else 0

        # 高评分产品占比越高，竞争越激烈
        rating_quality_score = high_rating_rate

        # 3. 品牌集中度指数 (0-100)
        brands = [p.brand for p in products if p.brand]
        if brands:
            unique_brands = len(set(brands))
            brand_concentration = (1 - unique_brands / len(brands)) * 100
        else:
            brand_concentration = 0

        # 4. 价格竞争度指数 (0-100)
        prices = [p.price for p in products if p.price]
        if prices:
            price_std = statistics.stdev(prices) if len(prices) > 1 else 0
            avg_price = statistics.mean(prices)
            # 价格标准差越小（价格越集中），竞争越激烈
            price_competition_score = max(0, 100 - (price_std / avg_price * 100)) if avg_price > 0 else 50
        else:
            price_competition_score = 50

        # 计算综合竞争指数
        competition_index = (
            review_density_score * 0.3 +
            rating_quality_score * 0.25 +
            brand_concentration * 0.25 +
            price_competition_score * 0.2
        )

        return {
            'competition_index': round(competition_index, 2),
            'review_density_score': round(review_density_score, 2),
            'rating_quality_score': round(rating_quality_score, 2),
            'brand_concentration': round(brand_concentration, 2),
            'price_competition_score': round(price_competition_score, 2),
            'avg_reviews': round(avg_reviews, 2),
            'median_reviews': round(median_reviews, 2),
            'avg_rating': round(avg_rating, 2),
            'high_rating_rate': round(high_rating_rate, 2),
            'unique_brands': len(set(brands)) if brands else 0,
            'total_brands': len(brands) if brands else 0
        }

    def _identify_blue_ocean_products(
        self,
        products: List[Product],
        market_competition: Dict[str, Any]
    ) -> List[Product]:
        """
        识别蓝海产品

        蓝海产品特征：
        1. 腰部销量（中等销量）
        2. 评论数适中（不太成熟）
        3. 评分合格（有一定质量）
        4. 市场竞争度低

        Args:
            products: 产品列表
            market_competition: 市场竞争数据

        Returns:
            蓝海产品列表
        """
        blue_ocean_products = []
        avg_reviews = market_competition.get('avg_reviews', 0)

        for product in products:
            # 检查销量范围（腰部产品）
            if not (self.min_sales_volume <= (product.sales_volume or 0) <= self.max_sales_volume):
                continue

            # 检查评论数范围
            if not (self.min_reviews <= (product.reviews_count or 0) <= self.max_reviews):
                continue

            # 检查评分要求
            if not product.rating or product.rating < self.min_rating:
                continue

            # 检查市场成熟度（评论数不能太高）
            if avg_reviews > self.max_avg_reviews:
                # 市场较成熟，要求产品评论数更低
                if (product.reviews_count or 0) > avg_reviews * 0.5:
                    continue

            # 计算产品竞争指数
            product_competition = self._calculate_product_competition(product, market_competition)

            # 竞争指数低于阈值，认为是蓝海产品
            if product_competition < self.competition_threshold:
                blue_ocean_products.append(product)

        return blue_ocean_products

    def _calculate_product_competition(
        self,
        product: Product,
        market_competition: Dict[str, Any]
    ) -> float:
        """
        计算单个产品的竞争指数

        Args:
            product: 产品对象
            market_competition: 市场竞争数据

        Returns:
            产品竞争指数
        """
        avg_reviews = market_competition.get('avg_reviews', 1)
        avg_rating = market_competition.get('avg_rating', 4.0)

        # 1. 评论数相对指数
        review_ratio = (product.reviews_count or 0) / avg_reviews if avg_reviews > 0 else 0
        review_score = min(100, review_ratio * 100)

        # 2. 评分相对指数
        rating_diff = (product.rating or 0) - avg_rating
        rating_score = 50 + rating_diff * 20  # 评分差0.5 = 10分差异

        # 3. 综合竞争指数
        competition_index = (review_score * 0.6 + rating_score * 0.4)

        return round(competition_index, 2)

    def _score_blue_ocean_products(
        self,
        products: List[Product],
        market_competition: Dict[str, Any],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> List[Product]:
        """
        对蓝海产品进行评分

        评分维度：
        1. 市场需求 (30分) - 销量、搜索量
        2. 竞争强度 (30分) - 评论数、评分、品牌
        3. 进入门槛 (20分) - 价格、复杂度
        4. 利润空间 (20分) - 价格区间

        Args:
            products: 蓝海产品列表
            market_competition: 市场竞争数据
            sellerspirit_data: 卖家精灵数据

        Returns:
            评分后的产品列表
        """
        scored_products = []

        for product in products:
            # 1. 市场需求分数 (30分)
            demand_score = self._score_market_demand(product, sellerspirit_data)

            # 2. 竞争强度分数 (30分) - 竞争越低分数越高
            competition_score = self._score_competition_level(product, market_competition)

            # 3. 进入门槛分数 (20分) - 门槛越低分数越高
            barrier_score = self._score_entry_barrier(product)

            # 4. 利润空间分数 (20分)
            profit_score = self._score_profit_potential(product)

            # 计算总分
            total_score = demand_score + competition_score + barrier_score + profit_score

            # 将评分信息附加到产品对象
            product.blue_ocean_score = round(total_score, 2)
            product.demand_score = round(demand_score, 2)
            product.competition_score = round(competition_score, 2)
            product.barrier_score = round(barrier_score, 2)
            product.profit_score = round(profit_score, 2)

            scored_products.append(product)

        # 按总分排序
        scored_products.sort(key=lambda p: p.blue_ocean_score, reverse=True)

        return scored_products

    def _score_market_demand(
        self,
        product: Product,
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> float:
        """
        评分：市场需求 (30分)

        Args:
            product: 产品对象
            sellerspirit_data: 卖家精灵数据

        Returns:
            需求分数
        """
        score = 0.0

        # 销量分数 (20分)
        sales = product.sales_volume or 0
        if sales >= 300:
            score += 20.0
        elif sales >= 200:
            score += 18.0
        elif sales >= 100:
            score += 15.0
        elif sales >= 50:
            score += 12.0
        else:
            score += 8.0

        # 搜索量分数 (10分)
        if sellerspirit_data and sellerspirit_data.monthly_searches:
            searches = sellerspirit_data.monthly_searches
            if searches >= 50000:
                score += 10.0
            elif searches >= 20000:
                score += 8.0
            elif searches >= 10000:
                score += 6.0
            elif searches >= 5000:
                score += 4.0
            else:
                score += 2.0
        else:
            score += 5.0  # 无数据给中等分

        return score

    def _score_competition_level(
        self,
        product: Product,
        market_competition: Dict[str, Any]
    ) -> float:
        """
        评分：竞争强度 (30分) - 竞争越低分数越高

        Args:
            product: 产品对象
            market_competition: 市场竞争数据

        Returns:
            竞争分数
        """
        score = 30.0
        avg_reviews = market_competition.get('avg_reviews', 100)

        # 评论数相对分数 (15分)
        review_ratio = (product.reviews_count or 0) / avg_reviews if avg_reviews > 0 else 0
        if review_ratio < 0.3:
            score -= 0  # 很低，不扣分
        elif review_ratio < 0.5:
            score -= 3
        elif review_ratio < 0.8:
            score -= 6
        elif review_ratio < 1.0:
            score -= 9
        else:
            score -= 12

        # 评分相对分数 (15分)
        avg_rating = market_competition.get('avg_rating', 4.0)
        rating_diff = (product.rating or 0) - avg_rating
        if rating_diff >= 0.3:
            score -= 0  # 评分高，竞争力强，不扣分
        elif rating_diff >= 0:
            score -= 3
        elif rating_diff >= -0.3:
            score -= 6
        else:
            score -= 10

        return max(0, score)

    def _score_entry_barrier(self, product: Product) -> float:
        """
        评分：进入门槛 (20分) - 门槛越低分数越高

        Args:
            product: 产品对象

        Returns:
            门槛分数
        """
        score = 20.0
        price = product.price or 0

        # 价格门槛 (20分)
        if price < 15:
            score = 20.0  # 低价，门槛低
        elif price < 30:
            score = 18.0
        elif price < 50:
            score = 15.0
        elif price < 80:
            score = 12.0
        elif price < 100:
            score = 8.0
        else:
            score = 5.0  # 高价，门槛高

        return score

    def _score_profit_potential(self, product: Product) -> float:
        """
        评分：利润空间 (20分)

        Args:
            product: 产品对象

        Returns:
            利润分数
        """
        price = product.price or 0

        # 价格适中（$20-60）利润空间较好
        if 20 <= price <= 60:
            return 20.0
        elif 15 <= price < 20 or 60 < price <= 80:
            return 16.0
        elif 10 <= price < 15 or 80 < price <= 100:
            return 12.0
        elif price < 10:
            return 6.0  # 太低，利润空间小
        else:
            return 8.0  # 太高，可能门槛高

    def _analyze_blue_ocean_segments(
        self,
        products: List[Product]
    ) -> List[Dict[str, Any]]:
        """
        分析蓝海产品的细分市场

        Args:
            products: 蓝海产品列表

        Returns:
            细分市场列表
        """
        if not products:
            return []

        # 按价格区间分组
        price_segments = {
            'low': {'range': '$0-20', 'products': []},
            'medium_low': {'range': '$20-40', 'products': []},
            'medium': {'range': '$40-60', 'products': []},
            'medium_high': {'range': '$60-80', 'products': []},
            'high': {'range': '$80+', 'products': []}
        }

        for product in products:
            price = product.price or 0
            if price < 20:
                price_segments['low']['products'].append(product)
            elif price < 40:
                price_segments['medium_low']['products'].append(product)
            elif price < 60:
                price_segments['medium']['products'].append(product)
            elif price < 80:
                price_segments['medium_high']['products'].append(product)
            else:
                price_segments['high']['products'].append(product)

        # 生成细分市场报告
        segments = []
        for key, segment in price_segments.items():
            if segment['products']:
                avg_score = statistics.mean([p.blue_ocean_score for p in segment['products']])
                avg_sales = statistics.mean([p.sales_volume or 0 for p in segment['products']])

                segments.append({
                    'segment': key,
                    'price_range': segment['range'],
                    'product_count': len(segment['products']),
                    'avg_blue_ocean_score': round(avg_score, 2),
                    'avg_sales': round(avg_sales, 2),
                    'top_product': segment['products'][0].to_dict() if segment['products'] else None
                })

        # 按平均分数排序
        segments.sort(key=lambda s: s['avg_blue_ocean_score'], reverse=True)

        return segments

    def _assess_market_opportunity(
        self,
        all_products: List[Product],
        blue_ocean_products: List[Product],
        market_competition: Dict[str, Any],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        评估市场机会

        Args:
            all_products: 所有产品列表
            blue_ocean_products: 蓝海产品列表
            market_competition: 市场竞争数据
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场机会评估
        """
        blue_ocean_rate = len(blue_ocean_products) / len(all_products) * 100 if all_products else 0
        competition_index = market_competition.get('competition_index', 50)

        # 市场机会等级
        if blue_ocean_rate >= 30 and competition_index < 40:
            opportunity_level = 'excellent'
            opportunity_desc = '优秀 - 大量蓝海机会，竞争温和'
        elif blue_ocean_rate >= 20 and competition_index < 50:
            opportunity_level = 'good'
            opportunity_desc = '良好 - 较多蓝海机会，竞争适中'
        elif blue_ocean_rate >= 10 and competition_index < 60:
            opportunity_level = 'moderate'
            opportunity_desc = '中等 - 有一定蓝海机会，需精准定位'
        elif blue_ocean_rate >= 5:
            opportunity_level = 'limited'
            opportunity_desc = '有限 - 蓝海机会较少，竞争较激烈'
        else:
            opportunity_level = 'poor'
            opportunity_desc = '较差 - 蓝海机会稀缺，市场成熟'

        # 市场建议
        recommendations = self._generate_recommendations(
            blue_ocean_rate, competition_index, market_competition, sellerspirit_data
        )

        return {
            'opportunity_level': opportunity_level,
            'opportunity_desc': opportunity_desc,
            'blue_ocean_rate': round(blue_ocean_rate, 2),
            'competition_index': competition_index,
            'recommendations': recommendations
        }

    def _generate_recommendations(
        self,
        blue_ocean_rate: float,
        competition_index: float,
        market_competition: Dict[str, Any],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> List[str]:
        """
        生成市场建议

        Args:
            blue_ocean_rate: 蓝海产品占比
            competition_index: 竞争指数
            market_competition: 市场竞争数据
            sellerspirit_data: 卖家精灵数据

        Returns:
            建议列表
        """
        recommendations = []

        # 基于蓝海率的建议
        if blue_ocean_rate >= 20:
            recommendations.append("市场存在大量蓝海机会，建议积极进入")
        elif blue_ocean_rate >= 10:
            recommendations.append("市场有一定蓝海空间，建议精准定位细分市场")
        else:
            recommendations.append("蓝海机会较少，建议寻找差异化切入点")

        # 基于竞争指数的建议
        if competition_index < 40:
            recommendations.append("市场竞争温和，适合新卖家进入")
        elif competition_index < 60:
            recommendations.append("市场竞争适中，需要有竞争优势")
        else:
            recommendations.append("市场竞争激烈，建议避开头部竞品")

        # 基于品牌集中度的建议
        brand_concentration = market_competition.get('brand_concentration', 0)
        if brand_concentration < 30:
            recommendations.append("品牌分散，市场开放度高")
        elif brand_concentration < 50:
            recommendations.append("品牌集中度适中，有品牌建设机会")
        else:
            recommendations.append("品牌集中度高，建议打造差异化品牌")

        # 基于评论密度的建议
        avg_reviews = market_competition.get('avg_reviews', 0)
        if avg_reviews < 100:
            recommendations.append("市场较新，评论数少，适合早期进入")
        elif avg_reviews < 300:
            recommendations.append("市场处于成长期，仍有机会")
        else:
            recommendations.append("市场较成熟，需要强大的产品力")

        return recommendations

    def _get_top_opportunities(
        self,
        products: List[Product],
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取最佳蓝海机会

        Args:
            products: 蓝海产品列表
            top_n: 返回前N个

        Returns:
            最佳机会列表
        """
        top_products = products[:top_n]

        opportunities = []
        for i, product in enumerate(top_products, 1):
            opportunities.append({
                'rank': i,
                'asin': product.asin,
                'name': product.name,
                'price': product.price,
                'sales_volume': product.sales_volume,
                'reviews_count': product.reviews_count,
                'rating': product.rating,
                'blue_ocean_score': product.blue_ocean_score,
                'demand_score': product.demand_score,
                'competition_score': product.competition_score,
                'barrier_score': product.barrier_score,
                'profit_score': product.profit_score
            })

        return opportunities

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'market_competition': {},
            'blue_ocean_products': [],
            'blue_ocean_count': 0,
            'blue_ocean_rate': 0,
            'segments': [],
            'opportunity_assessment': {
                'opportunity_level': 'unknown',
                'opportunity_desc': '无数据',
                'blue_ocean_rate': 0,
                'competition_index': 0,
                'recommendations': []
            },
            'top_opportunities': [],
            'weak_listing_analysis': {},
            'profit_analysis': {},
            'advertising_analysis': {}
        }

    def calculate_listing_quality_score(self, product: Product) -> float:
        """
        计算Listing质量分数 (0-100)

        评分维度:
        - 标题质量 (25分): 长度、关键词密度
        - 图片数量 (25分): 主图+副图
        - 评分评论 (25分): 评分高低、评论数量
        - 价格竞争力 (25分): 相对市场价格

        Args:
            product: 产品对象

        Returns:
            Listing质量分数
        """
        score = 0.0

        # 1. 标题质量 (25分)
        title_score = 0.0
        if product.name:
            title_len = len(product.name)
            if 80 <= title_len <= 200:
                title_score = 25.0
            elif 50 <= title_len < 80:
                title_score = 20.0
            elif title_len > 200:
                title_score = 15.0
            else:
                title_score = 10.0
        score += title_score

        # 2. Feature Bullets质量 (25分)
        bullets_score = 0.0
        if product.feature_bullets:
            try:
                bullets = json.loads(product.feature_bullets) if isinstance(product.feature_bullets, str) else product.feature_bullets
                bullet_count = len(bullets) if isinstance(bullets, list) else 0
                if bullet_count >= 5:
                    bullets_score = 25.0
                elif bullet_count >= 3:
                    bullets_score = 18.0
                elif bullet_count >= 1:
                    bullets_score = 10.0
            except (json.JSONDecodeError, TypeError):
                bullets_score = 12.0  # 有内容但格式不明
        score += bullets_score

        # 3. 评分评论 (25分)
        rating_review_score = 0.0
        if product.rating:
            if product.rating >= 4.5:
                rating_review_score += 15.0
            elif product.rating >= 4.0:
                rating_review_score += 12.0
            elif product.rating >= 3.5:
                rating_review_score += 8.0
            else:
                rating_review_score += 4.0

        if product.reviews_count:
            if product.reviews_count >= 100:
                rating_review_score += 10.0
            elif product.reviews_count >= 50:
                rating_review_score += 8.0
            elif product.reviews_count >= 20:
                rating_review_score += 5.0
            else:
                rating_review_score += 2.0
        score += rating_review_score

        # 4. 价格合理性 (25分) - 基于价格区间
        price_score = 0.0
        if product.price:
            if 15 <= product.price <= 50:
                price_score = 25.0  # 最佳价格区间
            elif 10 <= product.price < 15 or 50 < product.price <= 80:
                price_score = 20.0
            elif product.price < 10:
                price_score = 12.0  # 太低可能质量差
            else:
                price_score = 15.0  # 高价需要更强的listing
        score += price_score

        return round(score, 2)

    def identify_weak_listings(
        self,
        products: List[Product],
        weak_threshold: float = 60.0
    ) -> Dict[str, Any]:
        """
        识别弱Listing产品

        弱Listing特征:
        - Listing质量分数 < 60
        - 评分 < 4.0
        - 评论数 < 50 但销量不错
        - 标题/图片质量差

        Args:
            products: 产品列表
            weak_threshold: 弱listing阈值

        Returns:
            弱listing分析结果
        """
        weak_listings = []

        for product in products:
            quality_score = self.calculate_listing_quality_score(product)
            product.listing_quality_score = quality_score

            is_weak = False
            weak_reasons = []

            # 检查质量分数
            if quality_score < weak_threshold:
                is_weak = True
                weak_reasons.append(f"Listing质量分数低({quality_score})")

            # 检查评分
            if product.rating and product.rating < 4.0:
                is_weak = True
                weak_reasons.append(f"评分较低({product.rating})")

            # 检查评论数与销量比
            if product.sales_volume and product.reviews_count:
                review_rate = product.reviews_count / product.sales_volume
                if review_rate < 0.01:  # 评论转化率低
                    is_weak = True
                    weak_reasons.append("评论转化率低")

            # 检查标题长度
            if product.name and len(product.name) < 50:
                is_weak = True
                weak_reasons.append("标题过短")

            if is_weak:
                product.is_weak_listing = True
                weak_listings.append({
                    'asin': product.asin,
                    'name': product.name,
                    'price': product.price,
                    'rating': product.rating,
                    'reviews_count': product.reviews_count,
                    'sales_volume': product.sales_volume,
                    'listing_quality_score': quality_score,
                    'weak_reasons': weak_reasons
                })
            else:
                product.is_weak_listing = False

        # 统计前10名中的弱listing数量
        top_10_products = sorted(products, key=lambda p: p.sales_volume or 0, reverse=True)[:10]
        top_10_weak_count = sum(1 for p in top_10_products if p.is_weak_listing)

        return {
            'weak_listing_count': len(weak_listings),
            'weak_listing_rate': round(len(weak_listings) / len(products) * 100, 2) if products else 0,
            'top_10_weak_count': top_10_weak_count,
            'meets_threshold': top_10_weak_count >= self.min_weak_listings,
            'weak_listings': weak_listings[:20],  # 只返回前20个
            'opportunity_signal': '强' if top_10_weak_count >= 4 else ('中' if top_10_weak_count >= 2 else '弱')
        }

    def estimate_product_costs(
        self,
        product: Product,
        fba_rate: float = 0.15,
        referral_rate: float = 0.15,
        shipping_cost_per_lb: float = 0.5
    ) -> Dict[str, Any]:
        """
        估算产品成本和利润

        成本构成:
        - 产品成本 (估算为售价的25-35%)
        - FBA费用 (约15%)
        - 佣金 (约15%)
        - 运费 (基于重量)
        - 广告费 (基于ACoS)

        Args:
            product: 产品对象
            fba_rate: FBA费率
            referral_rate: 佣金费率
            shipping_cost_per_lb: 每磅运费

        Returns:
            成本利润分析
        """
        price = product.price or 0
        if price <= 0:
            return {'error': '价格无效'}

        # 估算产品成本 (售价的30%)
        estimated_product_cost = price * 0.30

        # FBA费用
        fba_fee = price * fba_rate

        # 平台佣金
        referral_fee = price * referral_rate

        # 运费估算 (假设平均1磅)
        weight = product.weight_lb or 1.0
        shipping_cost = weight * shipping_cost_per_lb

        # 总成本
        total_cost = estimated_product_cost + fba_fee + referral_fee + shipping_cost

        # 毛利润
        gross_profit = price - total_cost
        gross_margin = gross_profit / price if price > 0 else 0

        # 更新产品属性
        product.estimated_cost = round(total_cost, 2)
        product.gross_margin = round(gross_margin, 4)
        product.profit_amount = round(gross_profit, 2)

        return {
            'price': price,
            'estimated_product_cost': round(estimated_product_cost, 2),
            'fba_fee': round(fba_fee, 2),
            'referral_fee': round(referral_fee, 2),
            'shipping_cost': round(shipping_cost, 2),
            'total_cost': round(total_cost, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_margin': round(gross_margin * 100, 2),
            'meets_margin_target': gross_margin >= self.target_gross_margin,
            'margin_status': '达标' if gross_margin >= self.target_gross_margin else '未达标'
        }

    def analyze_with_advertising(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None,
        cpc_bid: Optional[float] = None,
        acos_estimate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        结合广告成本的综合分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据
            cpc_bid: CPC出价
            acos_estimate: 预估ACoS

        Returns:
            综合分析结果
        """
        # 获取CPC和ACoS数据
        cpc = cpc_bid
        acos = acos_estimate

        if sellerspirit_data:
            cpc = cpc or sellerspirit_data.cpc_bid
            acos = acos or sellerspirit_data.acos_estimate

        # 默认值
        cpc = cpc or 1.0
        acos = acos or 0.25

        advertising_analysis = {
            'cpc_bid': cpc,
            'acos_estimate': acos,
            'cpc_status': '优秀' if cpc < 0.8 else ('良好' if cpc < 1.5 else '较高'),
            'acos_status': '优秀' if acos < 0.20 else ('良好' if acos < 0.30 else '较高'),
            'advertising_viable': cpc < self.max_cpc and acos < 0.35
        }

        # 计算广告后的利润
        profit_after_ads = []
        for product in products:
            if product.price:
                ad_cost = product.price * acos
                cost_analysis = self.estimate_product_costs(product)
                if 'gross_profit' in cost_analysis:
                    net_profit = cost_analysis['gross_profit'] - ad_cost
                    net_margin = net_profit / product.price if product.price > 0 else 0
                    profit_after_ads.append({
                        'asin': product.asin,
                        'price': product.price,
                        'gross_profit': cost_analysis['gross_profit'],
                        'ad_cost': round(ad_cost, 2),
                        'net_profit': round(net_profit, 2),
                        'net_margin': round(net_margin * 100, 2),
                        'profitable': net_profit > 0
                    })

        # 统计盈利产品比例
        profitable_count = sum(1 for p in profit_after_ads if p['profitable'])

        advertising_analysis['profit_after_ads'] = profit_after_ads[:20]
        advertising_analysis['profitable_rate'] = round(profitable_count / len(profit_after_ads) * 100, 2) if profit_after_ads else 0
        advertising_analysis['recommendation'] = self._get_advertising_recommendation(cpc, acos, profitable_count / len(profit_after_ads) if profit_after_ads else 0)

        return advertising_analysis

    def _get_advertising_recommendation(
        self,
        cpc: float,
        acos: float,
        profitable_rate: float
    ) -> str:
        """生成广告建议"""
        if cpc < 0.8 and acos < 0.20 and profitable_rate > 0.7:
            return "广告环境优秀，建议积极投放PPC广告"
        elif cpc < 1.5 and acos < 0.30 and profitable_rate > 0.5:
            return "广告环境良好，建议适度投放广告并优化关键词"
        elif cpc < 2.0 and profitable_rate > 0.3:
            return "广告成本较高，建议精准投放长尾关键词"
        else:
            return "广告成本过高，建议以自然流量为主，谨慎投放广告"

    def analyze_enhanced(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        增强版蓝海分析 - 整合所有分析维度

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            完整的蓝海分析结果
        """
        if not products:
            return self._empty_result()

        self.log_info("开始增强版蓝海产品分析...")

        # 1. 基础蓝海分析
        base_result = self.analyze(products, sellerspirit_data)

        # 2. 弱Listing分析
        weak_listing_analysis = self.identify_weak_listings(products)

        # 3. 成本利润分析
        profit_analyses = []
        for product in products[:50]:  # 只分析前50个产品
            profit_analysis = self.estimate_product_costs(product)
            if 'error' not in profit_analysis:
                profit_analyses.append({
                    'asin': product.asin,
                    **profit_analysis
                })

        avg_margin = statistics.mean([p['gross_margin'] for p in profit_analyses]) if profit_analyses else 0
        margin_qualified_count = sum(1 for p in profit_analyses if p['meets_margin_target'])

        profit_summary = {
            'analyzed_count': len(profit_analyses),
            'avg_gross_margin': round(avg_margin, 2),
            'margin_qualified_count': margin_qualified_count,
            'margin_qualified_rate': round(margin_qualified_count / len(profit_analyses) * 100, 2) if profit_analyses else 0,
            'top_profit_products': sorted(profit_analyses, key=lambda x: x['gross_margin'], reverse=True)[:10]
        }

        # 4. 广告成本分析
        advertising_analysis = self.analyze_with_advertising(products, sellerspirit_data)

        # 5. 综合评估
        comprehensive_score = self._calculate_comprehensive_score(
            base_result, weak_listing_analysis, profit_summary, advertising_analysis, sellerspirit_data
        )

        # 合并结果
        result = {
            **base_result,
            'weak_listing_analysis': weak_listing_analysis,
            'profit_analysis': profit_summary,
            'advertising_analysis': advertising_analysis,
            'comprehensive_score': comprehensive_score,
            'final_recommendation': self._generate_final_recommendation(comprehensive_score)
        }

        return result

    def _calculate_comprehensive_score(
        self,
        base_result: Dict[str, Any],
        weak_listing_analysis: Dict[str, Any],
        profit_summary: Dict[str, Any],
        advertising_analysis: Dict[str, Any],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        计算综合蓝海评分 (0-100)

        评分维度:
        - 市场需求 (25分): 搜索量、销量
        - 竞争强度 (25分): 竞争指数、弱listing比例
        - 利润空间 (25分): 毛利率、广告后利润
        - 进入门槛 (25分): 价格、品牌集中度
        """
        score = 0.0
        score_breakdown = {}

        # 1. 市场需求 (25分)
        demand_score = 0.0
        if sellerspirit_data and sellerspirit_data.monthly_searches:
            searches = sellerspirit_data.monthly_searches
            if self.min_search_volume <= searches <= self.max_search_volume:
                demand_score = 25.0
            elif searches > self.max_search_volume:
                demand_score = 20.0  # 搜索量大但竞争可能激烈
            elif searches >= self.min_search_volume * 0.5:
                demand_score = 15.0
            else:
                demand_score = 8.0
        else:
            demand_score = 12.0  # 无数据给中等分
        score += demand_score
        score_breakdown['demand_score'] = demand_score

        # 2. 竞争强度 (25分) - 竞争越低分数越高
        competition_score = 25.0
        competition_index = base_result.get('market_competition', {}).get('competition_index', 50)
        if competition_index > 70:
            competition_score = 5.0
        elif competition_index > 50:
            competition_score = 12.0
        elif competition_index > 30:
            competition_score = 20.0

        # 弱listing加分
        if weak_listing_analysis.get('meets_threshold', False):
            competition_score = min(25, competition_score + 5)

        score += competition_score
        score_breakdown['competition_score'] = competition_score

        # 3. 利润空间 (25分)
        profit_score = 0.0
        avg_margin = profit_summary.get('avg_gross_margin', 0)
        if avg_margin >= 40:
            profit_score = 25.0
        elif avg_margin >= 35:
            profit_score = 22.0
        elif avg_margin >= 30:
            profit_score = 18.0
        elif avg_margin >= 25:
            profit_score = 12.0
        else:
            profit_score = 6.0

        # 广告后利润调整
        if advertising_analysis.get('profitable_rate', 0) < 50:
            profit_score = max(0, profit_score - 5)

        score += profit_score
        score_breakdown['profit_score'] = profit_score

        # 4. 进入门槛 (25分) - 门槛越低分数越高
        barrier_score = 25.0
        brand_concentration = base_result.get('market_competition', {}).get('brand_concentration', 0)
        if brand_concentration > 60:
            barrier_score = 8.0
        elif brand_concentration > 40:
            barrier_score = 15.0
        elif brand_concentration > 20:
            barrier_score = 20.0

        # CPC调整
        cpc = advertising_analysis.get('cpc_bid', 1.0)
        if cpc > self.max_cpc:
            barrier_score = max(0, barrier_score - 5)

        score += barrier_score
        score_breakdown['barrier_score'] = barrier_score

        # 评级
        if score >= 80:
            grade = 'A'
            grade_desc = '优秀蓝海机会'
        elif score >= 65:
            grade = 'B'
            grade_desc = '良好蓝海机会'
        elif score >= 50:
            grade = 'C'
            grade_desc = '一般机会'
        elif score >= 35:
            grade = 'D'
            grade_desc = '机会有限'
        else:
            grade = 'F'
            grade_desc = '不建议进入'

        return {
            'total_score': round(score, 2),
            'grade': grade,
            'grade_desc': grade_desc,
            'score_breakdown': score_breakdown
        }

    def _generate_final_recommendation(self, comprehensive_score: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终建议"""
        grade = comprehensive_score.get('grade', 'C')
        score = comprehensive_score.get('total_score', 50)
        breakdown = comprehensive_score.get('score_breakdown', {})

        recommendations = []
        action_items = []

        if grade in ['A', 'B']:
            recommendations.append("该市场具有良好的蓝海机会，建议积极进入")
            action_items.append("选择2-3个高分蓝海产品进行深入调研")
            action_items.append("分析弱listing竞品，找出可优化的差异化点")
        elif grade == 'C':
            recommendations.append("该市场机会一般，需要精准定位和差异化策略")
            action_items.append("重点关注弱listing产品，寻找改进空间")
            action_items.append("考虑长尾关键词策略降低广告成本")
        else:
            recommendations.append("该市场竞争激烈或利润空间有限，建议谨慎进入")
            action_items.append("考虑寻找其他细分市场")
            action_items.append("如坚持进入，需要强大的供应链和资金支持")

        # 基于各维度分数的具体建议
        if breakdown.get('demand_score', 0) < 15:
            recommendations.append("市场需求偏低，注意验证真实市场容量")
        if breakdown.get('competition_score', 0) < 15:
            recommendations.append("竞争较激烈，需要明确的差异化优势")
        if breakdown.get('profit_score', 0) < 15:
            recommendations.append("利润空间有限，需优化供应链成本")
        if breakdown.get('barrier_score', 0) < 15:
            recommendations.append("进入门槛较高，需要充足的启动资金")

        return {
            'overall_recommendation': '建议进入' if grade in ['A', 'B'] else ('谨慎考虑' if grade == 'C' else '不建议进入'),
            'confidence_level': '高' if score >= 70 else ('中' if score >= 50 else '低'),
            'recommendations': recommendations,
            'action_items': action_items
        }

