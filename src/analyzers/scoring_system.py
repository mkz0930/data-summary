"""
综合评分系统模块
对产品和市场进行多维度评分
"""

from typing import List, Dict, Any

from src.database.models import Product, SellerSpiritData
from src.utils.logger import get_logger


class ScoringSystem:
    """综合评分系统"""

    def __init__(self):
        """初始化综合评分系统"""
        self.logger = get_logger()

    def score_product(self, product: Product) -> Dict[str, Any]:
        """
        对单个产品进行综合评分

        评分维度：
        1. 销量表现 (30分)
        2. 评分质量 (25分)
        3. 评论数量 (20分)
        4. 价格竞争力 (15分)
        5. 市场潜力 (10分)

        Args:
            product: 产品对象

        Returns:
            评分结果
        """
        scores = {}

        # 1. 销量表现 (30分)
        scores['sales_score'] = self._score_sales(product)

        # 2. 评分质量 (25分)
        scores['rating_score'] = self._score_rating(product)

        # 3. 评论数量 (20分)
        scores['reviews_score'] = self._score_reviews(product)

        # 4. 价格竞争力 (15分)
        scores['price_score'] = self._score_price(product)

        # 5. 市场潜力 (10分)
        scores['potential_score'] = self._score_potential(product)

        # 计算总分
        total_score = sum(scores.values())

        # 评级
        grade = self._calculate_grade(total_score)

        return {
            'total_score': round(total_score, 2),
            'grade': grade,
            'scores': scores,
            'strengths': self._identify_strengths(scores),
            'weaknesses': self._identify_weaknesses(scores)
        }

    def score_market(
        self,
        products: List[Product],
        sellerspirit_data: SellerSpiritData = None
    ) -> Dict[str, Any]:
        """
        对市场进行综合评分

        评分维度：
        1. 市场规模 (25分)
        2. 增长潜力 (25分)
        3. 竞争强度 (20分)
        4. 进入门槛 (15分)
        5. 利润空间 (15分)

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场评分结果
        """
        if not products:
            return {
                'total_score': 0,
                'grade': 'F',
                'scores': {},
                'recommendation': 'insufficient_data'
            }

        scores = {}

        # 1. 市场规模 (25分)
        scores['market_size_score'] = self._score_market_size(products, sellerspirit_data)

        # 2. 增长潜力 (25分)
        scores['growth_score'] = self._score_growth_potential(products, sellerspirit_data)

        # 3. 竞争强度 (20分) - 竞争越弱分数越高
        scores['competition_score'] = self._score_competition(products)

        # 4. 进入门槛 (15分) - 门槛越低分数越高
        scores['entry_barrier_score'] = self._score_entry_barrier(products)

        # 5. 利润空间 (15分)
        scores['profit_score'] = self._score_profit_potential(products)

        # 计算总分
        total_score = sum(scores.values())

        # 评级
        grade = self._calculate_grade(total_score)

        # 生成建议
        recommendation = self._generate_market_recommendation(total_score, scores)

        return {
            'total_score': round(total_score, 2),
            'grade': grade,
            'scores': scores,
            'recommendation': recommendation,
            'key_factors': self._identify_key_factors(scores)
        }

    def _score_sales(self, product: Product) -> float:
        """
        评分：销量表现 (30分)

        Args:
            product: 产品对象

        Returns:
            销量分数
        """
        sales = product.sales_volume or 0

        if sales >= 1000:
            return 30.0
        elif sales >= 500:
            return 27.0
        elif sales >= 200:
            return 24.0
        elif sales >= 100:
            return 20.0
        elif sales >= 50:
            return 15.0
        elif sales >= 20:
            return 10.0
        else:
            return 5.0

    def _score_rating(self, product: Product) -> float:
        """
        评分：评分质量 (25分)

        Args:
            product: 产品对象

        Returns:
            评分分数
        """
        rating = product.rating or 0

        if rating >= 4.7:
            return 25.0
        elif rating >= 4.5:
            return 23.0
        elif rating >= 4.3:
            return 20.0
        elif rating >= 4.0:
            return 17.0
        elif rating >= 3.5:
            return 12.0
        elif rating >= 3.0:
            return 7.0
        else:
            return 3.0

    def _score_reviews(self, product: Product) -> float:
        """
        评分：评论数量 (20分)

        Args:
            product: 产品对象

        Returns:
            评论分数
        """
        reviews = product.reviews_count or 0

        if reviews >= 5000:
            return 20.0
        elif reviews >= 2000:
            return 18.0
        elif reviews >= 1000:
            return 16.0
        elif reviews >= 500:
            return 14.0
        elif reviews >= 200:
            return 11.0
        elif reviews >= 100:
            return 8.0
        elif reviews >= 50:
            return 5.0
        else:
            return 2.0

    def _score_price(self, product: Product) -> float:
        """
        评分：价格竞争力 (15分)

        价格适中（$20-50）得分最高

        Args:
            product: 产品对象

        Returns:
            价格分数
        """
        price = product.price or 0

        if 20 <= price <= 50:
            return 15.0
        elif 15 <= price < 20 or 50 < price <= 70:
            return 12.0
        elif 10 <= price < 15 or 70 < price <= 100:
            return 9.0
        elif price < 10 or price > 100:
            return 5.0
        else:
            return 7.0

    def _score_potential(self, product: Product) -> float:
        """
        评分：市场潜力 (10分)

        基于评论数和评分的比例判断潜力

        Args:
            product: 产品对象

        Returns:
            潜力分数
        """
        rating = product.rating or 0
        reviews = product.reviews_count or 0

        # 高评分 + 少评论 = 高潜力（新品机会）
        if rating >= 4.0 and reviews < 100:
            return 10.0
        elif rating >= 4.0 and reviews < 500:
            return 8.0
        elif rating >= 3.5 and reviews < 100:
            return 7.0
        elif rating >= 4.0:
            return 6.0
        else:
            return 3.0

    def _score_market_size(
        self,
        products: List[Product],
        sellerspirit_data: SellerSpiritData = None
    ) -> float:
        """
        评分：市场规模 (25分)

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场规模分数
        """
        # 使用卖家精灵的月搜索量
        if sellerspirit_data and sellerspirit_data.monthly_searches:
            search_volume = sellerspirit_data.monthly_searches
            if search_volume >= 100000:
                return 25.0
            elif search_volume >= 50000:
                return 22.0
            elif search_volume >= 20000:
                return 18.0
            elif search_volume >= 10000:
                return 14.0
            elif search_volume >= 5000:
                return 10.0
            else:
                return 5.0

        # 否则使用产品数量和总销量估算
        product_count = len(products)
        total_sales = sum(p.sales_volume for p in products if p.sales_volume)

        if product_count >= 200 or total_sales >= 50000:
            return 25.0
        elif product_count >= 100 or total_sales >= 20000:
            return 20.0
        elif product_count >= 50 or total_sales >= 10000:
            return 15.0
        elif product_count >= 20 or total_sales >= 5000:
            return 10.0
        else:
            return 5.0

    def _score_growth_potential(
        self,
        products: List[Product],
        sellerspirit_data: SellerSpiritData = None
    ) -> float:
        """
        评分：增长潜力 (25分)

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            增长潜力分数
        """
        score = 12.5  # 基准分

        # 新品占比
        new_products = [
            p for p in products
            if p.reviews_count and p.reviews_count < 50
        ]
        new_product_rate = len(new_products) / len(products) * 100

        if new_product_rate > 20:
            score += 7.5
        elif new_product_rate > 10:
            score += 5.0
        elif new_product_rate < 5:
            score -= 2.5

        return max(0, min(25, score))

    def _score_competition(self, products: List[Product]) -> float:
        """
        评分：竞争强度 (20分)

        竞争越弱，分数越高

        Args:
            products: 产品列表

        Returns:
            竞争分数
        """
        if not products:
            return 10.0

        # 计算竞争指标
        avg_reviews = sum(p.reviews_count for p in products if p.reviews_count) / len(products)
        high_rating_rate = len([p for p in products if p.rating and p.rating >= 4.0]) / len(products) * 100

        score = 20.0

        # 平均评论数越高，竞争越激烈
        if avg_reviews > 1000:
            score -= 8.0
        elif avg_reviews > 500:
            score -= 5.0
        elif avg_reviews > 200:
            score -= 3.0

        # 高评分产品占比越高，竞争越激烈
        if high_rating_rate > 70:
            score -= 5.0
        elif high_rating_rate > 50:
            score -= 3.0

        return max(0, score)

    def _score_entry_barrier(self, products: List[Product]) -> float:
        """
        评分：进入门槛 (15分)

        门槛越低，分数越高

        Args:
            products: 产品列表

        Returns:
            进入门槛分数
        """
        if not products:
            return 7.5

        score = 15.0

        # 平均价格（价格越高，门槛越高）
        avg_price = sum(p.price for p in products if p.price) / len(products)
        if avg_price > 100:
            score -= 5.0
        elif avg_price > 50:
            score -= 3.0

        # 品牌集中度（品牌越集中，门槛越高）
        brands = [p.brand for p in products if p.brand]
        if brands:
            brand_set = set(brands)
            brand_concentration = 1 - (len(brand_set) / len(brands))
            if brand_concentration > 0.5:
                score -= 5.0
            elif brand_concentration > 0.3:
                score -= 3.0

        return max(0, score)

    def _score_profit_potential(self, products: List[Product]) -> float:
        """
        评分：利润空间 (15分)

        Args:
            products: 产品列表

        Returns:
            利润空间分数
        """
        if not products:
            return 7.5

        # 平均价格
        avg_price = sum(p.price for p in products if p.price) / len(products)

        # 价格适中（$30-80）利润空间较好
        if 30 <= avg_price <= 80:
            return 15.0
        elif 20 <= avg_price < 30 or 80 < avg_price <= 100:
            return 12.0
        elif 15 <= avg_price < 20 or 100 < avg_price <= 150:
            return 9.0
        else:
            return 6.0

    def _calculate_grade(self, total_score: float) -> str:
        """
        根据总分计算评级

        Args:
            total_score: 总分

        Returns:
            评级 (A+, A, B+, B, C+, C, D, F)
        """
        if total_score >= 90:
            return 'A+'
        elif total_score >= 85:
            return 'A'
        elif total_score >= 80:
            return 'B+'
        elif total_score >= 75:
            return 'B'
        elif total_score >= 70:
            return 'C+'
        elif total_score >= 60:
            return 'C'
        elif total_score >= 50:
            return 'D'
        else:
            return 'F'

    def _identify_strengths(self, scores: Dict[str, float]) -> List[str]:
        """
        识别产品优势

        Args:
            scores: 各维度分数

        Returns:
            优势列表
        """
        strengths = []

        score_names = {
            'sales_score': ('销量表现', 30),
            'rating_score': ('评分质量', 25),
            'reviews_score': ('评论数量', 20),
            'price_score': ('价格竞争力', 15),
            'potential_score': ('市场潜力', 10)
        }

        for key, (name, max_score) in score_names.items():
            score = scores.get(key, 0)
            if score >= max_score * 0.8:  # 达到80%以上认为是优势
                strengths.append(name)

        return strengths

    def _identify_weaknesses(self, scores: Dict[str, float]) -> List[str]:
        """
        识别产品劣势

        Args:
            scores: 各维度分数

        Returns:
            劣势列表
        """
        weaknesses = []

        score_names = {
            'sales_score': ('销量表现', 30),
            'rating_score': ('评分质量', 25),
            'reviews_score': ('评论数量', 20),
            'price_score': ('价格竞争力', 15),
            'potential_score': ('市场潜力', 10)
        }

        for key, (name, max_score) in score_names.items():
            score = scores.get(key, 0)
            if score < max_score * 0.5:  # 低于50%认为是劣势
                weaknesses.append(name)

        return weaknesses

    def _generate_market_recommendation(
        self,
        total_score: float,
        scores: Dict[str, float]
    ) -> str:
        """
        生成市场建议

        Args:
            total_score: 总分
            scores: 各维度分数

        Returns:
            建议文本
        """
        if total_score >= 80:
            return "强烈推荐进入，市场条件优越"
        elif total_score >= 70:
            return "推荐进入，市场机会较好"
        elif total_score >= 60:
            return "可以考虑进入，需要制定合理策略"
        elif total_score >= 50:
            return "谨慎进入，市场挑战较大"
        else:
            return "不建议进入，市场条件不佳"

    def _identify_key_factors(self, scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        识别关键因素

        Args:
            scores: 各维度分数

        Returns:
            关键因素列表
        """
        score_names = {
            'market_size_score': ('市场规模', 25),
            'growth_score': ('增长潜力', 25),
            'competition_score': ('竞争强度', 20),
            'entry_barrier_score': ('进入门槛', 15),
            'profit_score': ('利润空间', 15)
        }

        factors = []
        for key, (name, max_score) in score_names.items():
            score = scores.get(key, 0)
            percentage = round(score / max_score * 100, 2)
            factors.append({
                'factor': name,
                'score': round(score, 2),
                'max_score': max_score,
                'percentage': percentage
            })

        # 按分数占比排序
        factors.sort(key=lambda x: x['percentage'], reverse=True)

        return factors
