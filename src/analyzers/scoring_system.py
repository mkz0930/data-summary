"""
统一评分系统模块
整合多维度分析结果，生成综合评分和建议
基于4大AI选品方法论优化
继承 BaseAnalyzer 基类
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.database.models import Product, SellerSpiritData
from src.analyzers.base_analyzer import BaseAnalyzer


def _get_sellerspirit_attr(data, attr: str, default=None):
    """
    安全获取卖家精灵数据属性，兼容字典和对象两种类型

    Args:
        data: SellerSpiritData 对象或字典
        attr: 属性名
        default: 默认值

    Returns:
        属性值或默认值
    """
    if data is None:
        return default
    if isinstance(data, dict):
        return data.get(attr, default)
    return getattr(data, attr, default)


class ScoreGrade(Enum):
    """评分等级"""
    A_PLUS = ('A+', 90, 100, '极佳机会')
    A = ('A', 80, 89, '优秀机会')
    B_PLUS = ('B+', 70, 79, '良好机会')
    B = ('B', 60, 69, '较好机会')
    C = ('C', 50, 59, '一般机会')
    D = ('D', 35, 49, '机会有限')
    F = ('F', 0, 34, '不建议进入')

    def __init__(self, grade: str, min_score: int, max_score: int, desc: str):
        self.grade = grade
        self.min_score = min_score
        self.max_score = max_score
        self.desc = desc

    @classmethod
    def from_score(cls, score: float) -> 'ScoreGrade':
        """根据分数获取等级"""
        for grade in cls:
            if grade.min_score <= score <= grade.max_score:
                return grade
        return cls.F


@dataclass
class ScoreDimension:
    """评分维度"""
    name: str
    weight: float
    score: float = 0.0
    max_score: float = 100.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """加权分数"""
        return self.score * self.weight

    @property
    def normalized_score(self) -> float:
        """归一化分数 (0-100)"""
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0


@dataclass
class ComprehensiveScore:
    """综合评分结果"""
    total_score: float
    grade: ScoreGrade
    dimensions: List[ScoreDimension]
    recommendations: List[str]
    action_items: List[str]
    confidence_level: str
    risk_factors: List[str]


class ScoringSystem(BaseAnalyzer):
    """
    统一评分系统

    继承 BaseAnalyzer，整合多维度分析结果，生成综合评分和建议。
    """

    # 默认权重配置
    DEFAULT_WEIGHTS = {
        'demand': 0.20,        # 市场需求
        'competition': 0.20,   # 竞争强度
        'profit': 0.20,        # 利润空间
        'barrier': 0.15,       # 进入门槛
        'seasonality': 0.10,   # 季节性
        'trend': 0.15          # 趋势方向
    }

    # 腰部蓝海专用权重
    WAIST_BLUE_OCEAN_WEIGHTS = {
        'demand': 0.18,
        'competition': 0.22,
        'profit': 0.22,
        'barrier': 0.13,
        'seasonality': 0.10,
        'trend': 0.15
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        use_waist_weights: bool = True
    ):
        """
        初始化评分系统

        Args:
            weights: 自定义权重配置
            use_waist_weights: 是否使用腰部蓝海专用权重
        """
        super().__init__(name="ScoringSystem")

        if weights:
            self.weights = weights
        elif use_waist_weights:
            self.weights = self.WAIST_BLUE_OCEAN_WEIGHTS
        else:
            self.weights = self.DEFAULT_WEIGHTS

        # 确保权重总和为1
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            self.log_warning(f"权重总和为{total_weight}，将进行归一化")
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        执行分析（实现基类抽象方法）

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            分析结果字典
        """
        # 此方法主要用于兼容基类接口
        # 实际评分通过 calculate_comprehensive_score 方法完成
        return {
            'message': '请使用 calculate_comprehensive_score 方法进行综合评分'
        }

    def calculate_comprehensive_score(
        self,
        blue_ocean_result: Dict[str, Any],
        seasonality_result: Optional[Dict[str, Any]] = None,
        sellerspirit_data: Optional[SellerSpiritData] = None,
        products: Optional[List[Product]] = None
    ) -> ComprehensiveScore:
        """
        计算综合评分

        Args:
            blue_ocean_result: 蓝海分析结果
            seasonality_result: 季节性分析结果
            sellerspirit_data: 卖家精灵数据
            products: 产品列表

        Returns:
            综合评分结果
        """
        self.log_info("开始计算综合评分...")

        dimensions = []

        # 1. 市场需求评分
        demand_dim = self._calculate_demand_score(blue_ocean_result, sellerspirit_data)
        dimensions.append(demand_dim)

        # 2. 竞争强度评分
        competition_dim = self._calculate_competition_score(blue_ocean_result)
        dimensions.append(competition_dim)

        # 3. 利润空间评分
        profit_dim = self._calculate_profit_score(blue_ocean_result)
        dimensions.append(profit_dim)

        # 4. 进入门槛评分
        barrier_dim = self._calculate_barrier_score(blue_ocean_result)
        dimensions.append(barrier_dim)

        # 5. 季节性评分
        seasonality_dim = self._calculate_seasonality_score(seasonality_result)
        dimensions.append(seasonality_dim)

        # 6. 趋势评分
        trend_dim = self._calculate_trend_score(seasonality_result, sellerspirit_data)
        dimensions.append(trend_dim)

        # 计算总分
        total_score = sum(dim.weighted_score for dim in dimensions)

        # 获取等级
        grade = ScoreGrade.from_score(total_score)

        # 生成建议
        recommendations, action_items = self._generate_recommendations(dimensions, grade)

        # 识别风险因素
        risk_factors = self._identify_risk_factors(dimensions)

        # 确定置信度
        confidence_level = self._determine_confidence_level(dimensions, sellerspirit_data)

        return ComprehensiveScore(
            total_score=round(total_score, 2),
            grade=grade,
            dimensions=dimensions,
            recommendations=recommendations,
            action_items=action_items,
            confidence_level=confidence_level,
            risk_factors=risk_factors
        )

    def _calculate_demand_score(
        self,
        blue_ocean_result: Dict[str, Any],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> ScoreDimension:
        """计算市场需求评分"""
        score = 0.0
        details = {}

        # 从卖家精灵数据获取搜索量
        monthly_searches = _get_sellerspirit_attr(sellerspirit_data, 'monthly_searches')
        if monthly_searches:
            searches = monthly_searches
            details['monthly_searches'] = searches

            # 腰部蓝海理想搜索量: 5000-50000
            if 5000 <= searches <= 12000:
                score = 100  # 最佳区间
            elif 12000 < searches <= 30000:
                score = 90
            elif 30000 < searches <= 50000:
                score = 80
            elif 3000 <= searches < 5000:
                score = 70
            elif searches > 50000:
                score = 65  # 搜索量大但竞争可能激烈
            elif 1000 <= searches < 3000:
                score = 50
            else:
                score = 30

            details['search_volume_status'] = self._get_search_volume_status(searches)
        else:
            # 从蓝海分析结果推断
            market_stats = blue_ocean_result.get('market_stats', {})
            avg_sales = market_stats.get('avg_sales_volume', 0)
            if avg_sales > 0:
                # 根据平均销量估算市场需求
                if avg_sales >= 1000:
                    score = 80
                elif avg_sales >= 500:
                    score = 65
                elif avg_sales >= 200:
                    score = 50
                else:
                    score = 35
                details['estimated_from_sales'] = True
                details['avg_sales_volume'] = avg_sales
            else:
                score = 50  # 无数据给中等分
                details['no_data'] = True

        return ScoreDimension(
            name='market_demand',
            weight=self.weights['demand'],
            score=score,
            details=details
        )

    def _get_search_volume_status(self, searches: int) -> str:
        """获取搜索量状态描述"""
        if searches >= 30000:
            return '高搜索量'
        elif searches >= 10000:
            return '中高搜索量'
        elif searches >= 5000:
            return '适中搜索量'
        elif searches >= 2000:
            return '中低搜索量'
        else:
            return '低搜索量'

    def _calculate_competition_score(
        self,
        blue_ocean_result: Dict[str, Any]
    ) -> ScoreDimension:
        """计算竞争强度评分 (竞争越低分数越高)"""
        score = 50.0
        details = {}

        market_competition = blue_ocean_result.get('market_competition', {})
        competition_index = market_competition.get('competition_index', 50)
        details['competition_index'] = competition_index

        # 竞争指数越低越好
        if competition_index <= 20:
            score = 100
        elif competition_index <= 30:
            score = 90
        elif competition_index <= 40:
            score = 80
        elif competition_index <= 50:
            score = 70
        elif competition_index <= 60:
            score = 55
        elif competition_index <= 70:
            score = 40
        else:
            score = 25

        # 弱listing加分
        weak_listing_analysis = blue_ocean_result.get('weak_listing_analysis', {})
        top_10_weak_count = weak_listing_analysis.get('top_10_weak_count', 0)
        details['top_10_weak_count'] = top_10_weak_count

        if top_10_weak_count >= 4:
            score = min(100, score + 10)
            details['weak_listing_bonus'] = 10
        elif top_10_weak_count >= 2:
            score = min(100, score + 5)
            details['weak_listing_bonus'] = 5

        # 品牌集中度
        brand_concentration = market_competition.get('brand_concentration', 0)
        details['brand_concentration'] = brand_concentration
        if brand_concentration > 50:
            score = max(0, score - 10)
            details['brand_penalty'] = -10

        return ScoreDimension(
            name='competition',
            weight=self.weights['competition'],
            score=score,
            details=details
        )

    def _calculate_profit_score(
        self,
        blue_ocean_result: Dict[str, Any]
    ) -> ScoreDimension:
        """计算利润空间评分"""
        score = 50.0
        details = {}

        profit_analysis = blue_ocean_result.get('profit_analysis', {})
        avg_margin = profit_analysis.get('avg_gross_margin', 0)
        details['avg_gross_margin'] = avg_margin

        # 毛利率评分 (目标≥35%)
        if avg_margin >= 45:
            score = 100
        elif avg_margin >= 40:
            score = 90
        elif avg_margin >= 35:
            score = 80
        elif avg_margin >= 30:
            score = 65
        elif avg_margin >= 25:
            score = 50
        elif avg_margin >= 20:
            score = 35
        else:
            score = 20

        # 广告后利润调整
        advertising_analysis = blue_ocean_result.get('advertising_analysis', {})
        profitable_rate = advertising_analysis.get('profitable_rate', 50)
        details['profitable_rate_after_ads'] = profitable_rate

        if profitable_rate < 30:
            score = max(0, score - 20)
            details['ad_profit_penalty'] = -20
        elif profitable_rate < 50:
            score = max(0, score - 10)
            details['ad_profit_penalty'] = -10
        elif profitable_rate >= 80:
            score = min(100, score + 5)
            details['ad_profit_bonus'] = 5

        return ScoreDimension(
            name='profit',
            weight=self.weights['profit'],
            score=score,
            details=details
        )

    def _calculate_barrier_score(
        self,
        blue_ocean_result: Dict[str, Any]
    ) -> ScoreDimension:
        """计算进入门槛评分 (门槛越低分数越高)"""
        score = 70.0
        details = {}

        market_competition = blue_ocean_result.get('market_competition', {})

        # 品牌集中度
        brand_concentration = market_competition.get('brand_concentration', 0)
        details['brand_concentration'] = brand_concentration

        if brand_concentration <= 10:
            score = 100
        elif brand_concentration <= 20:
            score = 90
        elif brand_concentration <= 30:
            score = 80
        elif brand_concentration <= 40:
            score = 70
        elif brand_concentration <= 50:
            score = 55
        elif brand_concentration <= 60:
            score = 40
        else:
            score = 25

        # CPC成本
        advertising_analysis = blue_ocean_result.get('advertising_analysis', {})
        cpc = advertising_analysis.get('cpc_bid', 1.0)
        details['cpc_bid'] = cpc

        if cpc > 2.0:
            score = max(0, score - 15)
            details['cpc_penalty'] = -15
        elif cpc > 1.5:
            score = max(0, score - 10)
            details['cpc_penalty'] = -10
        elif cpc < 0.8:
            score = min(100, score + 5)
            details['cpc_bonus'] = 5

        # 平均评论数 (评论数越高门槛越高)
        market_stats = blue_ocean_result.get('market_stats', {})
        avg_reviews = market_stats.get('avg_reviews', 0)
        details['avg_reviews'] = avg_reviews

        if avg_reviews > 1000:
            score = max(0, score - 15)
            details['review_barrier_penalty'] = -15
        elif avg_reviews > 500:
            score = max(0, score - 10)
            details['review_barrier_penalty'] = -10
        elif avg_reviews < 100:
            score = min(100, score + 5)
            details['review_barrier_bonus'] = 5

        return ScoreDimension(
            name='barrier',
            weight=self.weights['barrier'],
            score=score,
            details=details
        )

    def _calculate_seasonality_score(
        self,
        seasonality_result: Optional[Dict[str, Any]] = None
    ) -> ScoreDimension:
        """计算季节性评分 (越稳定分数越高)"""
        score = 70.0
        details = {}

        if not seasonality_result:
            details['no_data'] = True
            return ScoreDimension(
                name='seasonality',
                weight=self.weights['seasonality'],
                score=score,
                details=details
            )

        seasonality_score = seasonality_result.get('seasonality_score', {})
        total_score = seasonality_score.get('total_score', 70)
        details['seasonality_stability_score'] = total_score

        # 直接使用季节性分析的分数
        score = total_score

        # 是否常青产品
        is_evergreen = seasonality_score.get('is_evergreen', False)
        details['is_evergreen'] = is_evergreen
        if is_evergreen:
            score = min(100, score + 10)
            details['evergreen_bonus'] = 10

        # 风险等级
        risk_assessment = seasonality_result.get('risk_assessment', {})
        risk_level = risk_assessment.get('risk_level', 'medium')
        details['risk_level'] = risk_level

        if risk_level == 'high':
            score = max(0, score - 15)
            details['risk_penalty'] = -15
        elif risk_level == 'low':
            score = min(100, score + 5)
            details['risk_bonus'] = 5

        return ScoreDimension(
            name='seasonality',
            weight=self.weights['seasonality'],
            score=score,
            details=details
        )

    def _calculate_trend_score(
        self,
        seasonality_result: Optional[Dict[str, Any]] = None,
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> ScoreDimension:
        """计算趋势评分"""
        score = 60.0
        details = {}

        trend_direction = 'stable'

        # 优先从卖家精灵数据获取
        sp_trend_direction = _get_sellerspirit_attr(sellerspirit_data, 'trend_direction')
        if sp_trend_direction:
            trend_direction = sp_trend_direction
            details['source'] = 'sellerspirit'
        elif seasonality_result:
            trend_analysis = seasonality_result.get('trend_analysis', {})
            trend_direction = trend_analysis.get('trend_direction', 'stable')
            details['source'] = 'seasonality_analysis'

        details['trend_direction'] = trend_direction

        # 趋势评分
        if trend_direction == 'up':
            score = 90
            details['trend_desc'] = '上升趋势'
        elif trend_direction == 'stable':
            score = 70
            details['trend_desc'] = '稳定趋势'
        elif trend_direction == 'down':
            score = 35
            details['trend_desc'] = '下降趋势'
        else:
            score = 60
            details['trend_desc'] = '趋势未知'

        # 趋势强度调整
        if seasonality_result:
            trend_analysis = seasonality_result.get('trend_analysis', {})
            trend_strength = trend_analysis.get('trend_strength', 50)
            details['trend_strength'] = trend_strength

            if trend_direction == 'up' and trend_strength > 70:
                score = min(100, score + 10)
                details['strength_bonus'] = 10
            elif trend_direction == 'down' and trend_strength > 70:
                score = max(0, score - 10)
                details['strength_penalty'] = -10

        return ScoreDimension(
            name='trend',
            weight=self.weights['trend'],
            score=score,
            details=details
        )

    def _generate_recommendations(
        self,
        dimensions: List[ScoreDimension],
        grade: ScoreGrade
    ) -> tuple:
        """生成建议和行动项"""
        recommendations = []
        action_items = []

        # 基于总体等级的建议
        if grade in [ScoreGrade.A_PLUS, ScoreGrade.A]:
            recommendations.append("该市场具有优秀的蓝海机会，强烈建议进入")
            action_items.append("立即开始产品调研和供应商对接")
            action_items.append("准备首批测试订单")
        elif grade in [ScoreGrade.B_PLUS, ScoreGrade.B]:
            recommendations.append("该市场具有良好的机会，建议积极进入")
            action_items.append("深入分析竞品，制定差异化策略")
            action_items.append("评估供应链能力和资金需求")
        elif grade == ScoreGrade.C:
            recommendations.append("该市场机会一般，需要精准定位和差异化策略")
            action_items.append("寻找细分市场或长尾关键词机会")
            action_items.append("控制初期投入，小规模测试")
        elif grade == ScoreGrade.D:
            recommendations.append("该市场机会有限，建议谨慎考虑")
            action_items.append("评估是否有独特的竞争优势")
            action_items.append("考虑寻找其他市场机会")
        else:
            recommendations.append("该市场不建议进入，风险较高")
            action_items.append("建议寻找其他蓝海市场")

        # 基于各维度的具体建议
        dim_dict = {dim.name: dim for dim in dimensions}

        # 需求维度
        if dim_dict.get('market_demand') and dim_dict['market_demand'].score < 50:
            recommendations.append("市场需求偏低，注意验证真实市场容量")

        # 竞争维度
        if dim_dict.get('competition') and dim_dict['competition'].score < 50:
            recommendations.append("竞争较激烈，需要明确的差异化优势")
            action_items.append("分析弱listing竞品，找出可优化的差异化点")

        # 利润维度
        if dim_dict.get('profit') and dim_dict['profit'].score < 50:
            recommendations.append("利润空间有限，需优化供应链成本")
            action_items.append("寻找更优质的供应商或优化产品设计")

        # 门槛维度
        if dim_dict.get('barrier') and dim_dict['barrier'].score < 50:
            recommendations.append("进入门槛较高，需要充足的启动资金")

        # 季节性维度
        if dim_dict.get('seasonality') and dim_dict['seasonality'].score < 50:
            recommendations.append("季节性波动较大，需要精准把握入场时机")
            action_items.append("制定季节性库存管理策略")

        # 趋势维度
        if dim_dict.get('trend') and dim_dict['trend'].score < 50:
            recommendations.append("市场趋势下降，需要评估长期可行性")

        return recommendations, action_items

    def _identify_risk_factors(
        self,
        dimensions: List[ScoreDimension]
    ) -> List[str]:
        """识别风险因素"""
        risk_factors = []

        for dim in dimensions:
            if dim.score < 40:
                if dim.name == 'market_demand':
                    risk_factors.append("市场需求不足风险")
                elif dim.name == 'competition':
                    risk_factors.append("竞争激烈风险")
                elif dim.name == 'profit':
                    risk_factors.append("利润空间不足风险")
                elif dim.name == 'barrier':
                    risk_factors.append("进入门槛过高风险")
                elif dim.name == 'seasonality':
                    risk_factors.append("季节性波动风险")
                elif dim.name == 'trend':
                    risk_factors.append("市场下行风险")

            # 检查具体风险
            details = dim.details
            if details.get('brand_concentration', 0) > 50:
                if "品牌垄断风险" not in risk_factors:
                    risk_factors.append("品牌垄断风险")
            if details.get('cpc_bid', 0) > 2.0:
                if "广告成本过高风险" not in risk_factors:
                    risk_factors.append("广告成本过高风险")

        return risk_factors

    def _determine_confidence_level(
        self,
        dimensions: List[ScoreDimension],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> str:
        """确定置信度"""
        data_completeness = 0

        # 检查数据完整性
        if sellerspirit_data:
            if _get_sellerspirit_attr(sellerspirit_data, 'monthly_searches'):
                data_completeness += 20
            if _get_sellerspirit_attr(sellerspirit_data, 'cpc_bid'):
                data_completeness += 15
            if _get_sellerspirit_attr(sellerspirit_data, 'trend_direction'):
                data_completeness += 15
            if _get_sellerspirit_attr(sellerspirit_data, 'seasonality_index') is not None:
                data_completeness += 15

        # 检查各维度是否有数据
        for dim in dimensions:
            if not dim.details.get('no_data', False):
                data_completeness += 5

        # 确定置信度
        if data_completeness >= 70:
            return '高'
        elif data_completeness >= 40:
            return '中'
        else:
            return '低'

    def score_to_dict(self, score: ComprehensiveScore) -> Dict[str, Any]:
        """将评分结果转换为字典"""
        return {
            'total_score': score.total_score,
            'grade': score.grade.grade,
            'grade_desc': score.grade.desc,
            'confidence_level': score.confidence_level,
            'dimensions': [
                {
                    'name': dim.name,
                    'score': round(dim.score, 2),
                    'weight': dim.weight,
                    'weighted_score': round(dim.weighted_score, 2),
                    'details': dim.details
                }
                for dim in score.dimensions
            ],
            'recommendations': score.recommendations,
            'action_items': score.action_items,
            'risk_factors': score.risk_factors
        }

    def compare_opportunities(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        比较多个机会

        Args:
            opportunities: 机会列表，每个包含blue_ocean_result等

        Returns:
            排序后的机会列表
        """
        scored_opportunities = []

        for opp in opportunities:
            score = self.calculate_comprehensive_score(
                blue_ocean_result=opp.get('blue_ocean_result', {}),
                seasonality_result=opp.get('seasonality_result'),
                sellerspirit_data=opp.get('sellerspirit_data'),
                products=opp.get('products')
            )

            scored_opportunities.append({
                'keyword': opp.get('keyword', 'unknown'),
                'score': self.score_to_dict(score),
                'original_data': opp
            })

        # 按总分排序
        scored_opportunities.sort(
            key=lambda x: x['score']['total_score'],
            reverse=True
        )

        return scored_opportunities
