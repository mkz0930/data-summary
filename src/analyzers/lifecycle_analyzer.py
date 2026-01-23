"""
生命周期分析器模块
识别新品机会，分析产品生命周期趋势
基于4大AI选品方法论优化 - 增强版
继承 BaseAnalyzer 基类
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import statistics

from src.database.models import Product, SellerSpiritData
from src.analyzers.base_analyzer import BaseAnalyzer


class LifecycleStage(Enum):
    """产品生命周期阶段"""
    INTRODUCTION = ('导入期', '新品刚上市，销量低，评论少')
    GROWTH = ('成长期', '销量快速增长，评论积累中')
    MATURITY = ('成熟期', '销量稳定，评论数高')
    DECLINE = ('衰退期', '销量下降，市场饱和')
    UNKNOWN = ('未知', '数据不足，无法判断')

    def __init__(self, stage_name: str, description: str):
        self.stage_name = stage_name
        self.description = description


class LifecycleAnalyzer(BaseAnalyzer):
    """
    生命周期分析器 - 增强版

    继承 BaseAnalyzer，提供产品生命周期分析、新品机会识别等功能。
    """

    # 生命周期阶段判定阈值
    STAGE_THRESHOLDS = {
        'introduction': {
            'max_days': 90,
            'max_reviews': 50,
            'max_sales': 300
        },
        'growth': {
            'max_days': 365,
            'min_reviews': 20,
            'max_reviews': 500,
            'review_growth_rate': 0.1  # 月评论增长率
        },
        'maturity': {
            'min_reviews': 500,
            'stable_sales_variance': 0.3  # 销量波动系数
        },
        'decline': {
            'min_days': 365,
            'sales_decline_rate': -0.1  # 月销量下降率
        }
    }

    def __init__(
        self,
        new_product_days: int = 180,
        new_product_min_reviews: int = 50,
        new_product_max_bsr: int = 10000,
        success_review_threshold: int = 100,
        success_rating_threshold: float = 4.0,
        success_bsr_threshold: int = 5000
    ):
        """
        初始化生命周期分析器

        Args:
            new_product_days: 新品定义天数阈值
            new_product_min_reviews: 新品最小评论数（证明有销量）
            new_product_max_bsr: 新品最大BSR排名
            success_review_threshold: 成功新品评论数阈值
            success_rating_threshold: 成功新品评分阈值
            success_bsr_threshold: 成功新品BSR阈值
        """
        super().__init__(name="LifecycleAnalyzer")
        self.new_product_days = new_product_days
        self.new_product_min_reviews = new_product_min_reviews
        self.new_product_max_bsr = new_product_max_bsr
        self.success_review_threshold = success_review_threshold
        self.success_rating_threshold = success_rating_threshold
        self.success_bsr_threshold = success_bsr_threshold

    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        综合生命周期分析 - 增强版

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            生命周期分析结果
        """
        self.log_info(f"开始增强版生命周期分析，产品数量: {len(products)}")

        # 识别新品
        new_products = self.identify_new_products(products)

        # 分析新品趋势
        trend = self._analyze_new_product_trend(new_products)

        # 分析新品特征
        characteristics = self._analyze_new_product_characteristics(new_products)

        # 对比新品与老品
        comparison = self._compare_new_vs_old(products, new_products)

        # 新增：生命周期阶段分布
        lifecycle_distribution = self._analyze_lifecycle_distribution(products)

        # 新增：新品成功率分析
        success_analysis = self._analyze_new_product_success_rate(new_products)

        # 新增：市场进入时机评估
        entry_timing = self._evaluate_market_entry_timing(
            products, new_products, sellerspirit_data
        )

        # 新增：竞品生命周期对比
        competitor_lifecycle = self._analyze_competitor_lifecycle(products)

        # 新增：新品机会评分
        opportunity_score = self._calculate_new_product_opportunity_score(
            new_products, success_analysis, entry_timing, sellerspirit_data
        )

        result = {
            'new_products': [p.to_dict() for p in new_products[:50]],  # 限制返回数量
            'new_product_count': len(new_products),
            'trend': trend,
            'characteristics': characteristics,
            'comparison': comparison,
            'lifecycle_distribution': lifecycle_distribution,
            'success_analysis': success_analysis,
            'entry_timing': entry_timing,
            'competitor_lifecycle': competitor_lifecycle,
            'opportunity_score': opportunity_score
        }

        self.log_info(f"生命周期分析完成，发现 {len(new_products)} 个新品机会")
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
                self.log_warning(f"解析上架时间失败 {product.asin}: {e}")
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
        生成生命周期分析摘要 - 增强版

        Args:
            analysis_result: 生命周期分析结果

        Returns:
            摘要文本
        """
        new_count = analysis_result.get('new_product_count', 0)
        trend = analysis_result.get('trend', {})
        characteristics = analysis_result.get('characteristics', {})
        comparison = analysis_result.get('comparison', {})
        lifecycle_dist = analysis_result.get('lifecycle_distribution', {})
        success_analysis = analysis_result.get('success_analysis', {})
        entry_timing = analysis_result.get('entry_timing', {})
        opportunity_score = analysis_result.get('opportunity_score', {})

        summary = f"""
