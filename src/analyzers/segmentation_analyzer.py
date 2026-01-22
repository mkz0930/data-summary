"""
市场细分分析器模块
分析不同细分市场的特征和机会
"""

from typing import List, Dict, Any
from collections import defaultdict

from src.database.models import Product
from src.utils.logger import get_logger


class SegmentationAnalyzer:
    """市场细分分析器"""

    def __init__(self):
        """初始化市场细分分析器"""
        self.logger = get_logger()

    def analyze(self, products: List[Product], sellerspirit_data=None) -> Dict[str, Any]:
        """
        综合市场细分分析

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据（可选，包含keyword_extensions）

        Returns:
            市场细分分析结果
        """
        self.logger.info(f"开始市场细分分析，产品数量: {len(products)}")

        result = {
            'price_segments': self._segment_by_price(products),
            'brand_segments': self._segment_by_brand(products),
            'rating_segments': self._segment_by_rating(products),
            'sales_segments': self._segment_by_sales(products),
            'keyword_segments': self._segment_by_keywords(sellerspirit_data),
            'segment_opportunities': self._identify_segment_opportunities(products)
        }

        self.logger.info("市场细分分析完成")
        return result

    def _segment_by_price(self, products: List[Product]) -> Dict[str, Any]:
        """
        按价格细分市场

        Args:
            products: 产品列表

        Returns:
            价格细分结果
        """
        if not products:
            return {
                'segments': {},
                'total_products': 0
            }

        # 定义价格区间
        price_ranges = {
            'budget': (0, 15),           # 预算型
            'economy': (15, 30),         # 经济型
            'mid_range': (30, 60),       # 中端
            'premium': (60, 100),        # 高端
            'luxury': (100, float('inf')) # 奢侈
        }

        segments = {}
        for segment_name, (min_price, max_price) in price_ranges.items():
            segment_products = [
                p for p in products
                if p.price and min_price <= p.price < max_price
            ]

            if segment_products:
                # 计算该细分市场的统计数据
                prices = [p.price for p in segment_products if p.price]
                sales = [p.sales_volume for p in segment_products if p.sales_volume]
                ratings = [p.rating for p in segment_products if p.rating]

                segments[segment_name] = {
                    'product_count': len(segment_products),
                    'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                    'total_sales': sum(sales),
                    'avg_sales': round(sum(sales) / len(sales), 2) if sales else 0,
                    'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
                    'market_share': round(len(segment_products) / len(products) * 100, 2)
                }

        return {
            'segments': segments,
            'total_products': len(products)
        }

    def _segment_by_brand(self, products: List[Product]) -> Dict[str, Any]:
        """
        按品牌细分市场

        Args:
            products: 产品列表

        Returns:
            品牌细分结果
        """
        if not products:
            return {
                'top_brands': [],
                'brand_count': 0,
                'branded_vs_generic': {}
            }

        # 统计品牌
        brand_stats = defaultdict(lambda: {
            'product_count': 0,
            'total_sales': 0,
            'avg_price': 0,
            'avg_rating': 0,
            'prices': [],
            'ratings': []
        })

        for product in products:
            brand = product.brand or "Unknown"
            brand_stats[brand]['product_count'] += 1
            brand_stats[brand]['total_sales'] += product.sales_volume or 0
            if product.price:
                brand_stats[brand]['prices'].append(product.price)
            if product.rating:
                brand_stats[brand]['ratings'].append(product.rating)

        # 计算平均值
        top_brands = []
        for brand, stats in brand_stats.items():
            prices = stats['prices']
            ratings = stats['ratings']

            top_brands.append({
                'brand': brand,
                'product_count': stats['product_count'],
                'total_sales': stats['total_sales'],
                'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
                'market_share': round(stats['product_count'] / len(products) * 100, 2)
            })

        # 按产品数量排序
        top_brands.sort(key=lambda x: x['product_count'], reverse=True)

        # 品牌 vs 通用产品
        branded_count = sum(1 for p in products if p.brand and p.brand != "Unknown")
        generic_count = len(products) - branded_count

        return {
            'top_brands': top_brands[:20],
            'brand_count': len(brand_stats),
            'branded_vs_generic': {
                'branded': branded_count,
                'generic': generic_count,
                'branded_rate': round(branded_count / len(products) * 100, 2) if products else 0
            }
        }

    def _segment_by_rating(self, products: List[Product]) -> Dict[str, Any]:
        """
        按评分细分市场

        Args:
            products: 产品列表

        Returns:
            评分细分结果
        """
        if not products:
            return {
                'segments': {},
                'total_products': 0
            }

        # 定义评分区间
        rating_ranges = {
            'excellent': (4.5, 5.0),     # 优秀
            'good': (4.0, 4.5),          # 良好
            'average': (3.5, 4.0),       # 一般
            'below_average': (3.0, 3.5), # 较差
            'poor': (0, 3.0)             # 差
        }

        segments = {}
        for segment_name, (min_rating, max_rating) in rating_ranges.items():
            segment_products = [
                p for p in products
                if p.rating and min_rating <= p.rating < max_rating
            ]

            if segment_products:
                prices = [p.price for p in segment_products if p.price]
                sales = [p.sales_volume for p in segment_products if p.sales_volume]
                reviews = [p.reviews_count for p in segment_products if p.reviews_count]

                segments[segment_name] = {
                    'product_count': len(segment_products),
                    'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                    'total_sales': sum(sales),
                    'avg_reviews': round(sum(reviews) / len(reviews), 2) if reviews else 0,
                    'market_share': round(len(segment_products) / len(products) * 100, 2)
                }

        return {
            'segments': segments,
            'total_products': len(products)
        }

    def _segment_by_sales(self, products: List[Product]) -> Dict[str, Any]:
        """
        按销量细分市场

        Args:
            products: 产品列表

        Returns:
            销量细分结果
        """
        if not products:
            return {
                'segments': {},
                'total_products': 0
            }

        # 定义销量区间
        sales_ranges = {
            'best_sellers': (500, float('inf')),  # 畅销品
            'popular': (100, 500),                # 热销品
            'moderate': (50, 100),                # 中等销量
            'slow_movers': (10, 50),              # 慢销品
            'poor_sellers': (0, 10)               # 滞销品
        }

        segments = {}
        for segment_name, (min_sales, max_sales) in sales_ranges.items():
            segment_products = [
                p for p in products
                if p.sales_volume and min_sales <= p.sales_volume < max_sales
            ]

            if segment_products:
                prices = [p.price for p in segment_products if p.price]
                ratings = [p.rating for p in segment_products if p.rating]
                total_sales = sum(p.sales_volume for p in segment_products if p.sales_volume)

                segments[segment_name] = {
                    'product_count': len(segment_products),
                    'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                    'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
                    'total_sales': total_sales,
                    'market_share': round(len(segment_products) / len(products) * 100, 2)
                }

        return {
            'segments': segments,
            'total_products': len(products)
        }

    def _segment_by_keywords(self, sellerspirit_data=None) -> Dict[str, Any]:
        """
        按关键词扩展细分市场

        分析卖家精灵提供的关键词扩展数据，识别不同的关键词细分市场

        Args:
            sellerspirit_data: 卖家精灵数据（包含keyword_extensions）

        Returns:
            关键词细分结果
        """
        if not sellerspirit_data:
            return {
                'total_keywords': 0,
                'segments': {},
                'high_potential_keywords': [],
                'niche_keywords': []
            }

        # 提取关键词扩展数据
        keyword_extensions = None
        if hasattr(sellerspirit_data, 'keyword_extensions'):
            keyword_extensions = sellerspirit_data.keyword_extensions
        elif isinstance(sellerspirit_data, dict):
            keyword_extensions = sellerspirit_data.get('keyword_extensions', [])

        if not keyword_extensions:
            return {
                'total_keywords': 0,
                'segments': {},
                'high_potential_keywords': [],
                'niche_keywords': []
            }

        # 按搜索量细分关键词
        search_volume_segments = {
            'high_volume': [],      # 高搜索量 (>10000)
            'medium_volume': [],    # 中等搜索量 (1000-10000)
            'low_volume': [],       # 低搜索量 (<1000)
        }

        high_potential_keywords = []
        niche_keywords = []

        for kw in keyword_extensions:
            keyword = kw.get('keyword', '')
            search_volume = kw.get('search_volume', 0)
            competition = kw.get('competition', 0)  # 竞争度
            relevance = kw.get('relevance', 0)      # 相关性

            kw_data = {
                'keyword': keyword,
                'search_volume': search_volume,
                'competition': competition,
                'relevance': relevance
            }

            # 按搜索量分类
            if search_volume > 10000:
                search_volume_segments['high_volume'].append(kw_data)
            elif search_volume > 1000:
                search_volume_segments['medium_volume'].append(kw_data)
            else:
                search_volume_segments['low_volume'].append(kw_data)

            # 识别高潜力关键词（高搜索量 + 低竞争）
            if search_volume > 1000 and competition < 50:
                high_potential_keywords.append({
                    **kw_data,
                    'potential_score': search_volume / (competition + 1)  # 潜力分数
                })

            # 识别利基关键词（中低搜索量 + 低竞争 + 高相关性）
            if 100 < search_volume < 5000 and competition < 30 and relevance > 70:
                niche_keywords.append(kw_data)

        # 排序高潜力关键词
        high_potential_keywords.sort(key=lambda x: x['potential_score'], reverse=True)

        return {
            'total_keywords': len(keyword_extensions),
            'segments': {
                'high_volume': {
                    'count': len(search_volume_segments['high_volume']),
                    'keywords': search_volume_segments['high_volume'][:10]  # 只返回前10个
                },
                'medium_volume': {
                    'count': len(search_volume_segments['medium_volume']),
                    'keywords': search_volume_segments['medium_volume'][:10]
                },
                'low_volume': {
                    'count': len(search_volume_segments['low_volume']),
                    'keywords': search_volume_segments['low_volume'][:10]
                }
            },
            'high_potential_keywords': high_potential_keywords[:20],  # 前20个高潜力关键词
            'niche_keywords': niche_keywords[:20]  # 前20个利基关键词
        }

    def _identify_segment_opportunities(
        self,
        products: List[Product]
    ) -> List[Dict[str, Any]]:
        """
        识别细分市场机会

        通过交叉分析价格、评分、销量等维度，找出机会细分市场

        Args:
            products: 产品列表

        Returns:
            细分市场机会列表
        """
        if not products:
            return []

        opportunities = []

        # 机会1: 高价格 + 低竞争
        high_price_products = [p for p in products if p.price and p.price >= 50]
        if len(high_price_products) < len(products) * 0.2:  # 高价产品少于20%
            opportunities.append({
                'segment': '高端市场',
                'opportunity_type': '低竞争',
                'description': '高价格段产品数量较少，存在进入机会',
                'product_count': len(high_price_products),
                'avg_price': round(sum(p.price for p in high_price_products) / len(high_price_products), 2) if high_price_products else 0
            })

        # 机会2: 高评分 + 低价格（性价比市场）
        value_products = [
            p for p in products
            if p.price and p.rating and p.price < 30 and p.rating >= 4.0
        ]
        if len(value_products) < len(products) * 0.15:  # 性价比产品少于15%
            opportunities.append({
                'segment': '性价比市场',
                'opportunity_type': '供给不足',
                'description': '高性价比产品数量较少，市场需求可能未被满足',
                'product_count': len(value_products),
                'avg_price': round(sum(p.price for p in value_products) / len(value_products), 2) if value_products else 0
            })

        # 机会3: 中等价格 + 高销量（主流市场）
        mainstream_products = [
            p for p in products
            if p.price and p.sales_volume and 20 <= p.price <= 50 and p.sales_volume >= 100
        ]
        if mainstream_products:
            opportunities.append({
                'segment': '主流市场',
                'opportunity_type': '成熟市场',
                'description': '中等价格段销量表现良好，市场需求旺盛',
                'product_count': len(mainstream_products),
                'avg_price': round(sum(p.price for p in mainstream_products) / len(mainstream_products), 2),
                'total_sales': sum(p.sales_volume for p in mainstream_products)
            })

        # 机会4: 新品市场（评论数少但评分高）
        new_opportunity_products = [
            p for p in products
            if p.rating and p.reviews_count and p.rating >= 4.0 and p.reviews_count < 50
        ]
        if len(new_opportunity_products) >= len(products) * 0.1:  # 新品机会产品超过10%
            opportunities.append({
                'segment': '新品市场',
                'opportunity_type': '快速增长',
                'description': '存在较多高评分新品，市场处于快速增长期',
                'product_count': len(new_opportunity_products),
                'avg_rating': round(sum(p.rating for p in new_opportunity_products) / len(new_opportunity_products), 2)
            })

        return opportunities

    def get_segmentation_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成市场细分分析摘要

        Args:
            analysis_result: 市场细分分析结果

        Returns:
            摘要文本
        """
        price_segments = analysis_result.get('price_segments', {}).get('segments', {})
        brand_segments = analysis_result.get('brand_segments', {})
        rating_segments = analysis_result.get('rating_segments', {}).get('segments', {})
        sales_segments = analysis_result.get('sales_segments', {}).get('segments', {})
        keyword_segments = analysis_result.get('keyword_segments', {})
        opportunities = analysis_result.get('segment_opportunities', [])

        summary = f"""
