"""
趋势预测分析器模块
分析市场趋势和预测未来走向
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from src.database.models import Product, SellerSpiritData
from src.utils.logger import get_logger


class TrendAnalyzer:
    """趋势预测分析器"""

    def __init__(self):
        """初始化趋势预测分析器"""
        self.logger = get_logger()

    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: SellerSpiritData = None
    ) -> Dict[str, Any]:
        """
        综合趋势分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            趋势分析结果
        """
        self.logger.info(f"开始趋势预测分析，产品数量: {len(products)}")

        result = {
            'market_trend': self._analyze_market_trend(products, sellerspirit_data),
            'new_product_trend': self._analyze_new_product_trend(products),
            'price_trend': self._analyze_price_trend(products),
            'competition_trend': self._analyze_competition_trend(products),
            'forecast': self._generate_forecast(products, sellerspirit_data)
        }

        self.logger.info("趋势预测分析完成")
        return result

    def _analyze_market_trend(
        self,
        products: List[Product],
        sellerspirit_data: SellerSpiritData = None
    ) -> Dict[str, Any]:
        """
        分析市场整体趋势

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场趋势分析结果
        """
        if not products:
            return {
                'trend_direction': 'unknown',
                'trend_strength': 0,
                'indicators': {}
            }

        indicators = {}

        # 指标1: 新品占比（高占比表示市场活跃）
        new_products = self._identify_new_products(products)
        new_product_rate = len(new_products) / len(products) * 100
        indicators['new_product_rate'] = round(new_product_rate, 2)

        # 指标2: 平均评论数（高评论数表示市场成熟）
        reviews = [p.reviews_count for p in products if p.reviews_count]
        avg_reviews = sum(reviews) / len(reviews) if reviews else 0
        indicators['avg_reviews'] = round(avg_reviews, 2)

        # 指标3: 市场集中度（CR4）
        if sellerspirit_data and sellerspirit_data.cr4:
            indicators['cr4'] = sellerspirit_data.cr4
        else:
            # 计算Top 4产品的销量占比
            sales_list = sorted(
                [p.sales_volume for p in products if p.sales_volume],
                reverse=True
            )
            if len(sales_list) >= 4:
                top4_sales = sum(sales_list[:4])
                total_sales = sum(sales_list)
                indicators['cr4'] = round(top4_sales / total_sales * 100, 2) if total_sales > 0 else 0
            else:
                indicators['cr4'] = 0

        # 指标4: 购买率（从卖家精灵数据获取）
        if sellerspirit_data:
            if hasattr(sellerspirit_data, 'purchase_rate') and sellerspirit_data.purchase_rate:
                indicators['purchase_rate'] = sellerspirit_data.purchase_rate
            elif isinstance(sellerspirit_data, dict):
                indicators['purchase_rate'] = sellerspirit_data.get('purchase_rate', 0)

        # 指标5: 转化率（从卖家精灵数据获取）
        if sellerspirit_data:
            if hasattr(sellerspirit_data, 'conversion_rate') and sellerspirit_data.conversion_rate:
                indicators['conversion_rate'] = sellerspirit_data.conversion_rate
            elif isinstance(sellerspirit_data, dict):
                indicators['conversion_rate'] = sellerspirit_data.get('conversion_rate', 0)

        # 综合判断趋势方向
        trend_direction = self._determine_trend_direction(indicators)
        trend_strength = self._calculate_trend_strength(indicators)

        return {
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'indicators': indicators,
            'interpretation': self._interpret_market_trend(trend_direction, indicators)
        }

    def _determine_trend_direction(self, indicators: Dict[str, Any]) -> str:
        """
        判断趋势方向

        Args:
            indicators: 指标字典

        Returns:
            趋势方向: 'growing', 'stable', 'declining'
        """
        score = 0

        # 新品占比高 -> 增长
        new_product_rate = indicators.get('new_product_rate', 0)
        if new_product_rate > 20:
            score += 2
        elif new_product_rate > 10:
            score += 1

        # 搜索趋势
        search_trend = indicators.get('search_trend', 'stable')
        if search_trend == 'rising':
            score += 2
        elif search_trend == 'declining':
            score -= 2

        # CR4低 -> 竞争激烈 -> 增长期
        cr4 = indicators.get('cr4', 0)
        if cr4 < 40:
            score += 1
        elif cr4 > 60:
            score -= 1

        # 购买率高 -> 市场活跃 -> 增长
        purchase_rate = indicators.get('purchase_rate', 0)
        if purchase_rate > 15:
            score += 2
        elif purchase_rate > 10:
            score += 1
        elif purchase_rate < 5:
            score -= 1

        # 转化率高 -> 市场健康 -> 增长
        conversion_rate = indicators.get('conversion_rate', 0)
        if conversion_rate > 15:
            score += 2
        elif conversion_rate > 10:
            score += 1
        elif conversion_rate < 5:
            score -= 1

        # 判断
        if score >= 2:
            return 'growing'
        elif score <= -2:
            return 'declining'
        else:
            return 'stable'

    def _calculate_trend_strength(self, indicators: Dict[str, Any]) -> float:
        """
        计算趋势强度（0-100）

        Args:
            indicators: 指标字典

        Returns:
            趋势强度分数
        """
        strength = 50.0  # 基准分

        # 新品占比影响
        new_product_rate = indicators.get('new_product_rate', 0)
        if new_product_rate > 20:
            strength += 20
        elif new_product_rate > 10:
            strength += 10

        # 搜索趋势影响
        search_trend = indicators.get('search_trend', 'stable')
        if search_trend == 'rising':
            strength += 15
        elif search_trend == 'declining':
            strength -= 15

        # CR4影响
        cr4 = indicators.get('cr4', 0)
        if cr4 < 40:
            strength += 10
        elif cr4 > 60:
            strength -= 10

        # 购买率影响
        purchase_rate = indicators.get('purchase_rate', 0)
        if purchase_rate > 15:
            strength += 15
        elif purchase_rate > 10:
            strength += 10
        elif purchase_rate < 5:
            strength -= 10

        # 转化率影响
        conversion_rate = indicators.get('conversion_rate', 0)
        if conversion_rate > 15:
            strength += 15
        elif conversion_rate > 10:
            strength += 10
        elif conversion_rate < 5:
            strength -= 10

        return max(0, min(100, strength))

    def _interpret_market_trend(
        self,
        trend_direction: str,
        indicators: Dict[str, Any]
    ) -> str:
        """
        解释市场趋势

        Args:
            trend_direction: 趋势方向
            indicators: 指标字典

        Returns:
            趋势解释文本
        """
        if trend_direction == 'growing':
            return "市场处于增长期，新品不断涌入，竞争激烈但机会较多"
        elif trend_direction == 'declining':
            return "市场趋于饱和，增长放缓，竞争格局相对稳定"
        else:
            return "市场处于稳定期，供需平衡，适合稳健经营"

    def _analyze_new_product_trend(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析新品趋势

        Args:
            products: 产品列表

        Returns:
            新品趋势分析结果
        """
        if not products:
            return {
                'new_product_count': 0,
                'new_product_rate': 0,
                'trend': 'unknown'
            }

        new_products = self._identify_new_products(products)
        new_product_rate = len(new_products) / len(products) * 100

        # 分析新品表现
        if new_products:
            new_ratings = [p.rating for p in new_products if p.rating]
            new_sales = [p.sales_volume for p in new_products if p.sales_volume]

            avg_new_rating = sum(new_ratings) / len(new_ratings) if new_ratings else 0
            avg_new_sales = sum(new_sales) / len(new_sales) if new_sales else 0
        else:
            avg_new_rating = 0
            avg_new_sales = 0

        # 判断新品趋势
        if new_product_rate > 20:
            trend = 'very_active'
            interpretation = "新品非常活跃，市场处于快速增长期"
        elif new_product_rate > 10:
            trend = 'active'
            interpretation = "新品较为活跃，市场有一定增长空间"
        elif new_product_rate > 5:
            trend = 'moderate'
            interpretation = "新品适度进入，市场相对稳定"
        else:
            trend = 'slow'
            interpretation = "新品较少，市场可能趋于饱和"

        return {
            'new_product_count': len(new_products),
            'new_product_rate': round(new_product_rate, 2),
            'avg_new_rating': round(avg_new_rating, 2),
            'avg_new_sales': round(avg_new_sales, 2),
            'trend': trend,
            'interpretation': interpretation
        }

    def _analyze_price_trend(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析价格趋势

        Args:
            products: 产品列表

        Returns:
            价格趋势分析结果
        """
        if not products:
            return {
                'trend': 'unknown',
                'avg_price': 0,
                'price_volatility': 0
            }

        prices = [p.price for p in products if p.price]
        if not prices:
            return {
                'trend': 'unknown',
                'avg_price': 0,
                'price_volatility': 0
            }

        # 计算价格统计
        avg_price = sum(prices) / len(prices)
        sorted_prices = sorted(prices)
        median_price = sorted_prices[len(sorted_prices) // 2]

        # 计算价格波动性（标准差）
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        price_volatility = (std_dev / avg_price * 100) if avg_price > 0 else 0

        # 分析新品价格 vs 老品价格
        new_products = self._identify_new_products(products)
        old_products = [p for p in products if p not in new_products]

        new_prices = [p.price for p in new_products if p.price]
        old_prices = [p.price for p in old_products if p.price]

        avg_new_price = sum(new_prices) / len(new_prices) if new_prices else 0
        avg_old_price = sum(old_prices) / len(old_prices) if old_prices else 0

        # 判断价格趋势
        if avg_new_price > avg_old_price * 1.1:
            trend = 'rising'
            interpretation = "新品价格高于老品，市场价格呈上升趋势"
        elif avg_new_price < avg_old_price * 0.9:
            trend = 'falling'
            interpretation = "新品价格低于老品，市场价格呈下降趋势"
        else:
            trend = 'stable'
            interpretation = "新老产品价格相近，市场价格相对稳定"

        return {
            'trend': trend,
            'avg_price': round(avg_price, 2),
            'median_price': round(median_price, 2),
            'price_volatility': round(price_volatility, 2),
            'avg_new_price': round(avg_new_price, 2),
            'avg_old_price': round(avg_old_price, 2),
            'interpretation': interpretation
        }

    def _analyze_competition_trend(self, products: List[Product]) -> Dict[str, Any]:
        """
        分析竞争趋势

        Args:
            products: 产品列表

        Returns:
            竞争趋势分析结果
        """
        if not products:
            return {
                'trend': 'unknown',
                'competition_level': 'unknown'
            }

        # 计算竞争指标
        # 1. 产品数量
        product_count = len(products)

        # 2. 平均评论数（反映市场成熟度）
        reviews = [p.reviews_count for p in products if p.reviews_count]
        avg_reviews = sum(reviews) / len(reviews) if reviews else 0

        # 3. 高评分产品占比
        high_rating_products = [p for p in products if p.rating and p.rating >= 4.0]
        high_rating_rate = len(high_rating_products) / len(products) * 100

        # 4. 品牌集中度
        brands = set(p.brand for p in products if p.brand)
        brand_diversity = len(brands) / len(products) * 100

        # 判断竞争趋势
        competition_score = 0

        if product_count > 100:
            competition_score += 2
        elif product_count > 50:
            competition_score += 1

        if avg_reviews > 500:
            competition_score += 2
        elif avg_reviews > 100:
            competition_score += 1

        if high_rating_rate > 60:
            competition_score += 1

        # 判断竞争水平
        if competition_score >= 4:
            competition_level = 'intense'
            trend = 'intensifying'
            interpretation = "竞争非常激烈，市场成熟度高，进入门槛较高"
        elif competition_score >= 2:
            competition_level = 'moderate'
            trend = 'stable'
            interpretation = "竞争适中，市场有一定机会，需要差异化策略"
        else:
            competition_level = 'low'
            trend = 'emerging'
            interpretation = "竞争较弱，市场处于早期阶段，存在较大机会"

        return {
            'trend': trend,
            'competition_level': competition_level,
            'product_count': product_count,
            'avg_reviews': round(avg_reviews, 2),
            'high_rating_rate': round(high_rating_rate, 2),
            'brand_diversity': round(brand_diversity, 2),
            'interpretation': interpretation
        }

    def _generate_forecast(
        self,
        products: List[Product],
        sellerspirit_data: SellerSpiritData = None
    ) -> Dict[str, Any]:
        """
        生成市场预测

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            市场预测结果
        """
        if not products:
            return {
                'outlook': 'unknown',
                'recommendations': []
            }

        # 综合各项趋势分析
        market_trend = self._analyze_market_trend(products, sellerspirit_data)
        new_product_trend = self._analyze_new_product_trend(products)
        price_trend = self._analyze_price_trend(products)
        competition_trend = self._analyze_competition_trend(products)

        # 生成市场展望
        trend_direction = market_trend['trend_direction']
        competition_level = competition_trend['competition_level']

        if trend_direction == 'growing' and competition_level == 'low':
            outlook = 'very_positive'
            outlook_text = "市场前景非常乐观，处于增长期且竞争较弱"
        elif trend_direction == 'growing':
            outlook = 'positive'
            outlook_text = "市场前景乐观，虽有竞争但仍有增长空间"
        elif trend_direction == 'stable' and competition_level != 'intense':
            outlook = 'neutral'
            outlook_text = "市场前景中性，适合稳健经营"
        elif trend_direction == 'declining':
            outlook = 'cautious'
            outlook_text = "市场前景谨慎，需要差异化策略"
        else:
            outlook = 'negative'
            outlook_text = "市场前景不佳，竞争激烈且增长放缓"

        # 生成建议
        recommendations = self._generate_recommendations(
            market_trend,
            new_product_trend,
            price_trend,
            competition_trend
        )

        return {
            'outlook': outlook,
            'outlook_text': outlook_text,
            'recommendations': recommendations,
            'key_insights': [
                f"市场趋势: {market_trend['trend_direction']}",
                f"竞争水平: {competition_trend['competition_level']}",
                f"新品活跃度: {new_product_trend['trend']}",
                f"价格趋势: {price_trend['trend']}"
            ]
        }

    def _generate_recommendations(
        self,
        market_trend: Dict[str, Any],
        new_product_trend: Dict[str, Any],
        price_trend: Dict[str, Any],
        competition_trend: Dict[str, Any]
    ) -> List[str]:
        """
        生成策略建议

        Args:
            market_trend: 市场趋势
            new_product_trend: 新品趋势
            price_trend: 价格趋势
            competition_trend: 竞争趋势

        Returns:
            建议列表
        """
        recommendations = []

        # 基于市场趋势的建议
        if market_trend['trend_direction'] == 'growing':
            recommendations.append("市场处于增长期，建议积极进入，抓住市场机会")
        elif market_trend['trend_direction'] == 'declining':
            recommendations.append("市场增长放缓，建议谨慎进入，或寻找细分市场机会")

        # 基于竞争趋势的建议
        if competition_trend['competition_level'] == 'intense':
            recommendations.append("竞争激烈，建议通过差异化、品牌化策略突围")
        elif competition_trend['competition_level'] == 'low':
            recommendations.append("竞争较弱，建议快速进入占领市场份额")

        # 基于新品趋势的建议
        if new_product_trend['new_product_rate'] > 15:
            recommendations.append("新品活跃，建议关注产品创新和快速迭代")

        # 基于价格趋势的建议
        if price_trend['trend'] == 'rising':
            recommendations.append("价格上升，市场接受度提高，可考虑中高端定位")
        elif price_trend['trend'] == 'falling':
            recommendations.append("价格下降，建议控制成本或提升产品价值")

        # 基于购买率和转化率的建议
        indicators = market_trend.get('indicators', {})
        purchase_rate = indicators.get('purchase_rate', 0)
        conversion_rate = indicators.get('conversion_rate', 0)

        if purchase_rate > 0:
            if purchase_rate > 15:
                recommendations.append(f"购买率高达{purchase_rate}%，市场需求旺盛，建议加大投入")
            elif purchase_rate < 5:
                recommendations.append(f"购买率仅{purchase_rate}%，需要优化产品吸引力和营销策略")

        if conversion_rate > 0:
            if conversion_rate > 15:
                recommendations.append(f"转化率高达{conversion_rate}%，产品竞争力强，建议扩大流量获取")
            elif conversion_rate < 5:
                recommendations.append(f"转化率仅{conversion_rate}%，需要优化产品详情页、价格或评价")

        return recommendations

    def _identify_new_products(
        self,
        products: List[Product],
        days_threshold: int = 180
    ) -> List[Product]:
        """
        识别新品

        Args:
            products: 产品列表
            days_threshold: 新品天数阈值

        Returns:
            新品列表
        """
        new_products = []
        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        for product in products:
            # 如果有上架日期，直接判断
            if product.available_date:
                try:
                    available_date = datetime.strptime(
                        product.available_date,
                        '%Y-%m-%d'
                    )
                    if available_date >= cutoff_date:
                        new_products.append(product)
                        continue
                except:
                    pass

            # 否则根据评论数判断（评论数少于50认为是新品）
            if product.reviews_count and product.reviews_count < 50:
                new_products.append(product)

        return new_products

    def get_trend_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成趋势分析摘要

        Args:
            analysis_result: 趋势分析结果

        Returns:
            摘要文本
        """
        market_trend = analysis_result.get('market_trend', {})
        new_product_trend = analysis_result.get('new_product_trend', {})
        price_trend = analysis_result.get('price_trend', {})
        competition_trend = analysis_result.get('competition_trend', {})
        forecast = analysis_result.get('forecast', {})

        # 获取指标
        indicators = market_trend.get('indicators', {})
        purchase_rate = indicators.get('purchase_rate', 0)
        conversion_rate = indicators.get('conversion_rate', 0)

        summary = f"""
趋势预测分析摘要
{'=' * 50}

市场趋势:
- 趋势方向: {market_trend.get('trend_direction', 'unknown')}
- 趋势强度: {market_trend.get('trend_strength', 0)}/100
- 解释: {market_trend.get('interpretation', 'N/A')}
"""

        # 添加购买率和转化率信息
        if purchase_rate > 0:
            summary += f"- 购买率: {purchase_rate}%\n"
        if conversion_rate > 0:
            summary += f"- 转化率: {conversion_rate}%\n"

        summary += f"""
新品趋势:
- 新品数量: {new_product_trend.get('new_product_count', 0)}
- 新品占比: {new_product_trend.get('new_product_rate', 0)}%
- 趋势: {new_product_trend.get('trend', 'unknown')}

价格趋势:
- 趋势: {price_trend.get('trend', 'unknown')}
- 平均价格: ${price_trend.get('avg_price', 0)}
- 价格波动性: {price_trend.get('price_volatility', 0)}%

竞争趋势:
- 竞争水平: {competition_trend.get('competition_level', 'unknown')}
- 趋势: {competition_trend.get('trend', 'unknown')}
- 产品数量: {competition_trend.get('product_count', 0)}

市场预测:
- 展望: {forecast.get('outlook', 'unknown')}
- {forecast.get('outlook_text', 'N/A')}

策略建议:
"""

        recommendations = forecast.get('recommendations', [])
        for i, rec in enumerate(recommendations, 1):
            summary += f"{i}. {rec}\n"

        return summary