生命周期分析摘要 (增强版)
{'=' * 50}

【新品机会评分】
- 总分: {opportunity_score.get('total_score', 0)}/100
- 等级: {opportunity_score.get('grade', 'N/A')} - {opportunity_score.get('grade_desc', '')}
- 建议: {opportunity_score.get('recommendation', '')}

【新品机会】
- 新品数量: {new_count}
- 趋势方向: {trend.get('trend_direction', '未知')}
- 增长率: {trend.get('growth_rate', 0)}%

【新品成功率分析】
- 成功新品数: {success_analysis.get('successful_count', 0)}
- 成功率: {success_analysis.get('success_rate', 0)}%
- 部分成功: {success_analysis.get('partial_success_count', 0)}
- 成功难度: {success_analysis.get('success_difficulty', {}).get('difficulty_level', '未知')}

【市场进入时机】
- 时机评分: {entry_timing.get('timing_score', 0)}/100
- 时机评级: {entry_timing.get('timing_grade', '未知')}
- 建议: {entry_timing.get('timing_recommendation', '')}

【生命周期分布】
- 市场成熟度: {lifecycle_dist.get('market_maturity', '未知')}
- 成长期产品占比: {lifecycle_dist.get('growth_stage_rate', 0)}%
- 新进入者占比: {lifecycle_dist.get('new_entry_rate', 0)}%

【新品特征】
- 平均价格: ${characteristics.get('average_price', 0)}
- 平均评分: {characteristics.get('average_rating', 0)}
- 平均评论数: {characteristics.get('average_reviews', 0)}
- 价格区间: ${characteristics.get('price_range', {}).get('min', 0)} - ${characteristics.get('price_range', {}).get('max', 0)}

