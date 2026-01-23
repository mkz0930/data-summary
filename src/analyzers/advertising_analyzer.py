"""
广告成本分析模块
分析PPC广告成本、ACoS、ROI等指标
基于4大AI选品方法论优化
继承 BaseAnalyzer 基类
"""

from typing import List, Dict, Any, Optional
import statistics
from dataclasses import dataclass

from src.database.models import Product, SellerSpiritData
from src.analyzers.base_analyzer import BaseAnalyzer


@dataclass
class AdvertisingMetrics:
    """广告指标数据类"""
    cpc_bid: float = 0.0  # 每次点击成本
    acos: float = 0.0  # 广告销售成本比
    tacos: float = 0.0  # 总广告销售成本比
    conversion_rate: float = 0.0  # 转化率
    click_rate: float = 0.0  # 点击率
    impressions: int = 0  # 曝光量
    clicks: int = 0  # 点击量
    ad_spend: float = 0.0  # 广告花费
    ad_sales: float = 0.0  # 广告销售额


class AdvertisingAnalyzer(BaseAnalyzer):
    """
    广告成本分析器

    继承 BaseAnalyzer，提供PPC广告成本、ACoS、ROI等分析功能。
    """

    def __init__(
        self,
        max_cpc: float = 1.5,  # 最大可接受CPC
        target_acos: float = 0.25,  # 目标ACoS
        max_acos: float = 0.35,  # 最大可接受ACoS
        min_conversion_rate: float = 0.10,  # 最小转化率
        target_roas: float = 4.0  # 目标ROAS (广告回报率)
    ):
        """
        初始化广告成本分析器

        Args:
            max_cpc: 最大可接受CPC出价
            target_acos: 目标ACoS
            max_acos: 最大可接受ACoS
            min_conversion_rate: 最小转化率要求
            target_roas: 目标广告回报率
        """
        super().__init__(name="AdvertisingAnalyzer")
        self.max_cpc = max_cpc
        self.target_acos = target_acos
        self.max_acos = max_acos
        self.min_conversion_rate = min_conversion_rate
        self.target_roas = target_roas

    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行广告成本分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据
            keyword: 关键词

        Returns:
            广告分析结果
        """
        if not products:
            return self._empty_result()

        self.log_info("开始广告成本分析...")

        # 1. 获取广告基础指标
        ad_metrics = self._get_advertising_metrics(sellerspirit_data)

        # 2. 分析CPC竞争情况
        cpc_analysis = self._analyze_cpc_competition(ad_metrics, products)

        # 3. 计算预期ACoS
        acos_analysis = self._analyze_acos(ad_metrics, products)

        # 4. 计算广告ROI
        roi_analysis = self._analyze_advertising_roi(ad_metrics, products)

        # 5. 分析关键词广告价值
        keyword_ad_value = self._analyze_keyword_ad_value(sellerspirit_data, keyword)

        # 6. 生成广告策略建议
        strategy = self._generate_advertising_strategy(
            cpc_analysis, acos_analysis, roi_analysis, keyword_ad_value
        )

        # 7. 计算广告可行性评分
        viability_score = self._calculate_ad_viability_score(
            cpc_analysis, acos_analysis, roi_analysis
        )

        return {
            'ad_metrics': ad_metrics.__dict__ if isinstance(ad_metrics, AdvertisingMetrics) else ad_metrics,
            'cpc_analysis': cpc_analysis,
            'acos_analysis': acos_analysis,
            'roi_analysis': roi_analysis,
            'keyword_ad_value': keyword_ad_value,
            'strategy': strategy,
            'viability_score': viability_score,
            'overall_recommendation': self._get_overall_recommendation(viability_score)
        }

    def _get_advertising_metrics(
        self,
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> AdvertisingMetrics:
        """
        获取广告基础指标

        Args:
            sellerspirit_data: 卖家精灵数据

        Returns:
            广告指标
        """
        metrics = AdvertisingMetrics()

        if sellerspirit_data:
            metrics.cpc_bid = sellerspirit_data.cpc_bid or 0.0
            metrics.acos = sellerspirit_data.acos_estimate or 0.0
            metrics.conversion_rate = sellerspirit_data.conversion_rate or 0.0
            metrics.click_rate = sellerspirit_data.click_rate or 0.0

            # 估算曝光和点击
            if sellerspirit_data.monthly_searches:
                # 假设广告占搜索量的30%曝光
                metrics.impressions = int(sellerspirit_data.monthly_searches * 0.3)
                # 基于点击率计算点击量
                if metrics.click_rate:
                    metrics.clicks = int(metrics.impressions * metrics.click_rate)

        return metrics

    def _analyze_cpc_competition(
        self,
        ad_metrics: AdvertisingMetrics,
        products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析CPC竞争情况

        Args:
            ad_metrics: 广告指标
            products: 产品列表

        Returns:
            CPC分析结果
        """
        cpc = ad_metrics.cpc_bid or 1.0

        # CPC等级评估
        if cpc < 0.5:
            cpc_level = 'very_low'
            cpc_desc = '非常低 - 广告成本极具优势'
        elif cpc < 0.8:
            cpc_level = 'low'
            cpc_desc = '较低 - 广告成本有优势'
        elif cpc < 1.2:
            cpc_level = 'moderate'
            cpc_desc = '适中 - 广告成本可接受'
        elif cpc < 1.5:
            cpc_level = 'high'
            cpc_desc = '较高 - 需要优化广告策略'
        else:
            cpc_level = 'very_high'
            cpc_desc = '很高 - 广告成本压力大'

        # 计算相对于产品价格的CPC比例
        prices = [p.price for p in products if p.price]
        avg_price = statistics.mean(prices) if prices else 30.0
        cpc_to_price_ratio = cpc / avg_price if avg_price > 0 else 0

        # 估算每单广告成本 (假设10%转化率)
        conversion_rate = ad_metrics.conversion_rate or 0.10
        cost_per_order = cpc / conversion_rate if conversion_rate > 0 else cpc * 10

        return {
            'cpc_bid': round(cpc, 2),
            'cpc_level': cpc_level,
            'cpc_desc': cpc_desc,
            'cpc_to_price_ratio': round(cpc_to_price_ratio * 100, 2),
            'avg_product_price': round(avg_price, 2),
            'cost_per_order': round(cost_per_order, 2),
            'meets_threshold': cpc <= self.max_cpc,
            'competitive_cpc': round(cpc * 0.8, 2),  # 建议竞争性出价
            'conservative_cpc': round(cpc * 0.6, 2)  # 保守出价
        }

    def _analyze_acos(
        self,
        ad_metrics: AdvertisingMetrics,
        products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析ACoS (广告销售成本比)

        Args:
            ad_metrics: 广告指标
            products: 产品列表

        Returns:
            ACoS分析结果
        """
        acos = ad_metrics.acos or 0.25

        # ACoS等级评估
        if acos < 0.15:
            acos_level = 'excellent'
            acos_desc = '优秀 - 广告效率极高'
        elif acos < 0.20:
            acos_level = 'good'
            acos_desc = '良好 - 广告效率较高'
        elif acos < 0.25:
            acos_level = 'acceptable'
            acos_desc = '可接受 - 广告效率正常'
        elif acos < 0.35:
            acos_level = 'high'
            acos_desc = '较高 - 需要优化广告'
        else:
            acos_level = 'very_high'
            acos_desc = '很高 - 广告可能亏损'

        # 计算盈亏平衡ACoS
        # 假设毛利率35%，则盈亏平衡ACoS约为35%
        breakeven_acos = 0.35

        # 计算各价格段的预期ACoS
        prices = [p.price for p in products if p.price]
        acos_by_price = []
        for price in prices[:20]:
            # 估算该价格下的ACoS
            estimated_acos = ad_metrics.cpc_bid / (price * (ad_metrics.conversion_rate or 0.10)) if price > 0 else 0
            acos_by_price.append({
                'price': price,
                'estimated_acos': round(estimated_acos * 100, 2),
                'profitable': estimated_acos < breakeven_acos
            })

        profitable_count = sum(1 for a in acos_by_price if a['profitable'])

        return {
            'current_acos': round(acos * 100, 2),
            'acos_level': acos_level,
            'acos_desc': acos_desc,
            'target_acos': round(self.target_acos * 100, 2),
            'breakeven_acos': round(breakeven_acos * 100, 2),
            'meets_target': acos <= self.target_acos,
            'meets_breakeven': acos <= breakeven_acos,
            'acos_by_price': acos_by_price[:10],
            'profitable_price_count': profitable_count,
            'profitable_rate': round(profitable_count / len(acos_by_price) * 100, 2) if acos_by_price else 0
        }

    def _analyze_advertising_roi(
        self,
        ad_metrics: AdvertisingMetrics,
        products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析广告ROI

        Args:
            ad_metrics: 广告指标
            products: 产品列表

        Returns:
            ROI分析结果
        """
        acos = ad_metrics.acos or 0.25

        # 计算ROAS (广告支出回报率) = 1 / ACoS
        roas = 1 / acos if acos > 0 else 0

        # ROAS等级评估
        if roas >= 5:
            roas_level = 'excellent'
            roas_desc = '优秀 - 每$1广告带来$5+销售'
        elif roas >= 4:
            roas_level = 'good'
            roas_desc = '良好 - 每$1广告带来$4+销售'
        elif roas >= 3:
            roas_level = 'acceptable'
            roas_desc = '可接受 - 每$1广告带来$3+销售'
        elif roas >= 2:
            roas_level = 'low'
            roas_desc = '较低 - 广告效率需提升'
        else:
            roas_level = 'poor'
            roas_desc = '较差 - 广告可能亏损'

        # 计算预期月度广告投入和回报
        prices = [p.price for p in products if p.price]
        avg_price = statistics.mean(prices) if prices else 30.0

        # 假设月销100单的广告投入
        monthly_sales_target = 100
        monthly_ad_sales = monthly_sales_target * avg_price
        monthly_ad_spend = monthly_ad_sales * acos
        monthly_ad_profit = monthly_ad_sales * 0.35 - monthly_ad_spend  # 假设35%毛利

        return {
            'roas': round(roas, 2),
            'roas_level': roas_level,
            'roas_desc': roas_desc,
            'target_roas': self.target_roas,
            'meets_target': roas >= self.target_roas,
            'monthly_projection': {
                'sales_target': monthly_sales_target,
                'avg_price': round(avg_price, 2),
                'ad_sales': round(monthly_ad_sales, 2),
                'ad_spend': round(monthly_ad_spend, 2),
                'ad_profit': round(monthly_ad_profit, 2),
                'profitable': monthly_ad_profit > 0
            }
        }

    def _analyze_keyword_ad_value(
        self,
        sellerspirit_data: Optional[SellerSpiritData] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析关键词广告价值

        Args:
            sellerspirit_data: 卖家精灵数据
            keyword: 关键词

        Returns:
            关键词广告价值分析
        """
        if not sellerspirit_data:
            return {
                'keyword': keyword or '',
                'ad_value_score': 50,
                'recommendation': '无数据，建议进一步调研'
            }

        # 计算关键词广告价值分数 (0-100)
        score = 0

        # 1. 搜索量评分 (30分)
        searches = sellerspirit_data.monthly_searches or 0
        if searches >= 50000:
            score += 30
        elif searches >= 20000:
            score += 25
        elif searches >= 10000:
            score += 20
        elif searches >= 5000:
            score += 15
        else:
            score += 8

        # 2. 转化率评分 (25分)
        conversion = sellerspirit_data.conversion_rate or 0
        if conversion >= 0.15:
            score += 25
        elif conversion >= 0.10:
            score += 20
        elif conversion >= 0.08:
            score += 15
        elif conversion >= 0.05:
            score += 10
        else:
            score += 5

        # 3. CPC评分 (25分) - CPC越低越好
        cpc = sellerspirit_data.cpc_bid or 1.0
        if cpc < 0.5:
            score += 25
        elif cpc < 0.8:
            score += 20
        elif cpc < 1.2:
            score += 15
        elif cpc < 1.5:
            score += 10
        else:
            score += 5

        # 4. 购买率评分 (20分)
        purchase_rate = sellerspirit_data.purchase_rate or 0
        if purchase_rate >= 0.05:
            score += 20
        elif purchase_rate >= 0.03:
            score += 15
        elif purchase_rate >= 0.02:
            score += 10
        else:
            score += 5

        # 评级
        if score >= 80:
            value_level = 'excellent'
            recommendation = '关键词广告价值极高，建议重点投放'
        elif score >= 65:
            value_level = 'good'
            recommendation = '关键词广告价值良好，建议积极投放'
        elif score >= 50:
            value_level = 'moderate'
            recommendation = '关键词广告价值一般，建议适度投放'
        elif score >= 35:
            value_level = 'low'
            recommendation = '关键词广告价值较低，建议谨慎投放'
        else:
            value_level = 'poor'
            recommendation = '关键词广告价值差，不建议投放'

        return {
            'keyword': keyword or sellerspirit_data.keyword or '',
            'monthly_searches': searches,
            'conversion_rate': round(conversion * 100, 2) if conversion else 0,
            'cpc_bid': round(cpc, 2),
            'purchase_rate': round(purchase_rate * 100, 2) if purchase_rate else 0,
            'ad_value_score': score,
            'value_level': value_level,
            'recommendation': recommendation
        }

    def _generate_advertising_strategy(
        self,
        cpc_analysis: Dict[str, Any],
        acos_analysis: Dict[str, Any],
        roi_analysis: Dict[str, Any],
        keyword_ad_value: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成广告策略建议

        Args:
            cpc_analysis: CPC分析结果
            acos_analysis: ACoS分析结果
            roi_analysis: ROI分析结果
            keyword_ad_value: 关键词广告价值

        Returns:
            广告策略建议
        """
        strategies = []
        tactics = []

        # 基于CPC的策略
        cpc_level = cpc_analysis.get('cpc_level', 'moderate')
        if cpc_level in ['very_low', 'low']:
            strategies.append("CPC成本低，可以积极投放自动广告和广泛匹配")
            tactics.append("使用自动广告快速获取流量")
            tactics.append("测试多个关键词组合")
        elif cpc_level == 'moderate':
            strategies.append("CPC成本适中，建议精准投放高转化关键词")
            tactics.append("优先投放精准匹配关键词")
            tactics.append("定期优化否定关键词")
        else:
            strategies.append("CPC成本较高，建议聚焦长尾关键词降低成本")
            tactics.append("重点投放长尾关键词")
            tactics.append("使用商品定向广告")
            tactics.append("控制每日预算，避免过度消耗")

        # 基于ACoS的策略
        acos_level = acos_analysis.get('acos_level', 'acceptable')
        if acos_level in ['excellent', 'good']:
            strategies.append("ACoS表现优秀，可以适当提高广告预算扩大规模")
            tactics.append("逐步提高出价获取更多曝光")
        elif acos_level == 'acceptable':
            strategies.append("ACoS在可接受范围，持续优化提升效率")
            tactics.append("A/B测试不同广告文案")
        else:
            strategies.append("ACoS偏高，需要优化广告结构和关键词")
            tactics.append("暂停低效关键词")
            tactics.append("优化产品listing提高转化率")
            tactics.append("考虑降低出价或暂停广告")

        # 基于ROI的策略
        if roi_analysis.get('meets_target', False):
            strategies.append("广告ROI达标，可以持续投入")
        else:
            strategies.append("广告ROI未达标，需要提升转化率或降低成本")
            tactics.append("优化产品主图和标题")
            tactics.append("调整价格策略")

        # 推荐的广告类型
        ad_types = []
        if cpc_level in ['very_low', 'low']:
            ad_types.extend(['Sponsored Products - 自动广告', 'Sponsored Products - 广泛匹配'])
        if keyword_ad_value.get('ad_value_score', 0) >= 60:
            ad_types.append('Sponsored Products - 精准匹配')
        if acos_level in ['excellent', 'good']:
            ad_types.append('Sponsored Brands')
        ad_types.append('Sponsored Display - 商品定向')

        return {
            'strategies': strategies,
            'tactics': tactics,
            'recommended_ad_types': ad_types,
            'budget_recommendation': self._get_budget_recommendation(cpc_analysis, roi_analysis),
            'bid_strategy': {
                'aggressive_bid': cpc_analysis.get('cpc_bid', 1.0),
                'competitive_bid': cpc_analysis.get('competitive_cpc', 0.8),
                'conservative_bid': cpc_analysis.get('conservative_cpc', 0.6)
            }
        }

    def _get_budget_recommendation(
        self,
        cpc_analysis: Dict[str, Any],
        roi_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成预算建议"""
        cpc = cpc_analysis.get('cpc_bid', 1.0)
        profitable = roi_analysis.get('monthly_projection', {}).get('profitable', False)

        if profitable and cpc < 1.0:
            daily_budget = 50
            monthly_budget = 1500
            recommendation = '广告环境良好，建议充足预算'
        elif profitable:
            daily_budget = 30
            monthly_budget = 900
            recommendation = '广告可盈利，建议适度预算'
        else:
            daily_budget = 15
            monthly_budget = 450
            recommendation = '广告盈利性待验证，建议保守预算'

        return {
            'daily_budget': daily_budget,
            'monthly_budget': monthly_budget,
            'recommendation': recommendation
        }

    def _calculate_ad_viability_score(
        self,
        cpc_analysis: Dict[str, Any],
        acos_analysis: Dict[str, Any],
        roi_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算广告可行性评分 (0-100)

        Args:
            cpc_analysis: CPC分析结果
            acos_analysis: ACoS分析结果
            roi_analysis: ROI分析结果

        Returns:
            可行性评分
        """
        score = 0
        breakdown = {}

        # 1. CPC评分 (35分)
        cpc = cpc_analysis.get('cpc_bid', 1.0)
        if cpc < 0.5:
            cpc_score = 35
        elif cpc < 0.8:
            cpc_score = 30
        elif cpc < 1.2:
            cpc_score = 22
        elif cpc < 1.5:
            cpc_score = 15
        else:
            cpc_score = 8
        score += cpc_score
        breakdown['cpc_score'] = cpc_score

        # 2. ACoS评分 (35分)
        acos = acos_analysis.get('current_acos', 25) / 100
        if acos < 0.15:
            acos_score = 35
        elif acos < 0.20:
            acos_score = 30
        elif acos < 0.25:
            acos_score = 22
        elif acos < 0.35:
            acos_score = 15
        else:
            acos_score = 5
        score += acos_score
        breakdown['acos_score'] = acos_score

        # 3. ROI评分 (30分)
        roas = roi_analysis.get('roas', 3)
        if roas >= 5:
            roi_score = 30
        elif roas >= 4:
            roi_score = 25
        elif roas >= 3:
            roi_score = 18
        elif roas >= 2:
            roi_score = 10
        else:
            roi_score = 5
        score += roi_score
        breakdown['roi_score'] = roi_score

        # 评级
        if score >= 80:
            grade = 'A'
            grade_desc = '广告环境优秀'
        elif score >= 65:
            grade = 'B'
            grade_desc = '广告环境良好'
        elif score >= 50:
            grade = 'C'
            grade_desc = '广告环境一般'
        elif score >= 35:
            grade = 'D'
            grade_desc = '广告环境较差'
        else:
            grade = 'F'
            grade_desc = '不适合广告投放'

        return {
            'total_score': score,
            'grade': grade,
            'grade_desc': grade_desc,
            'breakdown': breakdown
        }

    def _get_overall_recommendation(
        self,
        viability_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成总体建议"""
        grade = viability_score.get('grade', 'C')
        score = viability_score.get('total_score', 50)

        if grade == 'A':
            return {
                'action': '积极投放',
                'confidence': '高',
                'summary': '广告环境优秀，建议积极投放PPC广告，可以较高预算快速获取市场份额',
                'priority': 1
            }
        elif grade == 'B':
            return {
                'action': '适度投放',
                'confidence': '中高',
                'summary': '广告环境良好，建议适度投放广告，重点优化高转化关键词',
                'priority': 2
            }
        elif grade == 'C':
            return {
                'action': '谨慎投放',
                'confidence': '中',
                'summary': '广告环境一般，建议小规模测试，优化后再扩大投放',
                'priority': 3
            }
        elif grade == 'D':
            return {
                'action': '保守投放',
                'confidence': '低',
                'summary': '广告环境较差，建议以自然流量为主，仅小额测试广告',
                'priority': 4
            }
        else:
            return {
                'action': '暂不投放',
                'confidence': '很低',
                'summary': '广告成本过高，不建议投放PPC广告，专注自然流量和站外引流',
                'priority': 5
            }

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'ad_metrics': {},
            'cpc_analysis': {},
            'acos_analysis': {},
            'roi_analysis': {},
            'keyword_ad_value': {},
            'strategy': {},
            'viability_score': {
                'total_score': 0,
                'grade': 'N/A',
                'grade_desc': '无数据'
            },
            'overall_recommendation': {
                'action': '无法评估',
                'confidence': '无',
                'summary': '缺少必要数据，无法进行广告分析',
                'priority': 0
            }
        }

    def estimate_break_even_price(
        self,
        cpc: float,
        conversion_rate: float,
        target_margin: float = 0.35
    ) -> float:
        """
        估算盈亏平衡价格

        Args:
            cpc: 每次点击成本
            conversion_rate: 转化率
            target_margin: 目标毛利率

        Returns:
            盈亏平衡价格
        """
        if conversion_rate <= 0:
            return 0

        # 每单广告成本
        cost_per_order = cpc / conversion_rate

        # 盈亏平衡价格 = 广告成本 / 目标毛利率
        break_even_price = cost_per_order / target_margin

        return round(break_even_price, 2)

    def calculate_optimal_bid(
        self,
        target_acos: float,
        product_price: float,
        conversion_rate: float
    ) -> float:
        """
        计算最优出价

        Args:
            target_acos: 目标ACoS
            product_price: 产品价格
            conversion_rate: 转化率

        Returns:
            最优CPC出价
        """
        if conversion_rate <= 0:
            return 0

        # 最优CPC = 目标ACoS * 产品价格 * 转化率
        optimal_cpc = target_acos * product_price * conversion_rate

        return round(optimal_cpc, 2)
