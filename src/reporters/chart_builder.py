"""
图表构建器模块
生成Plotly.js图表配置
"""

import json
from typing import List, Dict, Any

from src.database.models import Product
from src.utils.logger import get_logger


class ChartBuilder:
    """图表构建器"""

    def __init__(self):
        """初始化图表构建器"""
        self.logger = get_logger()

    def build_price_distribution_chart(
        self,
        price_bands: List[Dict[str, Any]]
    ) -> str:
        """
        构建价格分布柱状图

        Args:
            price_bands: 价格带数据

        Returns:
            Plotly图表JSON字符串
        """
        labels = [band['band'] for band in price_bands]
        values = [band['count'] for band in price_bands]

        chart_config = {
            'data': [{
                'type': 'bar',
                'x': labels,
                'y': values,
                'marker': {
                    'color': 'rgb(55, 83, 109)'
                },
                'text': values,
                'textposition': 'auto'
            }],
            'layout': {
                'title': '价格分布',
                'xaxis': {'title': '价格区间'},
                'yaxis': {'title': '产品数量'},
                'hovermode': 'closest'
            }
        }

        return json.dumps(chart_config)

    def build_brand_concentration_chart(
        self,
        brand_data: List[Dict[str, Any]],
        top_n: int = 10
    ) -> str:
        """
        构建品牌集中度饼图

        Args:
            brand_data: 品牌数据
            top_n: 显示前N个品牌

        Returns:
            Plotly图表JSON字符串
        """
        top_brands = brand_data[:top_n]
        labels = [brand['brand'] for brand in top_brands]
        values = [brand['count'] for brand in top_brands]

        chart_config = {
            'data': [{
                'type': 'pie',
                'labels': labels,
                'values': values,
                'textinfo': 'label+percent',
                'hoverinfo': 'label+value+percent'
            }],
            'layout': {
                'title': f'品牌集中度 (Top {top_n})'
            }
        }

        return json.dumps(chart_config)

    def build_price_rating_scatter(
        self,
        products: List[Product]
    ) -> str:
        """
        构建价格-评分散点图

        Args:
            products: 产品列表

        Returns:
            Plotly图表JSON字符串
        """
        # 筛选有效数据
        valid_products = [p for p in products
                         if p.price and p.rating and p.reviews_count]

        prices = [p.price for p in valid_products]
        ratings = [p.rating for p in valid_products]
        reviews = [p.reviews_count for p in valid_products]
        names = [p.name[:30] + '...' if len(p.name) > 30 else p.name
                for p in valid_products]

        chart_config = {
            'data': [{
                'type': 'scatter',
                'mode': 'markers',
                'x': prices,
                'y': ratings,
                'marker': {
                    'size': [min(r / 100, 50) for r in reviews],  # 气泡大小
                    'color': reviews,
                    'colorscale': 'Viridis',
                    'showscale': True,
                    'colorbar': {'title': '评论数'}
                },
                'text': names,
                'hovertemplate': '<b>%{text}</b><br>价格: $%{x}<br>评分: %{y}<br>评论数: %{marker.color}<extra></extra>'
            }],
            'layout': {
                'title': '价格-评分散点图',
                'xaxis': {'title': '价格 ($)'},
                'yaxis': {'title': '评分'},
                'hovermode': 'closest'
            }
        }

        return json.dumps(chart_config)

    def build_new_product_trend_chart(
        self,
        monthly_counts: Dict[str, int]
    ) -> str:
        """
        构建新品趋势折线图

        Args:
            monthly_counts: 月度新品数量

        Returns:
            Plotly图表JSON字符串
        """
        months = list(monthly_counts.keys())
        counts = list(monthly_counts.values())

        chart_config = {
            'data': [{
                'type': 'scatter',
                'mode': 'lines+markers',
                'x': months,
                'y': counts,
                'line': {'color': 'rgb(75, 192, 192)'},
                'marker': {'size': 8}
            }],
            'layout': {
                'title': '新品趋势',
                'xaxis': {'title': '月份'},
                'yaxis': {'title': '新品数量'},
                'hovermode': 'closest'
            }
        }

        return json.dumps(chart_config)

    def build_new_product_price_distribution(
        self,
        new_products: List[Product],
        price_ranges: List[float]
    ) -> str:
        """
        构建新品价格分布柱状图

        Args:
            new_products: 新品列表
            price_ranges: 价格区间

        Returns:
            Plotly图表JSON字符串
        """
        # 统计各价格区间的新品数量
        band_counts = {}
        for i in range(len(price_ranges) - 1):
            band_name = self._format_price_band(price_ranges, i)
            band_counts[band_name] = 0

        for product in new_products:
            if not product.price or product.price <= 0:
                continue

            for i in range(len(price_ranges) - 1):
                if price_ranges[i] <= product.price < price_ranges[i + 1]:
                    band_name = self._format_price_band(price_ranges, i)
                    band_counts[band_name] += 1
                    break

        labels = list(band_counts.keys())
        values = list(band_counts.values())

        chart_config = {
            'data': [{
                'type': 'bar',
                'x': labels,
                'y': values,
                'marker': {
                    'color': 'rgb(142, 124, 195)'
                },
                'text': values,
                'textposition': 'auto'
            }],
            'layout': {
                'title': '新品价格分布',
                'xaxis': {'title': '价格区间'},
                'yaxis': {'title': '新品数量'},
                'hovermode': 'closest'
            }
        }

        return json.dumps(chart_config)

    def build_rating_distribution_chart(
        self,
        products: List[Product]
    ) -> str:
        """
        构建评分分布柱状图

        Args:
            products: 产品列表

        Returns:
            Plotly图表JSON字符串
        """
        # 统计各评分区间的产品数量
        rating_counts = {
            '5星': 0,
            '4-5星': 0,
            '3-4星': 0,
            '2-3星': 0,
            '1-2星': 0
        }

        for product in products:
            if not product.rating:
                continue

            if product.rating >= 4.5:
                rating_counts['5星'] += 1
            elif product.rating >= 4.0:
                rating_counts['4-5星'] += 1
            elif product.rating >= 3.0:
                rating_counts['3-4星'] += 1
            elif product.rating >= 2.0:
                rating_counts['2-3星'] += 1
            else:
                rating_counts['1-2星'] += 1

        labels = list(rating_counts.keys())
        values = list(rating_counts.values())

        chart_config = {
            'data': [{
                'type': 'bar',
                'x': labels,
                'y': values,
                'marker': {
                    'color': ['#4CAF50', '#8BC34A', '#FFC107', '#FF9800', '#F44336']
                },
                'text': values,
                'textposition': 'auto'
            }],
            'layout': {
                'title': '评分分布',
                'xaxis': {'title': '评分区间'},
                'yaxis': {'title': '产品数量'},
                'hovermode': 'closest'
            }
        }

        return json.dumps(chart_config)

    def build_keyword_opportunity_chart(
        self,
        keyword_data: List[Dict[str, Any]],
        top_n: int = 10
    ) -> str:
        """
        构建关键词机会柱状图

        Args:
            keyword_data: 关键词数据
            top_n: 显示前N个关键词

        Returns:
            Plotly图表JSON字符串
        """
        top_keywords = keyword_data[:top_n]
        labels = [kw['keyword'] for kw in top_keywords]
        values = [kw['opportunity_index'] for kw in top_keywords]

        chart_config = {
            'data': [{
                'type': 'bar',
                'x': labels,
                'y': values,
                'marker': {
                    'color': 'rgb(26, 118, 255)'
                },
                'text': [f"{v:.0f}" for v in values],
                'textposition': 'auto'
            }],
            'layout': {
                'title': f'关键词机会指数 (Top {top_n})',
                'xaxis': {'title': '关键词', 'tickangle': -45},
                'yaxis': {'title': '机会指数'},
                'hovermode': 'closest',
                'margin': {'b': 120}
            }
        }

        return json.dumps(chart_config)

    def build_reviews_distribution_chart(
        self,
        products: List[Product]
    ) -> str:
        """
        构建评论数分布直方图

        Args:
            products: 产品列表

        Returns:
            Plotly图表JSON字符串
        """
        reviews = [p.reviews_count for p in products if p.reviews_count]

        chart_config = {
            'data': [{
                'type': 'histogram',
                'x': reviews,
                'nbinsx': 20,
                'marker': {
                    'color': 'rgb(100, 200, 102)'
                }
            }],
            'layout': {
                'title': '评论数分布',
                'xaxis': {'title': '评论数'},
                'yaxis': {'title': '产品数量'},
                'hovermode': 'closest'
            }
        }

        return json.dumps(chart_config)

    def _format_price_band(self, price_ranges: List[float], index: int) -> str:
        """
        格式化价格带名称

        Args:
            price_ranges: 价格区间列表
            index: 索引

        Returns:
            格式化的价格带名称
        """
        if index >= len(price_ranges) - 1:
            return f"${price_ranges[-2]}+"

        lower = price_ranges[index]
        upper = price_ranges[index + 1]

        if upper >= 999999:
            return f"${lower}+"
        else:
            return f"${lower}-${upper}"

    def build_all_charts(
        self,
        products: List[Product],
        new_products: List[Product],
        analysis_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        构建所有图表

        Args:
            products: 产品列表
            new_products: 新品列表
            analysis_data: 分析数据

        Returns:
            图表JSON字符串字典
        """
        self.logger.info("开始构建所有图表")

        charts = {}

        # 价格分布图
        price_bands = (analysis_data.get('price_analysis', {})
                      .get('distribution', {})
                      .get('bands', []))
        if price_bands:
            charts['price_distribution'] = self.build_price_distribution_chart(price_bands)

        # 品牌集中度图
        brand_data = (analysis_data.get('market_analysis', {})
                     .get('brand_concentration', {})
                     .get('top_brands', []))
        if brand_data:
            charts['brand_concentration'] = self.build_brand_concentration_chart(brand_data)

        # 价格-评分散点图
        if products:
            charts['price_rating_scatter'] = self.build_price_rating_scatter(products)

        # 新品趋势图
        monthly_counts = (analysis_data.get('lifecycle_analysis', {})
                         .get('trend', {})
                         .get('monthly_counts', {}))
        if monthly_counts:
            charts['new_product_trend'] = self.build_new_product_trend_chart(monthly_counts)

        # 新品价格分布图
        if new_products:
            price_ranges = [0, 20, 50, 100, 999999]  # 默认价格区间
            charts['new_product_price'] = self.build_new_product_price_distribution(
                new_products, price_ranges
            )

        # 评分分布图
        if products:
            charts['rating_distribution'] = self.build_rating_distribution_chart(products)

        # 关键词机会图
        keyword_data = (analysis_data.get('keyword_analysis', {})
                       .get('long_tail_opportunities', []))
        if keyword_data:
            charts['keyword_opportunities'] = self.build_keyword_opportunity_chart(keyword_data)

        # 评论数分布图
        if products:
            charts['reviews_distribution'] = self.build_reviews_distribution_chart(products)

        self.logger.info(f"成功构建 {len(charts)} 个图表")
        return charts
