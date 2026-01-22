"""
CSV导出器模块
导出各类分析数据到CSV文件
"""

import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from src.database.models import Product
from src.utils.logger import get_logger


class CSVExporter:
    """CSV导出器"""

    def __init__(self, output_dir: Path):
        """
        初始化CSV导出器

        Args:
            output_dir: 输出目录
        """
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_products(
        self,
        products: List[Product],
        filename: str = "products.csv"
    ) -> str:
        """
        导出产品数据

        Args:
            products: 产品列表
            filename: 文件名

        Returns:
            导出文件路径
        """
        filepath = self.output_dir / filename
        self.logger.info(f"导出产品数据到: {filepath}")

        headers = [
            'ASIN', '产品名称', '品牌', '分类', '价格', '评分', '评论数',
            '销量', 'BSR排名', '上架时间', '是否异常'
        ]

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for product in products:
                writer.writerow([
                    product.asin,
                    product.name,
                    product.brand or '',
                    product.category or '',
                    product.price or '',
                    product.rating or '',
                    product.reviews_count or '',
                    product.sales_volume or '',
                    product.bsr_rank or '',
                    product.available_date or '',
                    '是' if product.has_anomaly else '否'
                ])

        self.logger.info(f"成功导出 {len(products)} 个产品")
        return str(filepath)

    def export_new_products(
        self,
        new_products: List[Product],
        filename: str = "new_products.csv"
    ) -> str:
        """
        导出新品数据

        Args:
            new_products: 新品列表
            filename: 文件名

        Returns:
            导出文件路径
        """
        filepath = self.output_dir / filename
        self.logger.info(f"导出新品数据到: {filepath}")

        headers = [
            'ASIN', '产品名称', '品牌', '价格', '评分', '评论数',
            'BSR排名', '上架时间', '上架天数'
        ]

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for product in new_products:
                # 计算上架天数
                days_since_launch = ''
                if product.available_date:
                    try:
                        available_date = datetime.fromisoformat(
                            product.available_date.replace('Z', '+00:00')
                        )
                        days_since_launch = (datetime.now() - available_date).days
                    except:
                        pass

                writer.writerow([
                    product.asin,
                    product.name,
                    product.brand or '',
                    product.price or '',
                    product.rating or '',
                    product.reviews_count or '',
                    product.bsr_rank or '',
                    product.available_date or '',
                    days_since_launch
                ])

        self.logger.info(f"成功导出 {len(new_products)} 个新品")
        return str(filepath)

    def export_analysis_summary(
        self,
        analysis_data: Dict[str, Any],
        filename: str = "analysis_summary.csv"
    ) -> str:
        """
        导出分析摘要

        Args:
            analysis_data: 分析数据字典
            filename: 文件名

        Returns:
            导出文件路径
        """
        filepath = self.output_dir / filename
        self.logger.info(f"导出分析摘要到: {filepath}")

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['指标', '数值'])

            # 市场规模
            market_size = analysis_data.get('market_analysis', {}).get('market_size', {})
            writer.writerow(['总ASIN数', market_size.get('total_asins', 0)])
            writer.writerow(['月搜索量', market_size.get('monthly_searches', 0)])
            writer.writerow(['市场类型', market_size.get('size_rating', '')])

            # 竞争强度
            competition = analysis_data.get('market_analysis', {}).get('competition', {})
            writer.writerow(['竞争强度', competition.get('intensity', '')])
            writer.writerow(['平均评论数', competition.get('average_reviews', 0)])
            writer.writerow(['平均评分', competition.get('average_rating', 0)])

            # 品牌集中度
            brand_conc = analysis_data.get('market_analysis', {}).get('brand_concentration', {})
            writer.writerow(['总品牌数', brand_conc.get('total_brands', 0)])
            writer.writerow(['CR4', f"{brand_conc.get('cr4', 0)}%"])
            writer.writerow(['CR10', f"{brand_conc.get('cr10', 0)}%"])

            # 市场机会
            writer.writerow(['市场空白指数', analysis_data.get('market_analysis', {}).get('market_blank_index', 0)])

            # 新品机会
            lifecycle = analysis_data.get('lifecycle_analysis', {})
            writer.writerow(['新品数量', lifecycle.get('new_product_count', 0)])
            writer.writerow(['新品趋势', lifecycle.get('trend', {}).get('trend_direction', '')])

            # 价格分析
            price_stats = analysis_data.get('price_analysis', {}).get('statistics', {})
            writer.writerow(['平均价格', f"${price_stats.get('mean', 0)}"])
            writer.writerow(['价格中位数', f"${price_stats.get('median', 0)}"])

        self.logger.info("成功导出分析摘要")
        return str(filepath)

    def export_brand_ranking(
        self,
        brand_data: List[Dict[str, Any]],
        filename: str = "brand_ranking.csv"
    ) -> str:
        """
        导出品牌排名

        Args:
            brand_data: 品牌数据列表
            filename: 文件名

        Returns:
            导出文件路径
        """
        filepath = self.output_dir / filename
        self.logger.info(f"导出品牌排名到: {filepath}")

        headers = ['排名', '品牌', '产品数量', '市场份额(%)']

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for i, brand in enumerate(brand_data, 1):
                writer.writerow([
                    i,
                    brand.get('brand', ''),
                    brand.get('count', 0),
                    brand.get('share', 0)
                ])

        self.logger.info(f"成功导出 {len(brand_data)} 个品牌")
        return str(filepath)

    def export_keyword_opportunities(
        self,
        keyword_data: List[Dict[str, Any]],
        filename: str = "keyword_opportunities.csv"
    ) -> str:
        """
        导出关键词机会

        Args:
            keyword_data: 关键词数据列表
            filename: 文件名

        Returns:
            导出文件路径
        """
        filepath = self.output_dir / filename
        self.logger.info(f"导出关键词机会到: {filepath}")

        headers = ['关键词', '月搜索量', '竞品数量', '机会指数']

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for kw in keyword_data:
                writer.writerow([
                    kw.get('keyword', ''),
                    kw.get('searches', 0),
                    kw.get('products', 0),
                    kw.get('opportunity_index', 0)
                ])

        self.logger.info(f"成功导出 {len(keyword_data)} 个关键词")
        return str(filepath)

    def export_price_distribution(
        self,
        price_bands: List[Dict[str, Any]],
        filename: str = "price_distribution.csv"
    ) -> str:
        """
        导出价格分布

        Args:
            price_bands: 价格带数据列表
            filename: 文件名

        Returns:
            导出文件路径
        """
        filepath = self.output_dir / filename
        self.logger.info(f"导出价格分布到: {filepath}")

        headers = ['价格区间', '产品数量', '占比(%)']

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for band in price_bands:
                writer.writerow([
                    band.get('band', ''),
                    band.get('count', 0),
                    band.get('percentage', 0)
                ])

        self.logger.info(f"成功导出 {len(price_bands)} 个价格区间")
        return str(filepath)

    def export_all(
        self,
        products: List[Product],
        new_products: List[Product],
        analysis_data: Dict[str, Any],
        timestamp: str = None
    ) -> Dict[str, str]:
        """
        导出所有数据

        Args:
            products: 产品列表
            new_products: 新品列表
            analysis_data: 分析数据
            timestamp: 时间戳（用于文件名）

        Returns:
            导出文件路径字典
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        self.logger.info("开始导出所有数据")

        exported_files = {}

        # 导出产品数据
        exported_files['products'] = self.export_products(
            products,
            f"products_{timestamp}.csv"
        )

        # 导出新品数据
        if new_products:
            exported_files['new_products'] = self.export_new_products(
                new_products,
                f"new_products_{timestamp}.csv"
            )

        # 导出分析摘要
        exported_files['summary'] = self.export_analysis_summary(
            analysis_data,
            f"analysis_summary_{timestamp}.csv"
        )

        # 导出品牌排名
        brand_data = (analysis_data.get('market_analysis', {})
                     .get('brand_concentration', {})
                     .get('top_brands', []))
        if brand_data:
            exported_files['brands'] = self.export_brand_ranking(
                brand_data,
                f"brand_ranking_{timestamp}.csv"
            )

        # 导出关键词机会
        keyword_data = (analysis_data.get('keyword_analysis', {})
                       .get('long_tail_opportunities', []))
        if keyword_data:
            exported_files['keywords'] = self.export_keyword_opportunities(
                keyword_data,
                f"keyword_opportunities_{timestamp}.csv"
            )

        # 导出价格分布
        price_bands = (analysis_data.get('price_analysis', {})
                      .get('distribution', {})
                      .get('bands', []))
        if price_bands:
            exported_files['price_distribution'] = self.export_price_distribution(
                price_bands,
                f"price_distribution_{timestamp}.csv"
            )

        self.logger.info(f"成功导出 {len(exported_files)} 个文件")
        return exported_files
