"""
季节性分析模块
分析产品和关键词的季节性趋势
基于4大AI选品方法论优化
继承 BaseAnalyzer 基类
"""

from typing import List, Dict, Any, Optional
import statistics
import json
from datetime import datetime
from dataclasses import dataclass

from src.database.models import Product, SellerSpiritData
from src.analyzers.base_analyzer import BaseAnalyzer


@dataclass
class SeasonalityMetrics:
    """季节性指标数据类"""
    seasonality_index: float = 0.0  # 季节性指数 (0-100, 越低越稳定)
    peak_months: List[int] = None  # 旺季月份
    low_months: List[int] = None  # 淡季月份
    trend_direction: str = 'stable'  # 趋势方向: up/stable/down
    volatility: float = 0.0  # 波动率
    yoy_growth: float = 0.0  # 同比增长率

    def __post_init__(self):
        if self.peak_months is None:
            self.peak_months = []
        if self.low_months is None:
            self.low_months = []


class SeasonalityAnalyzer(BaseAnalyzer):
    """
    季节性分析器

    继承 BaseAnalyzer，提供季节性趋势分析、风险评估、入场时机建议等功能。
    """

    # 常见季节性品类
    SEASONAL_CATEGORIES = {
        'high_seasonal': [
            'christmas', 'halloween', 'easter', 'valentine',
            'summer', 'winter', 'spring', 'fall',
            'outdoor', 'pool', 'beach', 'snow', 'ski',
            'garden', 'patio', 'bbq', 'grill'
        ],
        'moderate_seasonal': [
            'school', 'back to school', 'graduation',
            'wedding', 'party', 'holiday',
            'fitness', 'diet', 'new year'
        ],
        'low_seasonal': [
            'kitchen', 'home', 'office', 'electronics',
            'pet', 'baby', 'health', 'beauty'
        ]
    }

    # 月份名称映射
    MONTH_NAMES = {
        1: '一月', 2: '二月', 3: '三月', 4: '四月',
        5: '五月', 6: '六月', 7: '七月', 8: '八月',
        9: '九月', 10: '十月', 11: '十一月', 12: '十二月'
    }

    def __init__(
        self,
        max_seasonality_index: float = 40.0,  # 最大可接受季节性指数
        min_stable_months: int = 8,  # 最少稳定月份数
        volatility_threshold: float = 0.3  # 波动率阈值
    ):
        """
        初始化季节性分析器

        Args:
            max_seasonality_index: 最大可接受季节性指数
            min_stable_months: 最少稳定月份数
            volatility_threshold: 波动率阈值
        """
        super().__init__(name="SeasonalityAnalyzer")
        self.max_seasonality_index = max_seasonality_index
        self.min_stable_months = min_stable_months
        self.volatility_threshold = volatility_threshold

    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行季节性分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据
            keyword: 关键词

        Returns:
            季节性分析结果
        """
        if not products and not sellerspirit_data:
            return self._empty_result()

        self.log_info("开始季节性分析...")

        # 1. 获取季节性基础指标
        metrics = self._get_seasonality_metrics(sellerspirit_data)

        # 2. 分析搜索趋势
        trend_analysis = self._analyze_search_trend(sellerspirit_data)

        # 3. 分析品类季节性
        category_seasonality = self._analyze_category_seasonality(products, keyword)

        # 4. 计算季节性风险
        risk_assessment = self._assess_seasonality_risk(metrics, trend_analysis, category_seasonality)

        # 5. 生成入场时机建议
        timing_recommendation = self._generate_timing_recommendation(
            metrics, trend_analysis, risk_assessment
        )

        # 6. 计算季节性评分
        seasonality_score = self._calculate_seasonality_score(
            metrics, trend_analysis, category_seasonality
        )

        return {
            'metrics': metrics.__dict__ if isinstance(metrics, SeasonalityMetrics) else metrics,
            'trend_analysis': trend_analysis,
            'category_seasonality': category_seasonality,
            'risk_assessment': risk_assessment,
            'timing_recommendation': timing_recommendation,
            'seasonality_score': seasonality_score,
            'overall_assessment': self._get_overall_assessment(seasonality_score)
        }

    def _get_seasonality_metrics(
        self,
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> SeasonalityMetrics:
        """
        获取季节性基础指标

        Args:
            sellerspirit_data: 卖家精灵数据

        Returns:
            季节性指标
        """
        metrics = SeasonalityMetrics()

        if sellerspirit_data and hasattr(sellerspirit_data, 'seasonality_index'):
            metrics.seasonality_index = sellerspirit_data.seasonality_index or 0.0
            metrics.trend_direction = sellerspirit_data.trend_direction or 'stable'

            # 解析搜索趋势数据
            if sellerspirit_data.search_trend_data:
                try:
                    trend_data = json.loads(sellerspirit_data.search_trend_data)
                    if isinstance(trend_data, list) and len(trend_data) >= 12:
                        # 计算波动率
                        avg = statistics.mean(trend_data)
                        if avg > 0:
                            std = statistics.stdev(trend_data)
                            metrics.volatility = std / avg

                        # 识别旺季和淡季
                        threshold_high = avg * 1.2
                        threshold_low = avg * 0.8

                        metrics.peak_months = [
                            i + 1 for i, v in enumerate(trend_data) if v >= threshold_high
                        ]
                        metrics.low_months = [
                            i + 1 for i, v in enumerate(trend_data) if v <= threshold_low
                        ]

                        # 计算同比增长 (假设数据是最近12个月)
                        if len(trend_data) >= 12:
                            recent_avg = statistics.mean(trend_data[-3:])
                            earlier_avg = statistics.mean(trend_data[:3])
                            if earlier_avg > 0:
                                metrics.yoy_growth = (recent_avg - earlier_avg) / earlier_avg

                except (json.JSONDecodeError, TypeError):
                    pass

        return metrics

    def _analyze_search_trend(
        self,
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        分析搜索趋势

        Args:
            sellerspirit_data: 卖家精灵数据

        Returns:
            搜索趋势分析
        """
        if not sellerspirit_data or not hasattr(sellerspirit_data, 'search_trend_data') or not sellerspirit_data.search_trend_data:
            return {
                'has_data': False,
                'trend_direction': 'unknown',
                'trend_strength': 0,
                'monthly_data': []
            }

        try:
            trend_data = json.loads(sellerspirit_data.search_trend_data)
            if not isinstance(trend_data, list) or len(trend_data) < 6:
                return {
                    'has_data': False,
                    'trend_direction': 'unknown',
                    'trend_strength': 0,
                    'monthly_data': []
                }

            # 计算趋势方向和强度
            avg = statistics.mean(trend_data)
            recent_avg = statistics.mean(trend_data[-3:]) if len(trend_data) >= 3 else avg
            earlier_avg = statistics.mean(trend_data[:3]) if len(trend_data) >= 3 else avg

            if earlier_avg > 0:
                change_rate = (recent_avg - earlier_avg) / earlier_avg
            else:
                change_rate = 0

            if change_rate > 0.15:
                trend_direction = 'up'
                trend_strength = min(100, int(change_rate * 200))
            elif change_rate < -0.15:
                trend_direction = 'down'
                trend_strength = min(100, int(abs(change_rate) * 200))
            else:
                trend_direction = 'stable'
                trend_strength = int((1 - abs(change_rate)) * 50)

            # 构建月度数据
            monthly_data = []
            for i, value in enumerate(trend_data):
                month_num = (datetime.now().month - len(trend_data) + i) % 12 + 1
                monthly_data.append({
                    'month': month_num,
                    'month_name': self.MONTH_NAMES.get(month_num, str(month_num)),
                    'search_volume': value,
                    'vs_avg': round((value / avg - 1) * 100, 2) if avg > 0 else 0
                })

            # 计算季节性模式
            max_value = max(trend_data)
            min_value = min(trend_data)
            seasonal_amplitude = (max_value - min_value) / avg if avg > 0 else 0

            return {
                'has_data': True,
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'change_rate': round(change_rate * 100, 2),
                'avg_search_volume': round(avg, 0),
                'max_search_volume': max_value,
                'min_search_volume': min_value,
                'seasonal_amplitude': round(seasonal_amplitude * 100, 2),
                'monthly_data': monthly_data
            }

        except (json.JSONDecodeError, TypeError):
            return {
                'has_data': False,
                'trend_direction': 'unknown',
                'trend_strength': 0,
                'monthly_data': []
            }

    def _analyze_category_seasonality(
        self,
        products: List[Product],
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析品类季节性

        Args:
            products: 产品列表
            keyword: 关键词

        Returns:
            品类季节性分析
        """
        # 收集所有相关文本
        text_to_analyze = []
        if keyword:
            text_to_analyze.append(keyword.lower())

        if products:
            for product in products[:20]:
                if product.name:
                    text_to_analyze.append(product.name.lower())
                if product.category:
                    text_to_analyze.append(product.category.lower())

        combined_text = ' '.join(text_to_analyze)

        # 检测季节性关键词
        high_seasonal_matches = []
        moderate_seasonal_matches = []
        low_seasonal_matches = []

        for kw in self.SEASONAL_CATEGORIES['high_seasonal']:
            if kw in combined_text:
                high_seasonal_matches.append(kw)

        for kw in self.SEASONAL_CATEGORIES['moderate_seasonal']:
            if kw in combined_text:
                moderate_seasonal_matches.append(kw)

        for kw in self.SEASONAL_CATEGORIES['low_seasonal']:
            if kw in combined_text:
                low_seasonal_matches.append(kw)

        # 确定季节性等级
        if high_seasonal_matches:
            seasonality_level = 'high'
            seasonality_desc = '高季节性品类'
            estimated_index = 70
        elif moderate_seasonal_matches:
            seasonality_level = 'moderate'
            seasonality_desc = '中等季节性品类'
            estimated_index = 45
        elif low_seasonal_matches:
            seasonality_level = 'low'
            seasonality_desc = '低季节性品类'
            estimated_index = 20
        else:
            seasonality_level = 'unknown'
            seasonality_desc = '季节性未知'
            estimated_index = 35

        return {
            'seasonality_level': seasonality_level,
            'seasonality_desc': seasonality_desc,
            'estimated_index': estimated_index,
            'high_seasonal_keywords': high_seasonal_matches,
            'moderate_seasonal_keywords': moderate_seasonal_matches,
            'low_seasonal_keywords': low_seasonal_matches,
            'is_evergreen': seasonality_level == 'low' and not high_seasonal_matches
        }

    def _assess_seasonality_risk(
        self,
        metrics: SeasonalityMetrics,
        trend_analysis: Dict[str, Any],
        category_seasonality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估季节性风险

        Args:
            metrics: 季节性指标
            trend_analysis: 趋势分析
            category_seasonality: 品类季节性

        Returns:
            风险评估结果
        """
        risks = []
        risk_score = 0

        # 1. 季节性指数风险
        if metrics.seasonality_index > 60:
            risks.append({
                'type': '高季节性',
                'severity': 'high',
                'description': f'季节性指数{metrics.seasonality_index}，销量波动大'
            })
            risk_score += 30
        elif metrics.seasonality_index > 40:
            risks.append({
                'type': '中等季节性',
                'severity': 'medium',
                'description': f'季节性指数{metrics.seasonality_index}，有一定波动'
            })
            risk_score += 15

        # 2. 趋势下降风险
        if trend_analysis.get('trend_direction') == 'down':
            change_rate = abs(trend_analysis.get('change_rate', 0))
            if change_rate > 20:
                risks.append({
                    'type': '趋势下降',
                    'severity': 'high',
                    'description': f'搜索量下降{change_rate}%，市场可能萎缩'
                })
                risk_score += 25
            else:
                risks.append({
                    'type': '轻微下降',
                    'severity': 'medium',
                    'description': f'搜索量下降{change_rate}%'
                })
                risk_score += 10

        # 3. 波动率风险
        if metrics.volatility > 0.5:
            risks.append({
                'type': '高波动',
                'severity': 'high',
                'description': f'波动率{round(metrics.volatility * 100, 1)}%，库存管理难度大'
            })
            risk_score += 20
        elif metrics.volatility > 0.3:
            risks.append({
                'type': '中等波动',
                'severity': 'medium',
                'description': f'波动率{round(metrics.volatility * 100, 1)}%'
            })
            risk_score += 10

        # 4. 品类季节性风险
        if category_seasonality.get('seasonality_level') == 'high':
            risks.append({
                'type': '品类季节性',
                'severity': 'high',
                'description': '属于高季节性品类，需要精准把握入场时机'
            })
            risk_score += 20

        # 风险等级
        if risk_score >= 50:
            risk_level = 'high'
            risk_desc = '高风险 - 季节性波动大，需谨慎'
        elif risk_score >= 25:
            risk_level = 'medium'
            risk_desc = '中等风险 - 有一定季节性，需关注'
        else:
            risk_level = 'low'
            risk_desc = '低风险 - 季节性稳定'

        return {
            'risk_level': risk_level,
            'risk_desc': risk_desc,
            'risk_score': risk_score,
            'risks': risks,
            'mitigation_strategies': self._get_mitigation_strategies(risks)
        }

    def _get_mitigation_strategies(self, risks: List[Dict]) -> List[str]:
        """生成风险缓解策略"""
        strategies = []

        risk_types = [r['type'] for r in risks]

        if '高季节性' in risk_types or '品类季节性' in risk_types:
            strategies.append("提前2-3个月备货，避免旺季断货")
            strategies.append("淡季时降低库存，减少仓储成本")
            strategies.append("考虑开发互补季节性产品平衡全年销量")

        if '趋势下降' in risk_types:
            strategies.append("分析下降原因，是否有替代品出现")
            strategies.append("考虑产品升级或差异化")
            strategies.append("控制库存深度，避免积压")

        if '高波动' in risk_types or '中等波动' in risk_types:
            strategies.append("使用FBA库存管理工具预测需求")
            strategies.append("建立安全库存缓冲")
            strategies.append("与供应商建立灵活补货机制")

        if not strategies:
            strategies.append("保持正常库存周转")
            strategies.append("定期监控市场趋势变化")

        return strategies

    def _generate_timing_recommendation(
        self,
        metrics: SeasonalityMetrics,
        trend_analysis: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成入场时机建议

        Args:
            metrics: 季节性指标
            trend_analysis: 趋势分析
            risk_assessment: 风险评估

        Returns:
            入场时机建议
        """
        current_month = datetime.now().month

        # 判断当前是否是好的入场时机
        is_peak_season = current_month in metrics.peak_months
        is_low_season = current_month in metrics.low_months
        trend_up = trend_analysis.get('trend_direction') == 'up'
        trend_down = trend_analysis.get('trend_direction') == 'down'

        # 入场时机评估
        if is_low_season and not trend_down:
            timing_score = 85
            timing_desc = '当前是淡季，适合入场准备'
            recommendation = '现在入场可以在旺季前完成产品优化和排名积累'
        elif is_peak_season:
            timing_score = 40
            timing_desc = '当前是旺季，入场风险较高'
            recommendation = '建议等待旺季结束后再入场，避免高竞争和高广告成本'
        elif trend_up:
            timing_score = 75
            timing_desc = '市场趋势向上，入场时机良好'
            recommendation = '趋势向好，建议尽快入场抓住增长机会'
        elif trend_down:
            timing_score = 35
            timing_desc = '市场趋势下降，入场需谨慎'
            recommendation = '建议观望或寻找其他机会'
        else:
            timing_score = 60
            timing_desc = '市场相对稳定'
            recommendation = '可以入场，但需要差异化策略'

        # 最佳入场月份建议
        best_entry_months = []
        if metrics.peak_months:
            # 旺季前2-3个月入场
            for peak in metrics.peak_months:
                entry_month = (peak - 3) % 12 + 1
                if entry_month not in best_entry_months:
                    best_entry_months.append(entry_month)

        if not best_entry_months:
            # 默认建议
            best_entry_months = [1, 2, 8, 9]  # 年初和秋季

        return {
            'current_month': current_month,
            'current_month_name': self.MONTH_NAMES.get(current_month, str(current_month)),
            'is_peak_season': is_peak_season,
            'is_low_season': is_low_season,
            'timing_score': timing_score,
            'timing_desc': timing_desc,
            'recommendation': recommendation,
            'best_entry_months': best_entry_months,
            'best_entry_months_names': [self.MONTH_NAMES.get(m, str(m)) for m in best_entry_months],
            'peak_months': metrics.peak_months,
            'peak_months_names': [self.MONTH_NAMES.get(m, str(m)) for m in metrics.peak_months],
            'low_months': metrics.low_months,
            'low_months_names': [self.MONTH_NAMES.get(m, str(m)) for m in metrics.low_months]
        }

    def _calculate_seasonality_score(
        self,
        metrics: SeasonalityMetrics,
        trend_analysis: Dict[str, Any],
        category_seasonality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算季节性评分 (0-100, 越高越稳定)

        Args:
            metrics: 季节性指标
            trend_analysis: 趋势分析
            category_seasonality: 品类季节性

        Returns:
            季节性评分
        """
        score = 100
        breakdown = {}

        # 1. 季节性指数扣分 (最多扣40分)
        seasonality_deduction = min(40, metrics.seasonality_index * 0.6)
        score -= seasonality_deduction
        breakdown['seasonality_index_impact'] = -round(seasonality_deduction, 2)

        # 2. 波动率扣分 (最多扣25分)
        volatility_deduction = min(25, metrics.volatility * 50)
        score -= volatility_deduction
        breakdown['volatility_impact'] = -round(volatility_deduction, 2)

        # 3. 趋势方向影响 (最多扣/加15分)
        if trend_analysis.get('trend_direction') == 'up':
            trend_bonus = 10
            score += trend_bonus
            breakdown['trend_impact'] = trend_bonus
        elif trend_analysis.get('trend_direction') == 'down':
            trend_deduction = 15
            score -= trend_deduction
            breakdown['trend_impact'] = -trend_deduction
        else:
            breakdown['trend_impact'] = 0

        # 4. 品类季节性影响 (最多扣20分)
        category_level = category_seasonality.get('seasonality_level', 'unknown')
        if category_level == 'high':
            category_deduction = 20
        elif category_level == 'moderate':
            category_deduction = 10
        else:
            category_deduction = 0
        score -= category_deduction
        breakdown['category_impact'] = -category_deduction

        # 确保分数在0-100范围内
        score = max(0, min(100, score))

        # 评级
        if score >= 80:
            grade = 'A'
            grade_desc = '非常稳定 - 全年销量均衡'
        elif score >= 65:
            grade = 'B'
            grade_desc = '较稳定 - 轻微季节波动'
        elif score >= 50:
            grade = 'C'
            grade_desc = '一般 - 有明显季节性'
        elif score >= 35:
            grade = 'D'
            grade_desc = '不稳定 - 季节性较强'
        else:
            grade = 'F'
            grade_desc = '高度季节性 - 需特别注意'

        return {
            'total_score': round(score, 2),
            'grade': grade,
            'grade_desc': grade_desc,
            'breakdown': breakdown,
            'is_evergreen': score >= 70 and category_seasonality.get('is_evergreen', False)
        }

    def _get_overall_assessment(
        self,
        seasonality_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成总体评估"""
        grade = seasonality_score.get('grade', 'C')
        score = seasonality_score.get('total_score', 50)
        is_evergreen = seasonality_score.get('is_evergreen', False)

        if is_evergreen:
            return {
                'assessment': '常青产品',
                'confidence': '高',
                'summary': '该产品/市场季节性低，全年销量稳定，适合长期经营',
                'inventory_strategy': '保持稳定库存，按正常周转补货',
                'priority': 1
            }
        elif grade in ['A', 'B']:
            return {
                'assessment': '季节性可控',
                'confidence': '中高',
                'summary': '季节性波动在可接受范围内，可以正常经营',
                'inventory_strategy': '根据历史数据预测需求，适度调整库存',
                'priority': 2
            }
        elif grade == 'C':
            return {
                'assessment': '需关注季节性',
                'confidence': '中',
                'summary': '存在明显季节性，需要制定相应的库存和营销策略',
                'inventory_strategy': '旺季前增加库存，淡季控制库存深度',
                'priority': 3
            }
        elif grade == 'D':
            return {
                'assessment': '高季节性风险',
                'confidence': '低',
                'summary': '季节性较强，需要精准把握入场时机和库存管理',
                'inventory_strategy': '严格控制库存，避免淡季积压',
                'priority': 4
            }
        else:
            return {
                'assessment': '极高季节性',
                'confidence': '很低',
                'summary': '季节性极强，仅适合有经验的卖家操作',
                'inventory_strategy': '采用预售或小批量多频次补货策略',
                'priority': 5
            }

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'metrics': {},
            'trend_analysis': {
                'has_data': False,
                'trend_direction': 'unknown'
            },
            'category_seasonality': {
                'seasonality_level': 'unknown',
                'is_evergreen': False
            },
            'risk_assessment': {
                'risk_level': 'unknown',
                'risk_score': 0,
                'risks': []
            },
            'timing_recommendation': {
                'timing_score': 50,
                'recommendation': '无数据，无法评估'
            },
            'seasonality_score': {
                'total_score': 50,
                'grade': 'N/A',
                'grade_desc': '无数据'
            },
            'overall_assessment': {
                'assessment': '无法评估',
                'confidence': '无',
                'summary': '缺少必要数据，无法进行季节性分析',
                'priority': 0
            }
        }

    def get_inventory_recommendation(
        self,
        seasonality_score: Dict[str, Any],
        current_month: int = None,
        peak_months: List[int] = None
    ) -> Dict[str, Any]:
        """
        获取库存建议

        Args:
            seasonality_score: 季节性评分
            current_month: 当前月份
            peak_months: 旺季月份

        Returns:
            库存建议
        """
        if current_month is None:
            current_month = datetime.now().month

        if peak_months is None:
            peak_months = []

        grade = seasonality_score.get('grade', 'C')

        # 计算距离旺季的月份数
        months_to_peak = float('inf')
        for peak in peak_months:
            diff = (peak - current_month) % 12
            if diff < months_to_peak:
                months_to_peak = diff

        # 基础库存周数
        if grade in ['A', 'B']:
            base_weeks = 6
        elif grade == 'C':
            base_weeks = 4
        else:
            base_weeks = 3

        # 根据距离旺季调整
        if months_to_peak <= 2 and peak_months:
            inventory_multiplier = 1.5
            recommendation = '旺季临近，建议增加库存'
        elif months_to_peak <= 4 and peak_months:
            inventory_multiplier = 1.2
            recommendation = '准备旺季，适度增加库存'
        else:
            inventory_multiplier = 1.0
            recommendation = '保持正常库存水平'

        return {
            'base_inventory_weeks': base_weeks,
            'inventory_multiplier': inventory_multiplier,
            'recommended_weeks': round(base_weeks * inventory_multiplier, 1),
            'recommendation': recommendation,
            'months_to_peak': months_to_peak if months_to_peak != float('inf') else None
        }