【新品 vs 老品对比】
- 新品数量: {comparison.get('new_count', 0)}
- 老品数量: {comparison.get('old_count', 0)}
- 价格差异: ${comparison.get('comparison', {}).get('price', {}).get('difference', 0)}
- 评分差异: {comparison.get('comparison', {}).get('rating', {}).get('difference', 0)}
"""

        return summary

    def determine_lifecycle_stage(self, product: Product) -> Tuple[LifecycleStage, Dict[str, Any]]:
        """
        判定单个产品的生命周期阶段

        Args:
            product: 产品对象

        Returns:
            (生命周期阶段, 判定依据)
        """
        details = {}

        # 计算上架天数
        days_on_market = self._calculate_days_on_market(product)
        details['days_on_market'] = days_on_market

        reviews = product.reviews_count or 0
        sales = product.sales_volume or 0
        rating = product.rating or 0

        details['reviews'] = reviews
        details['sales_volume'] = sales
        details['rating'] = rating

        # 导入期判定
        if days_on_market is not None and days_on_market <= self.STAGE_THRESHOLDS['introduction']['max_days']:
            if reviews <= self.STAGE_THRESHOLDS['introduction']['max_reviews']:
                return LifecycleStage.INTRODUCTION, details

        # 成长期判定
        if days_on_market is not None and days_on_market <= self.STAGE_THRESHOLDS['growth']['max_days']:
            if (self.STAGE_THRESHOLDS['growth']['min_reviews'] <= reviews <=
                self.STAGE_THRESHOLDS['growth']['max_reviews']):
                return LifecycleStage.GROWTH, details

        # 成熟期判定
        if reviews >= self.STAGE_THRESHOLDS['maturity']['min_reviews']:
            return LifecycleStage.MATURITY, details

        # 衰退期判定 (需要历史数据，这里简化处理)
        if days_on_market is not None and days_on_market > self.STAGE_THRESHOLDS['decline']['min_days']:
            if reviews < 100 and sales < 100:
                return LifecycleStage.DECLINE, details

        # 无法判定
        return LifecycleStage.UNKNOWN, details

    def _calculate_days_on_market(self, product: Product) -> Optional[int]:
        """计算产品上架天数"""
        if not product.available_date:
            return None

        try:
            available_date = datetime.fromisoformat(
                product.available_date.replace('Z', '+00:00')
            )
            days = (datetime.now(available_date.tzinfo) - available_date).days
            return max(0, days)
        except Exception:
            return None

    def _analyze_lifecycle_distribution(
        self,
        products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析产品生命周期阶段分布

        Args:
            products: 产品列表

        Returns:
            生命周期分布分析
        """
        distribution = {
            'introduction': [],
            'growth': [],
            'maturity': [],
            'decline': [],
            'unknown': []
        }

        stage_counts = defaultdict(int)

        for product in products:
            stage, details = self.determine_lifecycle_stage(product)

            stage_key = stage.name.lower()
            stage_counts[stage_key] += 1

            # 只保存前10个示例
            if len(distribution[stage_key]) < 10:
                distribution[stage_key].append({
                    'asin': product.asin,
                    'name': product.name[:50] if product.name else '',
                    'stage': stage.stage_name,
                    'details': details
                })

        total = len(products)
        percentages = {
            stage: round(count / total * 100, 2) if total > 0 else 0
            for stage, count in stage_counts.items()
        }

        # 市场成熟度评估
        maturity_rate = percentages.get('maturity', 0) + percentages.get('decline', 0)
        if maturity_rate > 60:
            market_maturity = '成熟市场'
            market_maturity_desc = '市场已趋于饱和，新品进入难度较大'
        elif maturity_rate > 40:
            market_maturity = '发展中市场'
            market_maturity_desc = '市场仍有发展空间，适合差异化进入'
        else:
            market_maturity = '新兴市场'
            market_maturity_desc = '市场处于早期阶段，机会较多'

        return {
            'counts': dict(stage_counts),
            'percentages': percentages,
            'examples': distribution,
            'market_maturity': market_maturity,
            'market_maturity_desc': market_maturity_desc,
            'growth_stage_rate': percentages.get('growth', 0),
            'new_entry_rate': percentages.get('introduction', 0)
        }

    def _analyze_new_product_success_rate(
        self,
        new_products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析新品成功率

        成功定义:
        - 评论数 >= success_review_threshold
        - 评分 >= success_rating_threshold
        - BSR排名 <= success_bsr_threshold

        Args:
            new_products: 新品列表

        Returns:
            成功率分析结果
        """
        if not new_products:
            return {
                'total_new_products': 0,
                'successful_count': 0,
                'success_rate': 0,
                'partial_success_count': 0,
                'failed_count': 0,
                'success_factors': [],
                'successful_products': []
            }

        successful = []
        partial_success = []
        failed = []

        for product in new_products:
            reviews_ok = (product.reviews_count or 0) >= self.success_review_threshold
            rating_ok = (product.rating or 0) >= self.success_rating_threshold
            bsr_ok = (product.bsr_rank or float('inf')) <= self.success_bsr_threshold

            success_score = sum([reviews_ok, rating_ok, bsr_ok])

            if success_score == 3:
                successful.append(product)
            elif success_score >= 2:
                partial_success.append(product)
            else:
                failed.append(product)

        total = len(new_products)
        success_rate = round(len(successful) / total * 100, 2) if total > 0 else 0

        # 分析成功因素
        success_factors = self._analyze_success_factors(successful, failed)

        # 成功产品详情
        successful_products = [
            {
                'asin': p.asin,
                'name': p.name[:50] if p.name else '',
                'price': p.price,
                'rating': p.rating,
                'reviews_count': p.reviews_count,
                'bsr_rank': p.bsr_rank,
                'days_on_market': self._calculate_days_on_market(p)
            }
            for p in successful[:10]
        ]

        return {
            'total_new_products': total,
            'successful_count': len(successful),
            'success_rate': success_rate,
            'partial_success_count': len(partial_success),
            'partial_success_rate': round(len(partial_success) / total * 100, 2) if total > 0 else 0,
            'failed_count': len(failed),
            'failure_rate': round(len(failed) / total * 100, 2) if total > 0 else 0,
            'success_factors': success_factors,
            'successful_products': successful_products,
            'success_difficulty': self._assess_success_difficulty(success_rate)
        }

    def _analyze_success_factors(
        self,
        successful: List[Product],
        failed: List[Product]
    ) -> List[Dict[str, Any]]:
        """分析成功因素"""
        factors = []

        if not successful:
            return factors

        # 价格因素
        success_prices = [p.price for p in successful if p.price]
        failed_prices = [p.price for p in failed if p.price]

        if success_prices and failed_prices:
            avg_success_price = statistics.mean(success_prices)
            avg_failed_price = statistics.mean(failed_prices)

            if avg_success_price < avg_failed_price * 0.9:
                factors.append({
                    'factor': '价格优势',
                    'description': f'成功产品平均价格(${avg_success_price:.2f})低于失败产品(${avg_failed_price:.2f})',
                    'importance': 'high'
                })
            elif avg_success_price > avg_failed_price * 1.1:
                factors.append({
                    'factor': '高端定位',
                    'description': f'成功产品采用高端定价策略(${avg_success_price:.2f})',
                    'importance': 'medium'
                })

        # 评分因素
        success_ratings = [p.rating for p in successful if p.rating]
        if success_ratings:
            avg_rating = statistics.mean(success_ratings)
            if avg_rating >= 4.5:
                factors.append({
                    'factor': '高评分',
                    'description': f'成功产品平均评分高达{avg_rating:.2f}',
                    'importance': 'high'
                })

        # 品牌因素
        success_brands = [p.brand for p in successful if p.brand]
        if success_brands:
            brand_counts = defaultdict(int)
            for brand in success_brands:
                brand_counts[brand] += 1

            top_brand = max(brand_counts.items(), key=lambda x: x[1]) if brand_counts else None
            if top_brand and top_brand[1] >= 2:
                factors.append({
                    'factor': '品牌效应',
                    'description': f'品牌"{top_brand[0]}"有{top_brand[1]}个成功产品',
                    'importance': 'medium'
                })

        return factors

    def _assess_success_difficulty(self, success_rate: float) -> Dict[str, Any]:
        """评估新品成功难度"""
        if success_rate >= 30:
            level = '低'
            desc = '新品成功率较高，市场对新进入者友好'
            recommendation = '建议积极进入，注重产品质量'
        elif success_rate >= 15:
            level = '中'
            desc = '新品成功率适中，需要差异化策略'
            recommendation = '建议找准细分定位，避免正面竞争'
        elif success_rate >= 5:
            level = '高'
            desc = '新品成功率较低，竞争激烈'
            recommendation = '建议谨慎进入，需要强大的运营能力'
        else:
            level = '极高'
            desc = '新品成功率极低，市场门槛很高'
            recommendation = '不建议新手进入，需要充足资源'

        return {
            'difficulty_level': level,
            'description': desc,
            'recommendation': recommendation
        }

    def _evaluate_market_entry_timing(
        self,
        products: List[Product],
        new_products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        评估市场进入时机

        Args:
            products: 所有产品
            new_products: 新品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            进入时机评估
        """
        # 新品占比
        new_product_rate = len(new_products) / len(products) * 100 if products else 0

        # 市场活跃度 (基于新品数量和趋势)
        trend = self._analyze_new_product_trend(new_products)
        trend_direction = trend.get('trend_direction', '未知')

        # 竞争强度评估
        reviews_list = [p.reviews_count for p in products if p.reviews_count]
        avg_reviews = statistics.mean(reviews_list) if reviews_list else 0

        # 季节性考虑
        seasonality_factor = 1.0
        if sellerspirit_data and sellerspirit_data.seasonality_index is not None:
            seasonality_index = sellerspirit_data.seasonality_index
            if seasonality_index < 30:
                seasonality_factor = 1.2  # 稳定市场加分
            elif seasonality_index > 70:
                seasonality_factor = 0.8  # 季节性强减分

        # 计算进入时机分数
        timing_score = 50.0

        # 新品占比影响
        if new_product_rate >= 20:
            timing_score += 15
        elif new_product_rate >= 10:
            timing_score += 10
        elif new_product_rate < 5:
            timing_score -= 10

        # 趋势影响
        if trend_direction == '上升':
            timing_score += 15
        elif trend_direction == '下降':
            timing_score -= 15

        # 竞争强度影响
        if avg_reviews < 100:
            timing_score += 10
        elif avg_reviews > 500:
            timing_score -= 10

        # 季节性调整
        timing_score *= seasonality_factor

        timing_score = max(0, min(100, timing_score))

        # 评级
        if timing_score >= 70:
            timing_grade = '优秀'
            timing_recommendation = '当前是进入市场的好时机'
        elif timing_score >= 50:
            timing_grade = '良好'
            timing_recommendation = '可以考虑进入，但需要差异化策略'
        elif timing_score >= 30:
            timing_grade = '一般'
            timing_recommendation = '进入时机一般，建议观望或寻找细分机会'
        else:
            timing_grade = '不佳'
            timing_recommendation = '当前不是进入的好时机，建议等待'

        return {
            'timing_score': round(timing_score, 2),
            'timing_grade': timing_grade,
            'timing_recommendation': timing_recommendation,
            'factors': {
                'new_product_rate': round(new_product_rate, 2),
                'trend_direction': trend_direction,
                'avg_competitor_reviews': round(avg_reviews, 0),
                'seasonality_factor': seasonality_factor
            },
            'best_entry_window': self._suggest_entry_window(sellerspirit_data)
        }

    def _suggest_entry_window(
        self,
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """建议最佳进入窗口"""
        current_month = datetime.now().month

        # 默认建议
        suggestion = {
            'recommended_months': [],
            'avoid_months': [],
            'reason': '无季节性数据，建议全年均可进入'
        }

        if sellerspirit_data and sellerspirit_data.search_trend_data:
            try:
                import json
                trend_data = json.loads(sellerspirit_data.search_trend_data)

                if isinstance(trend_data, list) and len(trend_data) >= 12:
                    # 找出搜索量高峰前2-3个月作为最佳进入时机
                    indexed_data = list(enumerate(trend_data, 1))
                    sorted_data = sorted(indexed_data, key=lambda x: x[1], reverse=True)

                    peak_months = [m for m, _ in sorted_data[:3]]
                    # 建议在高峰前2-3个月进入
                    recommended = [(m - 2) % 12 or 12 for m in peak_months]

                    low_months = [m for m, _ in sorted_data[-3:]]

                    suggestion = {
                        'recommended_months': recommended,
                        'avoid_months': low_months,
                        'peak_months': peak_months,
                        'reason': f'建议在销售高峰({peak_months})前2-3个月进入准备'
                    }
            except (json.JSONDecodeError, TypeError):
                pass

        return suggestion

    def _analyze_competitor_lifecycle(
        self,
        products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析竞品生命周期分布

        Args:
            products: 产品列表

        Returns:
            竞品生命周期分析
        """
        if not products:
            return {'error': '无产品数据'}

        # 按上架时间分组
        age_groups = {
            '0-3个月': [],
            '3-6个月': [],
            '6-12个月': [],
            '1-2年': [],
            '2年以上': [],
            '未知': []
        }

        for product in products:
            days = self._calculate_days_on_market(product)

            if days is None:
                age_groups['未知'].append(product)
            elif days <= 90:
                age_groups['0-3个月'].append(product)
            elif days <= 180:
                age_groups['3-6个月'].append(product)
            elif days <= 365:
                age_groups['6-12个月'].append(product)
            elif days <= 730:
                age_groups['1-2年'].append(product)
            else:
                age_groups['2年以上'].append(product)

        # 统计各组指标
        group_stats = {}
        for group_name, group_products in age_groups.items():
            if not group_products:
                continue

            prices = [p.price for p in group_products if p.price]
            reviews = [p.reviews_count for p in group_products if p.reviews_count]
            ratings = [p.rating for p in group_products if p.rating]

            group_stats[group_name] = {
                'count': len(group_products),
                'percentage': round(len(group_products) / len(products) * 100, 2),
                'avg_price': round(statistics.mean(prices), 2) if prices else 0,
                'avg_reviews': round(statistics.mean(reviews), 0) if reviews else 0,
                'avg_rating': round(statistics.mean(ratings), 2) if ratings else 0
            }

        # 市场年龄结构评估
        young_rate = sum(
            group_stats.get(g, {}).get('percentage', 0)
            for g in ['0-3个月', '3-6个月']
        )
        old_rate = sum(
            group_stats.get(g, {}).get('percentage', 0)
            for g in ['1-2年', '2年以上']
        )

        if young_rate > 30:
            age_structure = '年轻化市场'
            age_structure_desc = '新品占比高，市场活跃度好'
        elif old_rate > 50:
            age_structure = '成熟化市场'
            age_structure_desc = '老产品占主导，新品进入需要差异化'
        else:
            age_structure = '均衡市场'
            age_structure_desc = '产品年龄分布均衡，市场处于稳定发展期'

        return {
            'age_groups': group_stats,
            'age_structure': age_structure,
            'age_structure_desc': age_structure_desc,
            'young_product_rate': round(young_rate, 2),
            'old_product_rate': round(old_rate, 2)
        }

    def _calculate_new_product_opportunity_score(
        self,
        new_products: List[Product],
        success_analysis: Dict[str, Any],
        entry_timing: Dict[str, Any],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        计算新品机会评分

        Args:
            new_products: 新品列表
            success_analysis: 成功率分析
            entry_timing: 进入时机评估
            sellerspirit_data: 卖家精灵数据

        Returns:
            新品机会评分
        """
        score = 50.0
        score_breakdown = {}

        # 1. 新品数量分 (25分)
        new_count = len(new_products)
        if new_count >= 10:
            new_count_score = 25
        elif new_count >= 5:
            new_count_score = 20
        elif new_count >= 2:
            new_count_score = 15
        elif new_count >= 1:
            new_count_score = 10
        else:
            new_count_score = 5
        score_breakdown['new_count_score'] = new_count_score

        # 2. 成功率分 (25分)
        success_rate = success_analysis.get('success_rate', 0)
        if success_rate >= 30:
            success_score = 25
        elif success_rate >= 20:
            success_score = 20
        elif success_rate >= 10:
            success_score = 15
        elif success_rate >= 5:
            success_score = 10
        else:
            success_score = 5
        score_breakdown['success_score'] = success_score

        # 3. 进入时机分 (25分)
        timing_score = entry_timing.get('timing_score', 50)
        timing_component = timing_score * 0.25
        score_breakdown['timing_score'] = round(timing_component, 2)

        # 4. 市场需求分 (25分)
        demand_score = 15  # 默认中等
        if sellerspirit_data and sellerspirit_data.monthly_searches:
            searches = sellerspirit_data.monthly_searches
            if 5000 <= searches <= 50000:
                demand_score = 25
            elif searches > 50000:
                demand_score = 20
            elif searches >= 2000:
                demand_score = 15
            else:
                demand_score = 8
        score_breakdown['demand_score'] = demand_score

        # 计算总分
        total_score = new_count_score + success_score + timing_component + demand_score

        # 评级
        if total_score >= 80:
            grade = 'A'
            grade_desc = '优秀的新品机会'
            recommendation = '强烈建议进入，新品成功概率高'
        elif total_score >= 65:
            grade = 'B'
            grade_desc = '良好的新品机会'
            recommendation = '建议进入，注重差异化和产品质量'
        elif total_score >= 50:
            grade = 'C'
            grade_desc = '一般的新品机会'
            recommendation = '可以考虑，但需要精准定位'
        elif total_score >= 35:
            grade = 'D'
            grade_desc = '有限的新品机会'
            recommendation = '谨慎考虑，需要独特优势'
        else:
            grade = 'F'
            grade_desc = '不建议进入'
            recommendation = '新品机会较少，建议寻找其他市场'

        return {
            'total_score': round(total_score, 2),
            'grade': grade,
            'grade_desc': grade_desc,
            'recommendation': recommendation,
            'score_breakdown': score_breakdown
        }