市场细分分析摘要
{'=' * 50}

价格细分:
- 预算型 ($0-15): {price_segments.get('budget', {}).get('product_count', 0)} 个产品
- 经济型 ($15-30): {price_segments.get('economy', {}).get('product_count', 0)} 个产品
- 中端 ($30-60): {price_segments.get('mid_range', {}).get('product_count', 0)} 个产品
- 高端 ($60-100): {price_segments.get('premium', {}).get('product_count', 0)} 个产品
- 奢侈 ($100+): {price_segments.get('luxury', {}).get('product_count', 0)} 个产品

品牌细分:
- 总品牌数: {brand_segments.get('brand_count', 0)}
- 品牌产品占比: {brand_segments.get('branded_vs_generic', {}).get('branded_rate', 0)}%
- Top 5品牌:
"""

        top_brands = brand_segments.get('top_brands', [])[:5]
        for i, brand in enumerate(top_brands, 1):
            summary += f"  {i}. {brand['brand']}: {brand['product_count']} 个产品 (市场份额: {brand['market_share']}%)\n"

        summary += f"""
评分细分:
- 优秀 (4.5+): {rating_segments.get('excellent', {}).get('product_count', 0)} 个产品
- 良好 (4.0-4.5): {rating_segments.get('good', {}).get('product_count', 0)} 个产品
- 一般 (3.5-4.0): {rating_segments.get('average', {}).get('product_count', 0)} 个产品

销量细分:
- 畅销品 (500+): {sales_segments.get('best_sellers', {}).get('product_count', 0)} 个产品
- 热销品 (100-500): {sales_segments.get('popular', {}).get('product_count', 0)} 个产品
- 中等销量 (50-100): {sales_segments.get('moderate', {}).get('product_count', 0)} 个产品

关键词细分:
- 总关键词数: {keyword_segments.get('total_keywords', 0)}
- 高搜索量关键词: {keyword_segments.get('segments', {}).get('high_volume', {}).get('count', 0)}
- 中等搜索量关键词: {keyword_segments.get('segments', {}).get('medium_volume', {}).get('count', 0)}
- 低搜索量关键词: {keyword_segments.get('segments', {}).get('low_volume', {}).get('count', 0)}
- 高潜力关键词: {len(keyword_segments.get('high_potential_keywords', []))}
- 利基关键词: {len(keyword_segments.get('niche_keywords', []))}

细分市场机会:
- 发现机会: {len(opportunities)} 个
"""

        if opportunities:
            summary += "\n机会详情:\n"
            for opp in opportunities[:3]:
                summary += f"  - {opp['segment']}: {opp['opportunity_type']} - {opp['description']}\n"

        return summary
