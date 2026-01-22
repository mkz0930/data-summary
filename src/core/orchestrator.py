"""
流程编排器模块
协调所有模块的执行，实现完整的分析流程
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
from src.database.models import Product, AnalysisResult
from src.collectors.asin_collector import ASINCollector
from src.collectors.price_collector import PriceCollector
from src.collectors.sellerspirit_collector import SellerSpiritCollector
from src.validators.category_validator import CategoryValidator
from src.validators.gemini_validator import GeminiCategoryValidator
from src.validators.model_comparator import ModelComparator
from src.validators.data_quality_checker import DataQualityChecker
from src.analyzers.market_analyzer import MarketAnalyzer
from src.analyzers.lifecycle_analyzer import LifecycleAnalyzer
from src.analyzers.price_analyzer import PriceAnalyzer
from src.analyzers.keyword_analyzer import KeywordAnalyzer
from src.reporters.chart_builder import ChartBuilder
from src.reporters.html_generator import HTMLGenerator
from src.reporters.csv_exporter import CSVExporter
from src.utils.logger import get_logger


class Orchestrator:
    """流程编排器"""

    def __init__(self, config: ConfigManager):
        """
        初始化流程编排器

        Args:
            config: 配置管理器
        """
        self.config = config
        self.logger = get_logger()
        self.db = DatabaseManager(config.database_path)

        # 初始化各模块
        self._init_modules()

    def _init_modules(self):
        """初始化所有模块"""
        self.logger.info("初始化模块...")

        # 数据采集模块
        self.asin_collector = ASINCollector(
            api_key=self.config.scraperapi_key,
            max_concurrent=10
        )
        self.price_collector = PriceCollector(
            api_key=self.config.scraperapi_key
        )
        self.sellerspirit_collector = SellerSpiritCollector()

        # 数据校验模块
        self.category_validator = CategoryValidator(
            api_key=self.config.anthropic_api_key,
            db_manager=self.db
        )
        self.gemini_validator = GeminiCategoryValidator(
            api_key=self.config.google_api_key,
            db_manager=self.db
        )
        self.model_comparator = ModelComparator()
        self.quality_checker = DataQualityChecker()

        # 数据分析模块
        self.market_analyzer = MarketAnalyzer()
        self.lifecycle_analyzer = LifecycleAnalyzer(
            new_product_days=self.config.new_product_days,
            new_product_min_reviews=self.config.new_product_min_reviews,
            new_product_max_bsr=self.config.new_product_max_bsr
        )
        self.price_analyzer = PriceAnalyzer(
            price_ranges=self.config.price_ranges,
            main_band_threshold=self.config.main_price_band_threshold
        )
        self.keyword_analyzer = KeywordAnalyzer()

        # 报告生成模块
        self.chart_builder = ChartBuilder()
        self.html_generator = HTMLGenerator(self.config.reports_dir)
        self.csv_exporter = CSVExporter(self.config.exports_dir)

        self.logger.info("模块初始化完成")

    def run(
        self,
        keyword: Optional[str] = None,
        skip_collection: bool = False,
        skip_validation: bool = False,
        force_reanalysis: bool = False
    ) -> Dict[str, Any]:
        """
        运行完整的分析流程

        Args:
            keyword: 搜索关键词（如果为None则使用配置文件中的关键词）
            skip_collection: 是否跳过数据采集（使用数据库中的数据）
            skip_validation: 是否跳过AI分类校验
            force_reanalysis: 是否强制重新分析（即使已有分析结果）

        Returns:
            分析结果字典
        """
        keyword = keyword or self.config.keyword
        self.logger.info(f"=" * 60)
        self.logger.info(f"开始分析流程: {keyword}")
        self.logger.info(f"=" * 60)

        # 检查是否已经分析过该关键词
        if not force_reanalysis:
            existing_result = self.db.get_analysis_result(keyword)
            if existing_result:
                self.logger.info(f"关键词 '{keyword}' 已在 {existing_result.created_at} 分析过，跳过重复分析")
                self.logger.info(f"  - 市场空白指数: {existing_result.market_blank_index}")
                self.logger.info(f"  - 新品数量: {existing_result.new_product_count}")
                self.logger.info(f"  - 报告路径: {existing_result.report_path}")
                self.logger.info("提示: 如需重新分析，请使用 force_reanalysis=True 参数")

                # 解析分析数据
                analysis_data = json.loads(existing_result.analysis_data) if existing_result.analysis_data else {}

                return {
                    'success': True,
                    'keyword': keyword,
                    'from_cache': True,
                    'analyzed_at': existing_result.created_at,
                    'market_blank_index': existing_result.market_blank_index,
                    'new_product_count': existing_result.new_product_count,
                    'analysis_data': analysis_data,
                    'report_paths': {'html_report': existing_result.report_path}
                }

        try:
            # 步骤1: 数据采集
            if not skip_collection:
                products = self._collect_data(keyword)
            else:
                self.logger.info("跳过数据采集，从数据库加载数据")
                products = self.db.get_all_products()

            if not products:
                raise ValueError("没有产品数据可供分析")

            # 步骤2: 数据校验
            if not skip_validation:
                self._validate_data(products, keyword)

            # 步骤3: 数据质量检查
            self._check_data_quality(products)

            # 步骤4: 数据分析
            analysis_data = self._analyze_data(products, keyword)

            # 步骤5: 生成报告
            report_paths = self._generate_reports(keyword, products, analysis_data)

            # 步骤6: 保存分析结果
            self._save_analysis_result(keyword, analysis_data, report_paths)

            self.logger.info(f"=" * 60)
            self.logger.info(f"分析流程完成!")
            self.logger.info(f"=" * 60)

            return {
                'success': True,
                'keyword': keyword,
                'total_products': len(products),
                'analysis_data': analysis_data,
                'report_paths': report_paths
            }

        except Exception as e:
            self.logger.error(f"分析流程失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _collect_data(self, keyword: str) -> list:
        """
        数据采集阶段

        Args:
            keyword: 搜索关键词

        Returns:
            产品列表
        """
        self.logger.info("=" * 60)
        self.logger.info("步骤1: 数据采集")
        self.logger.info("=" * 60)

        # 1.1 采集ASIN
        self.logger.info(f"1.1 采集ASIN (关键词: {keyword})")
        products = self.asin_collector.collect_asins(
            keyword=keyword,
            max_pages=self.config.max_asin,
            sales_threshold=self.config.sales_threshold,
            fetch_details=False
        )
        self.logger.info(f"采集到 {len(products)} 个产品")

        # 保存到数据库
        for product in products:
            self.db.insert_product(product)

        # 1.2 补充价格数据
        self.logger.info("1.2 补充缺失的价格数据")
        products_without_price = [p for p in products if not p.price]
        if products_without_price:
            self.price_collector.update_prices(products_without_price)
            for product in products_without_price:
                self.db.insert_product(product)

        # 1.3 采集卖家精灵数据
        self.logger.info("1.3 采集卖家精灵数据")
        try:
            sellerspirit_data = self.sellerspirit_collector.collect(keyword)
            if sellerspirit_data:
                self.db.insert_sellerspirit_data(sellerspirit_data)
        except Exception as e:
            self.logger.warning(f"卖家精灵数据采集失败: {e}")

        return products

    def _validate_data(self, products: list, keyword: str):
        """
        数据校验阶段

        Args:
            products: 产品列表
            keyword: 搜索关键词
        """
        self.logger.info("=" * 60)
        self.logger.info("步骤2: 数据校验")
        self.logger.info("=" * 60)

        # 2.1 Claude AI分类校验
        self.logger.info("2.1 Claude AI分类校验")
        claude_validations = self.category_validator.validate_batch(products, keyword)

        # 保存Claude验证结果
        for validation in claude_validations:
            self.db.insert_category_validation(validation)

        # 统计Claude结果
        claude_stats = self.category_validator.get_statistics(claude_validations)
        self.logger.info(f"[Claude] 相关产品: {claude_stats['relevant']}/{claude_stats['total']}")
        self.logger.info(f"[Claude] 分类正确: {claude_stats['correct_category']}/{claude_stats['total']}")

        # 2.2 Gemini AI分类校验
        self.logger.info("2.2 Gemini AI分类校验")
        gemini_validations = self.gemini_validator.validate_batch(products, keyword)

        # 统计Gemini结果
        gemini_stats = self.gemini_validator.get_statistics(gemini_validations)
        self.logger.info(f"[Gemini] 相关产品: {gemini_stats['relevant']}/{gemini_stats['total']}")
        self.logger.info(f"[Gemini] 分类正确: {gemini_stats['correct_category']}/{gemini_stats['total']}")

        # 2.3 对比两个模型的结果
        if claude_validations and gemini_validations:
            self.logger.info("2.3 对比两个模型的结果")
            comparison_result = self.model_comparator.compare_validations(
                claude_validations, gemini_validations
            )

            # 输出对比摘要
            self.logger.info(self.model_comparator.get_comparison_summary(comparison_result))

            # 导出不一致的ASIN到CSV
            if comparison_result['disagreement_asins']:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_path = self.config.exports_dir / f"model_disagreements_{keyword}_{timestamp}.csv"
                self.model_comparator.export_disagreements_to_csv(comparison_result, str(csv_path))
                self.logger.info(f"不一致的ASIN已导出到: {csv_path}")

            # 保存对比结果到数据库（可选）
            self.db.save_model_comparison(keyword, comparison_result)

    def _check_data_quality(self, products: list):
        """
        数据质量检查阶段

        Args:
            products: 产品列表
        """
        self.logger.info("=" * 60)
        self.logger.info("步骤3: 数据质量检查")
        self.logger.info("=" * 60)

        # 检查数据质量
        quality_result = self.quality_checker.check_batch(products)
        self.logger.info(f"平均质量分: {quality_result['average_quality_score']}/100")
        self.logger.info(f"有问题的产品: {quality_result['products_with_issues']}")

        # 标记异常产品
        self.quality_checker.mark_anomalies(products)

        # 更新数据库
        for product in products:
            if product.has_anomaly:
                self.db.update_product(product)

    def _analyze_data(self, products: list, keyword: str) -> Dict[str, Any]:
        """
        数据分析阶段

        Args:
            products: 产品列表
            keyword: 搜索关键词

        Returns:
            分析数据字典
        """
        self.logger.info("=" * 60)
        self.logger.info("步骤4: 数据分析")
        self.logger.info("=" * 60)

        # 获取卖家精灵数据
        sellerspirit_data = self.db.get_sellerspirit_data(keyword)

        # 4.1 市场分析
        self.logger.info("4.1 市场分析")
        market_analysis = self.market_analyzer.analyze(products, sellerspirit_data)

        # 4.2 生命周期分析
        self.logger.info("4.2 生命周期分析")
        lifecycle_analysis = self.lifecycle_analyzer.analyze(products)

        # 4.3 价格分析
        self.logger.info("4.3 价格分析")
        price_analysis = self.price_analyzer.analyze(products)

        # 4.4 关键词分析
        self.logger.info("4.4 关键词分析")
        keyword_analysis = self.keyword_analyzer.analyze(sellerspirit_data, keyword)

        return {
            'market_analysis': market_analysis,
            'lifecycle_analysis': lifecycle_analysis,
            'price_analysis': price_analysis,
            'keyword_analysis': keyword_analysis
        }

    def _generate_reports(
        self,
        keyword: str,
        products: list,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        生成报告阶段

        Args:
            keyword: 搜索关键词
            products: 产品列表
            analysis_data: 分析数据

        Returns:
            报告文件路径字典
        """
        self.logger.info("=" * 60)
        self.logger.info("步骤5: 生成报告")
        self.logger.info("=" * 60)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 获取新品列表
        new_products = analysis_data['lifecycle_analysis'].get('new_products', [])
        new_products_objs = [Product.from_dict(p) for p in new_products]

        # 获取AI验证统计数据
        self.logger.info("5.1 获取AI验证统计数据")
        validation_stats = self._get_validation_statistics(products)

        # 获取模型对比结果
        self.logger.info("5.2 获取模型对比结果")
        model_comparison = self.db.get_model_comparison(keyword)

        # 5.3 构建图表
        self.logger.info("5.3 构建图表")
        charts = self.chart_builder.build_all_charts(
            products, new_products_objs, analysis_data
        )

        # 5.4 生成HTML报告
        self.logger.info("5.4 生成HTML报告")
        html_path = self.html_generator.generate_report(
            keyword=keyword,
            products=products,
            new_products=new_products_objs,
            analysis_data=analysis_data,
            charts=charts,
            validation_stats=validation_stats,
            model_comparison=model_comparison,
            filename=f"report_{keyword}_{timestamp}.html"
        )

        # 5.5 导出CSV数据
        self.logger.info("5.5 导出CSV数据")
        csv_paths = self.csv_exporter.export_all(
            products=products,
            new_products=new_products_objs,
            analysis_data=analysis_data,
            timestamp=timestamp
        )

        return {
            'html_report': html_path,
            **csv_paths
        }

    def _get_validation_statistics(self, products: list) -> Dict[str, Any]:
        """
        获取AI验证统计数据

        Args:
            products: 产品列表

        Returns:
            验证统计数据字典
        """
        # 从数据库获取所有产品的验证结果
        validations = []
        for product in products:
            validation = self.db.get_category_validation(product.asin)
            if validation:
                validations.append(validation)

        if not validations:
            return {
                'total': 0,
                'validated': 0,
                'relevant': 0,
                'irrelevant': 0,
                'correct_category': 0,
                'incorrect_category': 0,
                'relevant_rate': 0,
                'correct_rate': 0,
                'has_data': False
            }

        # 使用CategoryValidator的统计方法
        stats = self.category_validator.get_statistics(validations)
        stats['validated'] = len(validations)
        stats['has_data'] = True

        return stats

    def _save_analysis_result(
        self,
        keyword: str,
        analysis_data: Dict[str, Any],
        report_paths: Dict[str, str]
    ):
        """
        保存分析结果到数据库

        Args:
            keyword: 搜索关键词
            analysis_data: 分析数据
            report_paths: 报告文件路径
        """
        self.logger.info("6. 保存分析结果")

        market_blank_index = analysis_data['market_analysis'].get('market_blank_index', 0)
        new_product_count = analysis_data['lifecycle_analysis'].get('new_product_count', 0)

        result = AnalysisResult(
            keyword=keyword,
            market_blank_index=market_blank_index,
            new_product_count=new_product_count,
            analysis_data=json.dumps(analysis_data, ensure_ascii=False),
            report_path=report_paths.get('html_report', '')
        )

        self.db.insert_analysis_result(result)
        self.logger.info("分析结果已保存到数据库")

    def get_summary(self, keyword: str) -> str:
        """
        获取分析摘要

        Args:
            keyword: 搜索关键词

        Returns:
            摘要文本
        """
        products = self.db.get_all_products()
        sellerspirit_data = self.db.get_sellerspirit_data(keyword)

        if not products:
            return "没有可用的产品数据"

        # 生成各模块摘要
        market_analysis = self.market_analyzer.analyze(products, sellerspirit_data)
        lifecycle_analysis = self.lifecycle_analyzer.analyze(products)
        price_analysis = self.price_analyzer.analyze(products)

        summary = f"""
{'=' * 60}
亚马逊市场分析摘要 - {keyword}
{'=' * 60}

{self.market_analyzer.get_market_summary(market_analysis)}

{self.lifecycle_analyzer.get_lifecycle_summary(lifecycle_analysis)}

{self.price_analyzer.get_price_summary(price_analysis)}

{'=' * 60}
"""
        return summary
