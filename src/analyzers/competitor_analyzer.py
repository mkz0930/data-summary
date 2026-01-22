"""
竞品对标分析器模块
分析竞品表现、识别标杆产品
"""

from typing import List, Dict, Any
from collections import defaultdict

from src.database.models import Product
from src.utils.logger import get_logger


class CompetitorAnalyzer:
    """竞品对标分析器"""

    def __init__(self):
        """初始化竞品对标分析器"""
        self.logger = get_logger()

    def analyze(self, products: List[Product], sellerspirit_data=None) -> Dict[str, Any]:
        """
        综合竞品分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据（可选）

        Returns:
            竞品分析结果
        """
        self.logger.info(f"开始竞品对标分析，产品数量: {len(products)}")

        result = {
            'top_performers': self._identify_top_performers(products),
            'benchmark_products': self._identify_benchmark_products(products),
            'competitor_segments': self._segment_competitors(products),
            'success_patterns': self._analyze_success_patterns(products),
            'competitive_gaps': self._identify_competitive_gaps(products),
            'market_concentration': self._analyze_market_concentration(products, sellerspirit_data)
        }

        self.logger.info("竞品对标分析完成")
        return result

    def _identify_top_performers(
        self,
        products: List[Product],
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        识别头部表现产品

        Args:
            products: 产品列表
            top_n: 返回数量

        Returns:
            头部产品列表
        """
        if not products:
            return []

        # 计算综合表现分数
        scored_products = []
        for product in products:
            score = self._calculate_performance_score(product)
            scored_products.append({
                'asin': product.asin,
                'title': product.name,
                'brand': product.brand,
                'price': product.price,
                'rating': product.rating,
                'reviews_count': product.reviews_count,
                'sales_volume': product.sales_volume,
                'performance_score': score
            })

        # 按分数排序
        scored_products.sort(key=lambda x: x['performance_score'], reverse=True)

        return scored_products[:top_n]

    def _calculate_performance_score(self, product: Product) -> float:
        """
        计算产品表现分数

        评分维度：
        1. 销量（40分）
        2. 评分（30分）
        3. 评论数（30分）

        Args:
            product: 产品对象

        Returns:
            表现分数（0-100）
        """
        score = 0.0

        # 销量评分（40分）
        sales = product.sales_volume or 0
        if sales >= 1000:
            score += 40
        elif sales >= 500:
            score += 35
        elif sales >= 100:
            score += 30
        elif sales >= 50:
            score += 20
        else:
            score += 10

        # 评分评分（30分）
        rating = product.rating or 0
        if rating >= 4.5:
            score += 30
        elif rating >= 4.0:
            score += 25
        elif rating >= 3.5:
            score += 20
        elif rating >= 3.0:
            score += 10
        else:
            score += 5

        # 评论数评分（30分）
        reviews = product.reviews_count or 0
        if reviews >= 5000:
            score += 30
        elif reviews >= 1000:
            score += 25
        elif reviews >= 500:
            score += 20
        elif reviews >= 100:
            score += 15
        else:
            score += 5

        return score

    def _identify_benchmark_products(
        self,
        products: List[Product],
        min_score: float = 70.0
    ) -> List[Dict[str, Any]]:
        """
        识别标杆产品（可作为对标参考的产品）

        标杆产品标准：
        1. 综合表现分数 >= min_score
        2. 评分 >= 4.0
        3. 评论数 >= 100

        Args:
            products: 产品列表
            min_score: 最低分数阈值

        Returns:
            标杆产品列表
        """
        benchmarks = []

        for product in products:
            score = self._calculate_performance_score(product)
            rating = product.rating or 0
            reviews = product.reviews_count or 0

            if score >= min_score and rating >= 4.0 and reviews >= 100:
                benchmarks.append({
                    'asin': product.asin,
                    'title': product.name,
                    'brand': product.brand,
                    'price': product.price,
                    'rating': rating,
                    'reviews_count': reviews,
                    'sales_volume': product.sales_volume,
                    'performance_score': score,
                    'benchmark_reason': self._get_benchmark_reason(product, score)
                })

        # 按分数排序
        benchmarks.sort(key=lambda x: x['performance_score'], reverse=True)

        return benchmarks

    def _get_benchmark_reason(self, product: Product, score: float) -> str:
        """
        获取成为标杆产品的原因

        Args:
            product: 产品对象
            score: 表现分数

        Returns:
            原因描述
        """
        reasons = []

        if (product.rating or 0) >= 4.5:
            reasons.append("高评分")
        if (product.reviews_count or 0) >= 1000:
            reasons.append("大量评论")
        if (product.sales_volume or 0) >= 500:
            reasons.append("高销量")
        if score >= 85:
            reasons.append("综合表现优异")

        return "、".join(reasons) if reasons else "综合表现良好"

    def _segment_competitors(
        self,
        products: List[Product]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        竞品分层分析

        按价格和表现分为不同层级：
        - 高端市场：价格高、表现好
        - 中端市场：价格中等、表现中等
        - 低端市场：价格低、表现一般
        - 性价比产品：价格低、表现好

        Args:
            products: 产品列表

        Returns:
            分层竞品字典
        """
        if not products:
            return {
                'high_end': [],
                'mid_range': [],
                'low_end': [],
                'value_for_money': []
            }

        # 计算价格分位数
        prices = [p.price for p in products if p.price]
        if not prices:
            return {
                'high_end': [],
                'mid_range': [],
                'low_end': [],
                'value_for_money': []
            }

        sorted_prices = sorted(prices)
        price_33 = sorted_prices[len(sorted_prices) // 3]
        price_67 = sorted_prices[len(sorted_prices) * 2 // 3]

        segments = {
            'high_end': [],
            'mid_range': [],
            'low_end': [],
            'value_for_money': []
        }

        for product in products:
            if not product.price:
                continue

            score = self._calculate_performance_score(product)

            item = {
                'asin': product.asin,
                'title': product.name,
                'brand': product.brand,
                'price': product.price,
                'rating': product.rating,
                'reviews_count': product.reviews_count,
                'sales_volume': product.sales_volume,
                'performance_score': score
            }

            # 分类
            if product.price >= price_67:
                if score >= 70:
                    segments['high_end'].append(item)
                else:
                    segments['mid_range'].append(item)
            elif product.price >= price_33:
                segments['mid_range'].append(item)
            else:
                if score >= 70:
                    segments['value_for_money'].append(item)
                else:
                    segments['low_end'].append(item)

        # 排序
        for segment in segments.values():
            segment.sort(key=lambda x: x['performance_score'], reverse=True)

        return segments

    def _analyze_success_patterns(
        self,
        products: List[Product]
    ) -> Dict[str, Any]:
        """
        分析成功产品的共同模式

        Args:
            products: 产品列表

        Returns:
            成功模式分析结果
        """
        # 识别成功产品（表现分数 >= 70）
        successful_products = [
            p for p in products
            if self._calculate_performance_score(p) >= 70
        ]

        if not successful_products:
            return {
                'count': 0,
                'avg_price': 0,
                'avg_rating': 0,
                'avg_reviews': 0,
                'common_brands': [],
                'price_range': {}
            }

        # 统计成功产品的特征
        prices = [p.price for p in successful_products if p.price]
        ratings = [p.rating for p in successful_products if p.rating]
        reviews = [p.reviews_count for p in successful_products if p.reviews_count]

        # 品牌分布
        brand_counter = defaultdict(int)
        for product in successful_products:
            brand = product.brand or "Unknown"
            brand_counter[brand] += 1

        common_brands = sorted(
            brand_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'count': len(successful_products),
            'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
            'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
            'avg_reviews': round(sum(reviews) / len(reviews), 2) if reviews else 0,
            'common_brands': [{'brand': b, 'count': c} for b, c in common_brands],
            'price_range': {
                'min': round(min(prices), 2) if prices else 0,
                'max': round(max(prices), 2) if prices else 0
            }
        }

    def _identify_competitive_gaps(
        self,
        products: List[Product]
    ) -> List[Dict[str, Any]]:
        """
        识别竞争空白点

        通过分析价格带和表现分布，找出竞争较弱的区域

        Args:
            products: 产品列表

        Returns:
            竞争空白点列表
        """
        if not products:
            return []

        # 按价格分段统计
        price_segments = {
            'under_10': [],
            '10_20': [],
            '20_50': [],
            '50_100': [],
            'over_100': []
        }

        for product in products:
            if not product.price:
                continue

            if product.price < 10:
                price_segments['under_10'].append(product)
            elif product.price < 20:
                price_segments['10_20'].append(product)
            elif product.price < 50:
                price_segments['20_50'].append(product)
            elif product.price < 100:
                price_segments['50_100'].append(product)
            else:
                price_segments['over_100'].append(product)

        # 分析每个价格段的竞争强度
        gaps = []
        segment_names = {
            'under_10': '$0-10',
            '10_20': '$10-20',
            '20_50': '$20-50',
            '50_100': '$50-100',
            'over_100': '$100+'
        }

        for segment_key, segment_products in price_segments.items():
            if not segment_products:
                gaps.append({
                    'price_range': segment_names[segment_key],
                    'gap_type': '完全空白',
                    'product_count': 0,
                    'opportunity_level': '高'
                })
                continue

            # 计算该价格段的平均表现分数
            avg_score = sum(
                self._calculate_performance_score(p)
                for p in segment_products
            ) / len(segment_products)

            # 如果产品数量少且平均分数低，说明是竞争空白
            if len(segment_products) < 10 and avg_score < 60:
                gaps.append({
                    'price_range': segment_names[segment_key],
                    'gap_type': '弱竞争',
                    'product_count': len(segment_products),
                    'avg_performance': round(avg_score, 2),
                    'opportunity_level': '中'
                })

        return gaps

    def _analyze_market_concentration(
        self,
        products: List[Product],
        sellerspirit_data=None
    ) -> Dict[str, Any]:
        """
        分析市场集中度

        使用CR4（前4名市场份额）和HHI指数评估市场竞争格局

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据（包含cr4和monopoly_rate）

        Returns:
            市场集中度分析结果
        """
        if not products:
            return {
                'cr4': None,
                'monopoly_rate': None,
                'concentration_level': '未知',
                'market_structure': '未知',
                'competition_intensity': '未知',
                'entry_barrier': '未知'
            }

        # 从卖家精灵获取CR4和垄断率
        cr4 = None
        monopoly_rate = None
        if sellerspirit_data:
            cr4 = sellerspirit_data.cr4 if hasattr(sellerspirit_data, 'cr4') else sellerspirit_data.get('cr4')
            monopoly_rate = sellerspirit_data.monopoly_rate if hasattr(sellerspirit_data, 'monopoly_rate') else sellerspirit_data.get('monopoly_rate')

        # 基于产品数据计算市场集中度指标
        # 按销量排序计算前N名的市场份额
        products_with_sales = [p for p in products if p.sales_volume and p.sales_volume > 0]

        if products_with_sales:
            # 按销量排序
            sorted_products = sorted(products_with_sales, key=lambda x: x.sales_volume, reverse=True)
            total_sales = sum(p.sales_volume for p in products_with_sales)

            # 计算CR4（如果卖家精灵没有提供）
            if cr4 is None and len(sorted_products) >= 4:
                top4_sales = sum(p.sales_volume for p in sorted_products[:4])
                cr4 = round((top4_sales / total_sales) * 100, 2) if total_sales > 0 else 0

            # 计算HHI指数（赫芬达尔-赫希曼指数）
            hhi = sum(((p.sales_volume / total_sales) * 100) ** 2 for p in products_with_sales) if total_sales > 0 else 0
            hhi = round(hhi, 2)
        else:
            hhi = None

        # 判断市场集中度水平
        concentration_level = self._get_concentration_level(cr4)
        market_structure = self._get_market_structure(cr4, hhi)
        competition_intensity = self._get_competition_intensity(cr4, monopoly_rate)
        entry_barrier = self._get_entry_barrier(cr4, monopoly_rate)

        return {
            'cr4': cr4,
            'monopoly_rate': monopoly_rate,
            'hhi': hhi,
            'concentration_level': concentration_level,
            'market_structure': market_structure,
            'competition_intensity': competition_intensity,
            'entry_barrier': entry_barrier,
            'top_brands': self._get_top_brands(products, top_n=4)
        }

    def _get_concentration_level(self, cr4: float) -> str:
        """根据CR4判断市场集中度水平"""
        if cr4 is None:
            return '未知'
        if cr4 >= 75:
            return '极高集中'
        elif cr4 >= 50:
            return '高度集中'
        elif cr4 >= 30:
            return '中度集中'
        else:
            return '低度集中'

    def _get_market_structure(self, cr4: float, hhi: float) -> str:
        """根据CR4和HHI判断市场结构"""
        if cr4 is None:
            return '未知'

        if cr4 >= 75:
            return '寡头垄断'
        elif cr4 >= 50:
            return '寡头竞争'
        elif cr4 >= 30:
            return '垄断竞争'
        else:
            return '完全竞争'

    def _get_competition_intensity(self, cr4: float, monopoly_rate: float) -> str:
        """根据CR4和垄断率判断竞争强度"""
        if cr4 is None:
            return '未知'

        # CR4越高，竞争越激烈（头部品牌占据主导）
        if cr4 >= 60 or (monopoly_rate and monopoly_rate >= 60):
            return '激烈'
        elif cr4 >= 40:
            return '中等'
        else:
            return '温和'

    def _get_entry_barrier(self, cr4: float, monopoly_rate: float) -> str:
        """根据市场集中度判断进入壁垒"""
        if cr4 is None:
            return '未知'

        if cr4 >= 60 or (monopoly_rate and monopoly_rate >= 60):
            return '高壁垒'
        elif cr4 >= 40:
            return '中等壁垒'
        else:
            return '低壁垒'

    def _get_top_brands(self, products: List[Product], top_n: int = 4) -> List[Dict[str, Any]]:
        """获取头部品牌信息"""
        # 按品牌聚合销量
        brand_sales = defaultdict(lambda: {'sales': 0, 'products': 0, 'avg_rating': []})

        for product in products:
            if product.brand and product.sales_volume:
                brand = product.brand
                brand_sales[brand]['sales'] += product.sales_volume
                brand_sales[brand]['products'] += 1
                if product.rating:
                    brand_sales[brand]['avg_rating'].append(product.rating)

        # 排序并返回前N名
        top_brands = []
        for brand, data in sorted(brand_sales.items(), key=lambda x: x[1]['sales'], reverse=True)[:top_n]:
            avg_rating = round(sum(data['avg_rating']) / len(data['avg_rating']), 2) if data['avg_rating'] else None
            top_brands.append({
                'brand': brand,
                'sales_volume': data['sales'],
                'product_count': data['products'],
                'avg_rating': avg_rating
            })

        return top_brands

    def get_competitor_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成竞品分析摘要

        Args:
            analysis_result: 竞品分析结果

        Returns:
            摘要文本
        """
        top_performers = analysis_result.get('top_performers', [])
        benchmarks = analysis_result.get('benchmark_products', [])
        segments = analysis_result.get('competitor_segments', {})
        success_patterns = analysis_result.get('success_patterns', {})
        gaps = analysis_result.get('competitive_gaps', [])
        concentration = analysis_result.get('market_concentration', {})

        summary = f"""
竞品对标分析摘要
{'=' * 50}

市场集中度:
- CR4指数: {concentration.get('cr4', 'N/A')}%
- 垄断率: {concentration.get('monopoly_rate', 'N/A')}%
- 集中度水平: {concentration.get('concentration_level', '未知')}
- 市场结构: {concentration.get('market_structure', '未知')}
- 竞争强度: {concentration.get('competition_intensity', '未知')}
- 进入壁垒: {concentration.get('entry_barrier', '未知')}

头部产品:
- Top 20产品数: {len(top_performers)}
- 最高表现分: {top_performers[0]['performance_score'] if top_performers else 0}

标杆产品:
- 标杆产品数: {len(benchmarks)}
- 可对标参考产品: {min(5, len(benchmarks))} 个

竞品分层:
- 高端市场: {len(segments.get('high_end', []))} 个产品
- 中端市场: {len(segments.get('mid_range', []))} 个产品
- 低端市场: {len(segments.get('low_end', []))} 个产品
- 性价比产品: {len(segments.get('value_for_money', []))} 个产品

成功模式:
- 成功产品数: {success_patterns.get('count', 0)}
- 平均价格: ${success_patterns.get('avg_price', 0)}
- 平均评分: {success_patterns.get('avg_rating', 0)}
- 平均评论数: {success_patterns.get('avg_reviews', 0)}

竞争空白:
- 发现空白点: {len(gaps)} 个
"""

        if gaps:
            summary += "\n空白点详情:\n"
            for gap in gaps[:3]:
                summary += f"  - {gap['price_range']}: {gap['gap_type']} (机会等级: {gap['opportunity_level']})\n"

        return summary
