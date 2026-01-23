"""
市场分析器模块
分析市场规模、竞争强度、市场集中度等指标
继承 BaseAnalyzer 基类，复用公共方法
"""

from typing import List, Dict, Any, Optional
from collections import Counter

from src.database.models import Product, SellerSpiritData
from src.analyzers.base_analyzer import BaseAnalyzer


class MarketAnalyzer(BaseAnalyzer):
    """
    市场分析器

    继承 BaseAnalyzer，提供市场规模、竞争强度、品牌集中度等分析功能。
    新增：市场成熟度评估、进入难度评分、市场健康度指数
    """

    def __init__(self):
        """初始化市场分析器"""
        super().__init__(name="MarketAnalyzer")

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
        self.log_info(f"开始市场分析，产品数量: {len(products)}")

        result = {
            'market_size': self._analyze_market_size(products, sellerspirit_data),
            'competition': self._analyze_competition(products),
            'brand_concentration': self._analyze_brand_concentration(products),
            'market_blank_index': self._calculate_market_blank_index(products, sellerspirit_data),
            'price_distribution': self._analyze_price_distribution(products),
            'sales_distribution': self._analyze_sales_distribution(products),
            'market_activity': self._analyze_market_activity(products),
            'product_diversity': self._analyze_product_diversity(products),
            'market_statistics': self._calculate_market_statistics(products),
            # 新增分析维度
            'market_maturity': self._analyze_market_maturity(products, sellerspirit_data),
            'entry_difficulty': self._calculate_entry_difficulty(products, sellerspirit_data),
            'market_health': self._calculate_market_health_index(products, sellerspirit_data)
        }

        self.log_info("市场分析完成")
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

    def _analyze_price_distribution(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析价格分布

        Args:
            products: 产品列表

        Returns:
            价格分布分析结果
        """
        if not products:
            return {
                'ranges': {},
                'avg_price': 0,
                'median_price': 0,
                'price_variance': 0
            }

        prices = [p.price for p in products if p.price]

        if not prices:
            return {
                'ranges': {},
                'avg_price': 0,
                'median_price': 0,
                'price_variance': 0
            }

        # 价格区间分布
        ranges = {
            'under_10': len([p for p in prices if p < 10]),
            '10_20': len([p for p in prices if 10 <= p < 20]),
            '20_50': len([p for p in prices if 20 <= p < 50]),
            '50_100': len([p for p in prices if 50 <= p < 100]),
            '100_200': len([p for p in prices if 100 <= p < 200]),
            'over_200': len([p for p in prices if p >= 200])
        }

        # 统计指标
        avg_price = sum(prices) / len(prices)
        sorted_prices = sorted(prices)
        median_price = sorted_prices[len(sorted_prices) // 2]

        # 价格方差（衡量价格分散程度）
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)

        return {
            'ranges': ranges,
            'avg_price': round(avg_price, 2),
            'median_price': round(median_price, 2),
            'min_price': round(min(prices), 2),
            'max_price': round(max(prices), 2),
            'price_variance': round(variance, 2)
        }

    def _analyze_sales_distribution(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析销量分布

        Args:
            products: 产品列表

        Returns:
            销量分布分析结果
        """
        if not products:
            return {
                'ranges': {},
                'total_sales': 0,
                'avg_sales': 0,
                'top_10_sales': 0
            }

        sales_list = [p.sales_volume for p in products if p.sales_volume]

        if not sales_list:
            return {
                'ranges': {},
                'total_sales': 0,
                'avg_sales': 0,
                'top_10_sales': 0
            }

        # 销量区间分布
        ranges = {
            'under_10': len([s for s in sales_list if s < 10]),
            '10_100': len([s for s in sales_list if 10 <= s < 100]),
            '100_500': len([s for s in sales_list if 100 <= s < 500]),
            '500_1000': len([s for s in sales_list if 500 <= s < 1000]),
            'over_1000': len([s for s in sales_list if s >= 1000])
        }

        # 统计指标
        total_sales = sum(sales_list)
        avg_sales = total_sales / len(sales_list)

        # Top 10产品销量
        sorted_sales = sorted(sales_list, reverse=True)
        top_10_sales = sum(sorted_sales[:10])

        return {
            'ranges': ranges,
            'total_sales': total_sales,
            'avg_sales': round(avg_sales, 2),
            'top_10_sales': top_10_sales,
            'top_10_percentage': round(top_10_sales / total_sales * 100, 2) if total_sales > 0 else 0
        }

    def _analyze_market_activity(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析市场活跃度

        Args:
            products: 产品列表

        Returns:
            市场活跃度分析结果
        """
        if not products:
            return {
                'activity_level': '未知',
                'active_products': 0,
                'activity_rate': 0
            }

        # 有销量的产品视为活跃产品
        active_products = [p for p in products if p.sales_volume and p.sales_volume > 0]
        activity_rate = len(active_products) / len(products) * 100 if products else 0

        # 活跃度等级
        if activity_rate >= 80:
            activity_level = '非常活跃'
        elif activity_rate >= 60:
            activity_level = '活跃'
        elif activity_rate >= 40:
            activity_level = '一般'
        elif activity_rate >= 20:
            activity_level = '较低'
        else:
            activity_level = '冷清'

        return {
            'activity_level': activity_level,
            'active_products': len(active_products),
            'total_products': len(products),
            'activity_rate': round(activity_rate, 2)
        }

    def _analyze_product_diversity(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析产品多样性

        Args:
            products: 产品列表

        Returns:
            产品多样性分析结果
        """
        if not products:
            return {
                'diversity_score': 0,
                'unique_brands': 0,
                'price_range_span': 0
            }

        # 品牌多样性
        unique_brands = len(set(p.brand for p in products if p.brand))

        # 价格区间跨度
        prices = [p.price for p in products if p.price]
        price_range_span = (max(prices) - min(prices)) if prices else 0

        # 多样性评分（0-100）
        diversity_score = 0

        # 品牌多样性（50分）
        if unique_brands > 50:
            diversity_score += 50
        elif unique_brands > 30:
            diversity_score += 40
        elif unique_brands > 10:
            diversity_score += 30
        else:
            diversity_score += 20

        # 价格多样性（50分）
        if prices:
            avg_price = sum(prices) / len(prices)
            if price_range_span > avg_price * 5:
                diversity_score += 50
            elif price_range_span > avg_price * 3:
                diversity_score += 40
            elif price_range_span > avg_price * 2:
                diversity_score += 30
            else:
                diversity_score += 20

        return {
            'diversity_score': diversity_score,
            'unique_brands': unique_brands,
            'price_range_span': round(price_range_span, 2)
        }

    def _calculate_market_statistics(self, products: List[Product]) -> Dict[str, Any]:
        """
        计算市场统计信息

        Args:
            products: 产品列表

        Returns:
            市场统计信息
        """
        if not products:
            return {
                'product_count': 0,
                'avg_price': 0,
                'total_sales': 0,
                'avg_sales': 0,
                'total_revenue': 0
            }

        # 价格统计
        prices = [p.price for p in products if p.price]
        avg_price = sum(prices) / len(prices) if prices else 0

        # 销量统计
        sales_list = [p.sales_volume for p in products if p.sales_volume]
        total_sales = sum(sales_list)
        avg_sales = total_sales / len(sales_list) if sales_list else 0

        # 估算总收入
        total_revenue = sum(
            (p.price or 0) * (p.sales_volume or 0)
            for p in products
        )

        return {
            'product_count': len(products),
            'avg_price': round(avg_price, 2),
            'total_sales': total_sales,
            'avg_sales': round(avg_sales, 2),
            'total_revenue': round(total_revenue, 2)
        }

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

        market_stats = analysis_result.get('market_statistics', {})
        price_dist = analysis_result.get('price_distribution', {})
        sales_dist = analysis_result.get('sales_distribution', {})
        market_activity = analysis_result.get('market_activity', {})

        summary = f"""
市场分析摘要
{'=' * 50}

市场规模:
- 总ASIN数: {market_size.get('total_asins', 0)}
- 月搜索量: {market_size.get('monthly_searches', '未知')}
- 市场类型: {market_size.get('size_rating', '未知')}
- 总销量: {market_stats.get('total_sales', 0)}
- 估算总收入: ${market_stats.get('total_revenue', 0):,.2f}

价格分析:
- 平均价格: ${price_dist.get('avg_price', 0)}
- 价格区间: ${price_dist.get('min_price', 0)} - ${price_dist.get('max_price', 0)}
- 中位价格: ${price_dist.get('median_price', 0)}

销量分析:
- 平均销量: {sales_dist.get('avg_sales', 0)}
- Top10销量占比: {sales_dist.get('top_10_percentage', 0)}%

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

市场活跃度:
- 活跃度等级: {market_activity.get('activity_level', '未知')}
- 活跃产品数: {market_activity.get('active_products', 0)}
- 活跃率: {market_activity.get('activity_rate', 0)}%

市场机会:
- 市场空白指数: {blank_index}
- 机会等级: {opportunity}
"""

        return summary

    # ==================== 新增分析维度 ====================

    def _analyze_market_maturity(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        分析市场成熟度

        基于以下指标判断市场所处阶段：
        - 新兴市场：平均评论数<100，新品占比>20%
        - 成长市场：平均评论数100-500，新品占比10-20%
        - 成熟市场：平均评论数500-1000，新品占比5-10%
        - 衰退市场：平均评论数>1000，新品占比<5%，销量下降

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场成熟度分析结果
        """
        if not products:
            return {
                'stage': '未知',
                'stage_desc': '数据不足',
                'maturity_score': 0,
                'indicators': {}
            }

        # 提取评论数据
        reviews = self.extract_numeric_values(products, 'reviews_count')
        review_stats = self.calculate_statistics(reviews)

        # 计算新品占比（假设评论数<50为新品）
        new_products = [p for p in products if (p.reviews_count or 0) < 50]
        new_product_rate = self.safe_percentage(len(new_products), len(products))

        # 计算高评论产品占比（评论数>500）
        mature_products = [p for p in products if (p.reviews_count or 0) > 500]
        mature_product_rate = self.safe_percentage(len(mature_products), len(products))

        # 判断市场阶段
        avg_reviews = review_stats.mean
        if avg_reviews < 100 and new_product_rate > 20:
            stage = '新兴市场'
            stage_desc = '市场处于早期阶段，竞争较少，机会较多'
            maturity_score = 25
        elif avg_reviews < 500 and new_product_rate > 10:
            stage = '成长市场'
            stage_desc = '市场快速发展中，仍有较好的进入机会'
            maturity_score = 50
        elif avg_reviews < 1000 and mature_product_rate < 30:
            stage = '成熟市场'
            stage_desc = '市场趋于稳定，需要差异化策略'
            maturity_score = 75
        else:
            stage = '饱和市场'
            stage_desc = '市场高度成熟，进入门槛高'
            maturity_score = 90

        return {
            'stage': stage,
            'stage_desc': stage_desc,
            'maturity_score': maturity_score,
            'indicators': {
                'avg_reviews': round(avg_reviews, 2),
                'median_reviews': round(review_stats.median, 2),
                'new_product_rate': new_product_rate,
                'mature_product_rate': mature_product_rate,
                'review_std': round(review_stats.std, 2)
            }
        }

    def _calculate_entry_difficulty(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        计算市场进入难度评分

        评分维度（0-100，越高越难）：
        - 竞争强度 (30分)：基于评论数和产品数量
        - 品牌壁垒 (25分)：基于品牌集中度
        - 资金门槛 (25分)：基于平均价格和库存需求
        - 运营难度 (20分)：基于评分要求和广告成本

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            进入难度评估结果
        """
        if not products:
            return {
                'difficulty_score': 0,
                'difficulty_level': '未知',
                'breakdown': {},
                'recommendations': []
            }

        # 1. 竞争强度分数 (30分)
        reviews = self.extract_numeric_values(products, 'reviews_count')
        avg_reviews = sum(reviews) / len(reviews) if reviews else 0
        competition_score = self.normalize_score_log(avg_reviews, 1, 5000) * 0.3

        # 2. 品牌壁垒分数 (25分)
        brands = self.extract_values(products, 'brand')
        unique_brands = len(set(brands))
        brand_concentration = 1 - (unique_brands / len(products)) if products else 0
        brand_barrier_score = brand_concentration * 100 * 0.25

        # 3. 资金门槛分数 (25分)
        prices = self.extract_numeric_values(products, 'price')
        price_stats = self.calculate_statistics(prices)
        # 价格越高，资金门槛越高
        capital_score = self.normalize_score(price_stats.mean, 10, 100) * 0.25

        # 4. 运营难度分数 (20分)
        ratings = self.extract_numeric_values(products, 'rating')
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        # 平均评分越高，运营难度越大（需要更高质量）
        operation_score = self.normalize_score(avg_rating, 3.5, 4.8) * 0.20

        # 总分
        total_score = competition_score + brand_barrier_score + capital_score + operation_score
        total_score = min(100, max(0, total_score))

        # 难度等级
        difficulty_level, difficulty_desc = self.grade_score_with_desc(100 - total_score)
        # 反转等级描述
        if total_score >= 80:
            difficulty_level = '极高'
            difficulty_desc = '进入门槛极高，不建议新手进入'
        elif total_score >= 60:
            difficulty_level = '高'
            difficulty_desc = '进入门槛较高，需要充足资源'
        elif total_score >= 40:
            difficulty_level = '中等'
            difficulty_desc = '进入门槛适中，需要差异化策略'
        elif total_score >= 20:
            difficulty_level = '低'
            difficulty_desc = '进入门槛较低，适合新卖家'
        else:
            difficulty_level = '极低'
            difficulty_desc = '进入门槛很低，机会较多'

        # 生成建议
        recommendations = []
        if competition_score > 20:
            recommendations.append("竞争激烈，建议寻找细分市场或长尾关键词")
        if brand_barrier_score > 15:
            recommendations.append("品牌集中度高，建议打造差异化品牌")
        if capital_score > 15:
            recommendations.append("资金门槛较高，建议准备充足启动资金")
        if operation_score > 12:
            recommendations.append("用户对质量要求高，建议注重产品品质")

        return {
            'difficulty_score': round(total_score, 2),
            'difficulty_level': difficulty_level,
            'difficulty_desc': difficulty_desc,
            'breakdown': {
                'competition_score': round(competition_score, 2),
                'brand_barrier_score': round(brand_barrier_score, 2),
                'capital_score': round(capital_score, 2),
                'operation_score': round(operation_score, 2)
            },
            'recommendations': recommendations
        }

    def _calculate_market_health_index(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        计算市场健康度指数

        健康市场特征：
        - 价格分布合理（不过度集中）
        - 销量分布均匀（非头部垄断）
        - 评分普遍较高（用户满意度高）
        - 新品有机会（市场活力）

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场健康度评估结果
        """
        if not products:
            return {
                'health_score': 0,
                'health_level': '未知',
                'factors': {}
            }

        # 1. 价格健康度 (25分) - 价格分布越均匀越健康
        prices = self.extract_numeric_values(products, 'price')
        price_stats = self.calculate_statistics(prices)
        # 变异系数（CV）越大，分布越分散，越健康
        price_cv = self.safe_divide(price_stats.std, price_stats.mean, 0)
        price_health = min(25, price_cv * 50)

        # 2. 销量健康度 (25分) - Top10占比越低越健康
        sales = self.extract_numeric_values(products, 'sales_volume')
        if sales:
            sorted_sales = sorted(sales, reverse=True)
            top10_sales = sum(sorted_sales[:10])
            total_sales = sum(sales)
            top10_ratio = self.safe_divide(top10_sales, total_sales, 1)
            sales_health = (1 - top10_ratio) * 25
        else:
            sales_health = 12.5

        # 3. 评分健康度 (25分) - 平均评分越高越健康
        ratings = self.extract_numeric_values(products, 'rating')
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            rating_health = self.normalize_score(avg_rating, 3.0, 4.8) * 0.25
        else:
            rating_health = 12.5

        # 4. 市场活力 (25分) - 新品占比适中最健康
        new_products = [p for p in products if (p.reviews_count or 0) < 50]
        new_rate = self.safe_percentage(len(new_products), len(products))
        # 新品占比10-30%最健康
        if 10 <= new_rate <= 30:
            vitality_health = 25
        elif 5 <= new_rate < 10 or 30 < new_rate <= 50:
            vitality_health = 18
        else:
            vitality_health = 10

        # 总分
        health_score = price_health + sales_health + rating_health + vitality_health
        health_score = min(100, max(0, health_score))

        # 健康等级
        grade, grade_desc = self.grade_score_with_desc(health_score)

        return {
            'health_score': round(health_score, 2),
            'health_level': grade,
            'health_desc': grade_desc,
            'factors': {
                'price_health': round(price_health, 2),
                'sales_health': round(sales_health, 2),
                'rating_health': round(rating_health, 2),
                'vitality_health': round(vitality_health, 2)
            },
            'interpretation': self._interpret_health_score(health_score)
        }

    def _interpret_health_score(self, score: float) -> str:
        """解释健康度分数"""
        if score >= 80:
            return "市场非常健康，竞争环境良好，适合进入"
        elif score >= 60:
            return "市场较为健康，存在一定机会"
        elif score >= 40:
            return "市场健康度一般，需要谨慎评估"
        elif score >= 20:
            return "市场健康度较低，可能存在垄断或价格战"
        else:
            return "市场健康度很低，不建议进入"

