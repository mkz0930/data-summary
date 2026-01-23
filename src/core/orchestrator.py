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
from src.analyzers.competitor_analyzer import CompetitorAnalyzer
from src.analyzers.segmentation_analyzer import SegmentationAnalyzer
from src.analyzers.trend_analyzer import TrendAnalyzer
from src.analyzers.blue_ocean_analyzer import BlueOceanAnalyzer
from src.analyzers.advertising_analyzer import AdvertisingAnalyzer
from src.analyzers.seasonality_analyzer import SeasonalityAnalyzer
from src.analyzers.scoring_system import ScoringSystem
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
            max_concurrent=self.config.scraperapi_max_concurrent,
            cache_dir=str(self.config.keyword_cache_dir)
        )
        self.price_collector = PriceCollector(
            api_token=self.config.apify_api_token,
            max_concurrent=self.config.apify_max_concurrent,
            rate_limit_delay=self.config.apify_rate_limit_delay
        )
        self.sellerspirit_collector = SellerSpiritCollector(db_manager=self.db)

        # 数据校验模块
        # Claude和Gemini验证器将在运行时动态创建（需要任务输出目录）
        self.category_validator = None
        self.gemini_validator = None
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
        self.competitor_analyzer = CompetitorAnalyzer()
        self.segmentation_analyzer = SegmentationAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        self.blue_ocean_analyzer = BlueOceanAnalyzer(
            competition_threshold=self.config.blue_ocean_competition_threshold,
            min_sales_volume=self.config.blue_ocean_min_sales,
            max_sales_volume=self.config.blue_ocean_max_sales,
            min_reviews=self.config.blue_ocean_min_reviews,
            max_reviews=self.config.blue_ocean_max_reviews,
            min_rating=self.config.blue_ocean_min_rating,
            max_avg_reviews=self.config.blue_ocean_max_avg_reviews
        )
        self.advertising_analyzer = AdvertisingAnalyzer()
        self.seasonality_analyzer = SeasonalityAnalyzer()
        self.scoring_system = ScoringSystem()

        # 报告生成模块（注意：这里使用默认目录初始化，实际使用时会动态指定）
        self.chart_builder = ChartBuilder()
        self.html_generator = None  # 将在生成报告时动态创建
        self.csv_exporter = None    # 将在生成报告时动态创建

        self.logger.info("模块初始化完成")

    def run(
        self,
        keyword: Optional[str] = None,
        skip_collection: bool = False,
        skip_validation: bool = False,
        force_reanalysis: bool = False,
        regenerate_report: bool = True
    ) -> Dict[str, Any]:
        """
        运行完整的分析流程

        Args:
            keyword: 搜索关键词（如果为None则使用配置文件中的关键词）
            skip_collection: 是否跳过数据采集（使用数据库中的数据）
            skip_validation: 是否跳过AI分类校验
            force_reanalysis: 是否强制重新分析（即使已有分析结果）
            regenerate_report: 是否重新生成报告（默认True，即使使用缓存数据也生成新报告）

        Returns:
            分析结果字典
        """
        from datetime import datetime

        keyword = keyword or self.config.keyword

        # 生成任务时间戳（用于创建任务专属目录）
        task_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info(f"开始分析流程: {keyword}")
        self.logger.info("=" * 60)
        self.logger.info(f"  - 关键词: {keyword}")
        self.logger.info(f"  - 任务时间戳: {task_timestamp}")
        self.logger.info(f"  - 跳过数据采集: {'是' if skip_collection else '否'}")
        self.logger.info(f"  - 跳过数据校验: {'是' if skip_validation else '否'}")
        self.logger.info(f"  - 强制重新分析: {'是' if force_reanalysis else '否'}")
        self.logger.info(f"  - 重新生成报告: {'是' if regenerate_report else '否'}")
        self.logger.info(f"  - 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  - 输出目录: {self.config.get_task_output_dir(keyword, task_timestamp)}")
        self.logger.info("=" * 60)

        # 检查是否已经分析过该关键词
        if not force_reanalysis:
            self.logger.info(f"  - 正在检查是否已有分析结果...")
            existing_result = self.db.get_analysis_result(keyword)
            if existing_result:
                self.logger.info(f"  ✓ 找到已有分析结果")
                self.logger.info(f"  - 分析时间: {existing_result.created_at}")
                self.logger.info(f"  - 市场空白指数: {existing_result.market_blank_index}")
                self.logger.info(f"  - 新品数量: {existing_result.new_product_count}")
                self.logger.info(f"  - 原报告路径: {existing_result.report_path}")

                # 即使有缓存结果，也要确保卖家精灵数据存在
                self.logger.info("")
                self.logger.info("  - 检查卖家精灵数据完整性...")
                self._ensure_sellerspirit_data(keyword, task_timestamp)

                # 解析分析数据
                analysis_data = json.loads(existing_result.analysis_data) if existing_result.analysis_data else {}

                # 如果需要重新生成报告
                if regenerate_report:
                    self.logger.info("")
                    self.logger.info("  - 使用缓存的分析数据，重新生成带时间戳的报告...")

                    # 从数据库加载产品数据
                    products = self.db.get_all_products()
                    if not products:
                        self.logger.error("  ✗ 错误: 数据库中没有产品数据")
                        raise ValueError("数据库中没有产品数据")

                    # 生成新报告
                    report_paths = self._generate_reports(keyword, products, analysis_data, task_timestamp)

                    self.logger.info("")
                    self.logger.info("=" * 60)
                    self.logger.info(f"✓ 报告生成完成!")
                    self.logger.info("=" * 60)
                    self.logger.info(f"  - 关键词: {keyword}")
                    self.logger.info(f"  - 使用缓存数据: 是")
                    self.logger.info(f"  - 新报告路径: {report_paths.get('html_report', '')}")
                    self.logger.info(f"  - 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    self.logger.info("=" * 60)

                    return {
                        'success': True,
                        'keyword': keyword,
                        'from_cache': True,
                        'report_regenerated': True,
                        'analyzed_at': existing_result.created_at,
                        'market_blank_index': existing_result.market_blank_index,
                        'new_product_count': existing_result.new_product_count,
                        'analysis_data': analysis_data,
                        'report_paths': report_paths
                    }
                else:
                    self.logger.info("")
                    self.logger.info("提示: 如需重新分析，请使用 --force-reanalysis 参数")
                    self.logger.info("提示: 如需重新生成报告，请使用 --regenerate-report 参数")

                    return {
                        'success': True,
                        'keyword': keyword,
                        'from_cache': True,
                        'report_regenerated': False,
                        'analyzed_at': existing_result.created_at,
                        'market_blank_index': existing_result.market_blank_index,
                        'new_product_count': existing_result.new_product_count,
                        'analysis_data': analysis_data,
                        'report_paths': {'html_report': existing_result.report_path}
                    }
            else:
                self.logger.info(f"  - 未找到已有分析结果，将执行完整分析")

        overall_start_time = datetime.now()

        try:
            # 步骤1: 数据采集
            if not skip_collection:
                products = self._collect_data(keyword, task_timestamp)
            else:
                self.logger.info("")
                self.logger.info("=" * 160)
                self.logger.info("步骤1: 数据采集 (跳过)")
                self.logger.info("=" * 160)
                self.logger.info("  - 正在从数据库加载产品数据...")
                products = self.db.get_all_products()
                self.logger.info(f"  ✓ 已加载 {len(products)} 个产品")
                self.logger.info("=" * 160)
            if not products:
                self.logger.error("  ✗ 错误: 没有产品数据可供分析")
                raise ValueError("没有产品数据可供分析")

            # 确保卖家精灵数据存在（无论是否跳过采集）
            self._ensure_sellerspirit_data(keyword, task_timestamp)

            # 步骤2: 数据校验
            if not skip_validation:
                self._validate_data(products, keyword, task_timestamp)
            else:
                self.logger.info("")
                self.logger.info("=" * 60)
                self.logger.info("步骤2: 数据校验 (跳过)")
                self.logger.info("=" * 60)
                self.logger.info("  - 已跳过AI分类校验")
                self.logger.info("=" * 60)

            # 步骤3: 数据质量检查
            self._check_data_quality(products)

            # 步骤4: 数据分析
            analysis_data = self._analyze_data(products, keyword)

            # 步骤5: 生成报告
            report_paths = self._generate_reports(keyword, products, analysis_data, task_timestamp)

            # 步骤6: 保存分析结果
            self._save_analysis_result(keyword, analysis_data, report_paths)

            overall_end_time = datetime.now()
            total_elapsed = (overall_end_time - overall_start_time).total_seconds()

            self.logger.info("")
            self.logger.info("=" * 60)
            self.logger.info(f"✓ 分析流程完成!")
            self.logger.info("=" * 60)
            self.logger.info(f"  - 关键词: {keyword}")
            self.logger.info(f"  - 总产品数: {len(products)}")
            self.logger.info(f"  - 市场空白指数: {analysis_data['market_analysis'].get('market_blank_index', 'N/A')}")
            self.logger.info(f"  - 新品数量: {analysis_data['lifecycle_analysis'].get('new_product_count', 0)}")
            self.logger.info(f"  - 总耗时: {total_elapsed:.2f}秒 ({total_elapsed/60:.1f}分钟)")
            self.logger.info(f"  - 完成时间: {overall_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("=" * 60)

            return {
                'success': True,
                'keyword': keyword,
                'total_products': len(products),
                'analysis_data': analysis_data,
                'report_paths': report_paths
            }

        except Exception as e:
            overall_end_time = datetime.now()
            total_elapsed = (overall_end_time - overall_start_time).total_seconds()

            self.logger.error("")
            self.logger.error("=" * 60)
            self.logger.error(f"✗ 分析流程失败!")
            self.logger.error("=" * 60)
            self.logger.error(f"  - 关键词: {keyword}")
            self.logger.error(f"  - 错误类型: {type(e).__name__}")
            self.logger.error(f"  - 错误信息: {str(e)}")
            self.logger.error(f"  - 失败时间: {overall_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.error(f"  - 已耗时: {total_elapsed:.2f}秒")
            self.logger.error("=" * 60)
            self.logger.error(f"详细错误信息:", exc_info=True)

            return {
                'success': False,
                'error': str(e)
            }

    def _collect_data(self, keyword: str, task_timestamp: str) -> list:
        """
        数据采集阶段

        Args:
            keyword: 搜索关键词
            task_timestamp: 任务时间戳

        Returns:
            产品列表
        """
        from datetime import datetime

        self.logger.info("=" * 60)
        self.logger.info("步骤1: 数据采集")
        self.logger.info("=" * 60)

        # 1.1 采集ASIN
        self.logger.info(f"1.1 开始采集ASIN")
        self.logger.info(f"  - 关键词: {keyword}")
        self.logger.info(f"  - 最大页数: {self.config.max_asin}")
        self.logger.info(f"  - 销量阈值: {self.config.sales_threshold}")

        start_time = datetime.now()
        self.logger.info(f"  - 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        products = self.asin_collector.collect_asins(
            keyword=keyword,
            max_pages=self.config.max_asin,
            sales_threshold=self.config.sales_threshold,
            fetch_details=False
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        self.logger.info(f"  ✓ ASIN采集完成")
        self.logger.info(f"  - 采集到产品数: {len(products)}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 保存到数据库（跳过已存在的产品）
        self.logger.info(f"  - 正在保存到数据库...")
        existing_asins = self.db.get_existing_asins()
        new_products = [p for p in products if p.asin not in existing_asins]
        skipped_count = len(products) - len(new_products)

        if skipped_count > 0:
            self.logger.info(f"  - 跳过已存在的产品: {skipped_count} 个")

        saved_count = 0
        for product in new_products:
            self.db.insert_product(product)
            saved_count += 1

        if saved_count > 0:
            self.logger.info(f"  ✓ 已保存 {saved_count} 个新产品到数据库")
        else:
            self.logger.info(f"  ✓ 所有产品已存在，无需保存")

        # 1.2 补充价格数据
        self.logger.info("")
        self.logger.info("1.2 补充缺失的价格数据")
        products_without_price = [p for p in products if not p.price]
        self.logger.info(f"  - 缺少价格的产品数: {len(products_without_price)}/{len(products)}")

        if products_without_price:
            start_time = datetime.now()
            self.logger.info(f"  - 开始补充价格数据...")

            self.price_collector.update_prices(products_without_price)

            updated_count = 0
            for product in products_without_price:
                self.db.insert_product(product)
                updated_count += 1

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            self.logger.info(f"  ✓ 价格数据补充完成")
            self.logger.info(f"  - 更新产品数: {updated_count}")
            self.logger.info(f"  - 耗时: {elapsed:.2f}秒")
        else:
            self.logger.info(f"  ✓ 所有产品都有价格数据，无需补充")

        # 1.3 采集卖家精灵数据
        self.logger.info("")
        self.logger.info("1.3 采集卖家精灵数据")
        self.logger.info(f"  - 关键词: {keyword}")

        # 先检查数据库中是否已有数据
        self.logger.info(f"  - 正在检查数据库...")
        existing_data = self.db.get_sellerspirit_data(keyword)

        if existing_data:
            self.logger.info(f"  ✓ 数据库中已有卖家精灵数据，跳过采集")
            self.logger.info(f"  - 采集时间: {existing_data.collected_at}")
            self.logger.info(f"  - 月搜索量: {existing_data.monthly_searches}")
            self.logger.info(f"  - CR4: {existing_data.cr4}")
        else:
            # 数据不存在，开始采集
            try:
                start_time = datetime.now()
                self.logger.info(f"  - 数据库中无数据，开始采集...")

                # 获取任务专属的raw目录
                task_raw_dir = self.config.get_task_raw_dir(keyword, task_timestamp)
                self.logger.info(f"  - 原始数据保存目录: {task_raw_dir}")

                sellerspirit_data = self.sellerspirit_collector.collect_data(
                    keyword=keyword,
                    output_dir=task_raw_dir
                )

                end_time = datetime.now()
                elapsed = (end_time - start_time).total_seconds()

                if sellerspirit_data:
                    self.db.insert_sellerspirit_data(sellerspirit_data)
                    self.logger.info(f"  ✓ 卖家精灵数据采集完成")
                    self.logger.info(f"  - 月搜索量: {sellerspirit_data.monthly_searches}")
                    self.logger.info(f"  - CR4: {sellerspirit_data.cr4}")
                    self.logger.info(f"  - 耗时: {elapsed:.2f}秒")
                else:
                    self.logger.warning(f"  ⚠ 未获取到卖家精灵数据")
            except Exception as e:
                self.logger.error(f"  ✗ 卖家精灵数据采集失败: {e}")
                self.logger.error(f"  - 错误类型: {type(e).__name__}")

        self.logger.info("")
        self.logger.info(f"✓ 步骤1完成 - 共采集 {len(products)} 个产品")
        self.logger.info("=" * 60)

        return products

    def _ensure_sellerspirit_data(self, keyword: str, task_timestamp: str):
        """
        确保卖家精灵数据存在，如果不存在则采集

        Args:
            keyword: 搜索关键词
            task_timestamp: 任务时间戳
        """
        from datetime import datetime

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("检查卖家精灵数据")
        self.logger.info("=" * 60)
        self.logger.info(f"  - 关键词: {keyword}")

        # 检查数据库中是否已有数据
        self.logger.info(f"  - 正在检查数据库...")
        sellerspirit_data = self.db.get_sellerspirit_data(keyword)

        if sellerspirit_data:
            self.logger.info(f"  ✓ 数据库中已有卖家精灵数据")
            self.logger.info(f"  - 采集时间: {sellerspirit_data.collected_at}")
            self.logger.info(f"  - 月搜索量: {sellerspirit_data.monthly_searches}")
            self.logger.info(f"  - CR4: {sellerspirit_data.cr4}")
            self.logger.info("=" * 60)
            return

        # 数据不存在，需要采集
        self.logger.info(f"  ⚠ 数据库中无卖家精灵数据，开始采集...")
        self.logger.info(f"  - 关键词: {keyword}")

        try:
            start_time = datetime.now()
            self.logger.info(f"  - 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"  - 正在启动卖家精灵采集器...")

            # 获取任务专属的raw目录
            task_raw_dir = self.config.get_task_raw_dir(keyword, task_timestamp)
            self.logger.info(f"  - 原始数据保存目录: {task_raw_dir}")

            sellerspirit_data = self.sellerspirit_collector.collect_data(
                keyword=keyword,
                output_dir=task_raw_dir
            )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            if sellerspirit_data:
                self.db.insert_sellerspirit_data(sellerspirit_data)
                self.logger.info(f"  ✓ 卖家精灵数据采集完成")
                self.logger.info(f"  - 月搜索量: {sellerspirit_data.monthly_searches}")
                self.logger.info(f"  - CR4: {sellerspirit_data.cr4}")
                self.logger.info(f"  - 关键词扩展数: {len(sellerspirit_data.keyword_extensions) if sellerspirit_data.keyword_extensions else 0}")
                self.logger.info(f"  - 耗时: {elapsed:.2f}秒")
                self.logger.info(f"  ✓ 数据已保存到数据库")
            else:
                self.logger.warning(f"  ⚠ 未获取到卖家精灵数据")
                self.logger.warning(f"  - 可能原因: Chrome未启动、插件未加载、网络问题等")
                self.logger.warning(f"  - 将继续分析，但部分功能可能受限")
        except Exception as e:
            self.logger.error(f"  ✗ 卖家精灵数据采集失败: {e}")
            self.logger.error(f"  - 错误类型: {type(e).__name__}")
            self.logger.warning(f"  - 将继续分析，但部分功能可能受限")

        self.logger.info("=" * 60)

    def _validate_data(self, products: list, keyword: str, task_timestamp: str):
        """
        数据校验阶段

        Args:
            products: 产品列表
            keyword: 搜索关键词
            task_timestamp: 任务时间戳
        """
        from datetime import datetime

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("步骤2: 数据校验")
        self.logger.info("=" * 60)

        # 获取任务专属的raw目录（用于保存验证结果CSV）
        task_raw_dir = self.config.get_task_raw_dir(keyword, task_timestamp)

        # 2.1 Claude AI分类校验
        self.logger.info("2.1 Claude AI分类校验")
        self.logger.info(f"  - 待校验产品数: {len(products)}")
        self.logger.info(f"  - 关键词: {keyword}")

        # 初始化Claude验证器（使用任务专属的raw目录）
        self.category_validator = CategoryValidator(
            api_key=self.config.anthropic_api_key,
            db_manager=self.db,
            csv_output_dir=task_raw_dir,
            max_concurrent=self.config.claude_max_concurrent,
            rate_limit_delay=self.config.claude_rate_limit_delay
        )

        start_time = datetime.now()
        self.logger.info(f"  - 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  - 正在调用Claude API...")

        claude_validations = self.category_validator.validate_batch(products, keyword)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        # 保存Claude验证结果到数据库
        self.logger.info(f"  - 正在保存验证结果到数据库...")
        saved_count = 0
        for validation in claude_validations:
            self.db.insert_category_validation(validation)
            saved_count += 1

        # 统计Claude结果
        claude_stats = self.category_validator.get_statistics(claude_validations)
        self.logger.info(f"  ✓ Claude校验完成")
        self.logger.info(f"  - 校验产品数: {claude_stats['total']}")
        self.logger.info(f"  - 相关产品: {claude_stats['relevant']} ({claude_stats['relevant_rate']:.1f}%)")
        self.logger.info(f"  - 不相关产品: {claude_stats['irrelevant']}")
        self.logger.info(f"  - 分类正确: {claude_stats['correct_category']} ({claude_stats['correct_rate']:.1f}%)")
        self.logger.info(f"  - 分类错误: {claude_stats['incorrect_category']}")
        self.logger.info(f"  - 已保存: {saved_count} 条记录到数据库")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 保存Claude验证结果到CSV（raw目录）
        if claude_validations:
            self.logger.info(f"  - 正在保存验证结果到CSV...")
            claude_csv_path = self.category_validator.save_results_to_csv(
                claude_validations, products, keyword
            )
            if claude_csv_path:
                self.logger.info(f"  ✓ Claude验证结果已保存到: {claude_csv_path}")

        # 2.2 Gemini AI分类校验
        self.logger.info("")
        self.logger.info("2.2 Gemini AI分类校验")
        self.logger.info(f"  - 待校验产品数: {len(products)}")
        self.logger.info(f"  - 关键词: {keyword}")

        # 初始化Gemini验证器（使用任务专属的raw目录）
        self.gemini_validator = GeminiCategoryValidator(
            api_key=self.config.google_api_key,
            db_manager=self.db,
            max_concurrent=self.config.gemini_max_concurrent,
            rate_limit_delay=self.config.gemini_rate_limit_delay,
            csv_output_dir=task_raw_dir
        )

        start_time = datetime.now()
        self.logger.info(f"  - 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  - 正在调用Gemini API...")

        gemini_validations = self.gemini_validator.validate_batch(products, keyword)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        # 统计Gemini结果
        gemini_stats = self.gemini_validator.get_statistics(gemini_validations)
        self.logger.info(f"  ✓ Gemini校验完成")
        self.logger.info(f"  - 校验产品数: {gemini_stats['total']}")
        self.logger.info(f"  - 相关产品: {gemini_stats['relevant']} ({gemini_stats['relevant_rate']:.1f}%)")
        self.logger.info(f"  - 不相关产品: {gemini_stats['irrelevant']}")
        self.logger.info(f"  - 分类正确: {gemini_stats['correct_category']} ({gemini_stats['correct_rate']:.1f}%)")
        self.logger.info(f"  - 分类错误: {gemini_stats['incorrect_category']}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 保存Gemini验证结果到CSV（raw目录）
        if gemini_validations:
            self.logger.info(f"  - 正在保存验证结果到CSV...")
            gemini_csv_path = self.gemini_validator.save_results_to_csv(
                gemini_validations, products, keyword
            )
            if gemini_csv_path:
                self.logger.info(f"  ✓ Gemini验证结果已保存到: {gemini_csv_path}")

        # 2.3 对比两个模型的结果
        if claude_validations and gemini_validations:
            self.logger.info("")
            self.logger.info("2.3 对比两个模型的结果")
            self.logger.info(f"  - Claude结果数: {len(claude_validations)}")
            self.logger.info(f"  - Gemini结果数: {len(gemini_validations)}")
            self.logger.info(f"  - 正在对比...")

            start_time = datetime.now()
            comparison_result = self.model_comparator.compare_validations(
                claude_validations, gemini_validations
            )
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # 输出对比摘要
            self.logger.info(f"  ✓ 对比完成")
            self.logger.info(self.model_comparator.get_comparison_summary(comparison_result))
            self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

            # 导出不一致的ASIN到CSV
            if comparison_result['disagreement_asins']:
                task_exports_dir = self.config.get_task_exports_dir(keyword, task_timestamp)
                csv_path = task_exports_dir / f"model_disagreements_{keyword}_{task_timestamp}.csv"
                self.logger.info(f"  - 正在导出不一致的ASIN到CSV...")
                self.model_comparator.export_disagreements_to_csv(comparison_result, str(csv_path))
                self.logger.info(f"  ✓ 不一致的ASIN已导出")
                self.logger.info(f"  - 文件路径: {csv_path}")

            # 保存对比结果到数据库
            self.logger.info(f"  - 正在保存对比结果到数据库...")
            self.db.save_model_comparison(keyword, comparison_result)
            self.logger.info(f"  ✓ 对比结果已保存")

        self.logger.info("")
        self.logger.info(f"✓ 步骤2完成 - 数据校验完成")
        self.logger.info("=" * 60)

    def _check_data_quality(self, products: list):
        """
        数据质量检查阶段

        Args:
            products: 产品列表
        """
        from datetime import datetime

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("步骤3: 数据质量检查")
        self.logger.info("=" * 60)

        self.logger.info(f"  - 待检查产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  - 正在检查数据质量...")

        # 检查数据质量
        quality_result = self.quality_checker.check_batch(products)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 数据质量检查完成")
        self.logger.info(f"  - 平均质量分: {quality_result['average_quality_score']:.2f}/100")
        self.logger.info(f"  - 有问题的产品: {quality_result['products_with_issues']}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 标记异常产品
        self.logger.info(f"  - 正在标记异常产品...")
        self.quality_checker.mark_anomalies(products)

        # 统计异常产品
        anomaly_count = sum(1 for p in products if p.has_anomaly)
        self.logger.info(f"  - 异常产品数: {anomaly_count}/{len(products)}")

        # 更新数据库
        if anomaly_count > 0:
            self.logger.info(f"  - 正在更新数据库...")
            updated_count = 0
            for product in products:
                if product.has_anomaly:
                    self.db.update_product(product)
                    updated_count += 1
            self.logger.info(f"  ✓ 已更新 {updated_count} 个异常产品")
        else:
            self.logger.info(f"  ✓ 无异常产品需要更新")

        self.logger.info("")
        self.logger.info(f"✓ 步骤3完成 - 数据质量检查完成")
        self.logger.info("=" * 60)

    def _analyze_data(self, products: list, keyword: str) -> Dict[str, Any]:
        """
        数据分析阶段

        Args:
            products: 产品列表
            keyword: 搜索关键词

        Returns:
            分析数据字典
        """
        from datetime import datetime

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("步骤4: 数据分析")
        self.logger.info("=" * 60)

        # 获取卖家精灵数据
        self.logger.info(f"  - 正在加载卖家精灵数据...")
        sellerspirit_data = self.db.get_sellerspirit_data(keyword)
        if sellerspirit_data:
            # 计算非 None 字段数量
            non_none_fields = sum(1 for v in sellerspirit_data.to_dict().values() if v is not None)
            self.logger.info(f"  ✓ 已加载卖家精灵数据 (有效字段数: {non_none_fields})")
        else:
            self.logger.info(f"  ⚠ 未找到卖家精灵数据")

        # 4.1 市场分析
        self.logger.info("")
        self.logger.info("4.1 市场分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析市场数据...")

        market_analysis = self.market_analyzer.analyze(products, sellerspirit_data)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 市场分析完成")
        self.logger.info(f"  - 市场空白指数: {market_analysis.get('market_blank_index', 'N/A')}")
        self.logger.info(f"  - 市场规模: {market_analysis.get('market_size', 'N/A')}")
        self.logger.info(f"  - 竞争强度: {market_analysis.get('competition_level', 'N/A')}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.2 生命周期分析
        self.logger.info("")
        self.logger.info("4.2 生命周期分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")
        self.logger.info(f"  - 新品定义: 上架 {self.config.new_product_days} 天内")
        self.logger.info(f"  - 评论数上限: {self.config.new_product_min_reviews}")
        self.logger.info(f"  - BSR排名上限: {self.config.new_product_max_bsr}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析产品生命周期...")

        lifecycle_analysis = self.lifecycle_analyzer.analyze(products)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 生命周期分析完成")
        self.logger.info(f"  - 新品数量: {lifecycle_analysis.get('new_product_count', 0)}")
        self.logger.info(f"  - 成熟产品数量: {lifecycle_analysis.get('mature_product_count', 0)}")
        self.logger.info(f"  - 新品占比: {lifecycle_analysis.get('new_product_rate', 0):.1f}%")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.3 价格分析
        self.logger.info("")
        self.logger.info("4.3 价格分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")
        self.logger.info(f"  - 价格区间数: {len(self.config.price_ranges)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析价格分布...")

        price_analysis = self.price_analyzer.analyze(products)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 价格分析完成")
        self.logger.info(f"  - 平均价格: ${price_analysis.get('average_price', 0):.2f}")
        self.logger.info(f"  - 价格中位数: ${price_analysis.get('median_price', 0):.2f}")
        self.logger.info(f"  - 主力价格带: {price_analysis.get('main_price_band', 'N/A')}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.4 关键词分析
        self.logger.info("")
        self.logger.info("4.4 关键词分析")
        self.logger.info(f"  - 关键词: {keyword}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析关键词数据...")

        keyword_analysis = self.keyword_analyzer.analyze(
            sellerspirit_data=sellerspirit_data, main_keyword=keyword
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 关键词分析完成")
        if keyword_analysis:
            self.logger.info(f"  - 搜索量: {keyword_analysis.get('search_volume', 'N/A')}")
            self.logger.info(f"  - 搜索趋势: {keyword_analysis.get('search_trend', 'N/A')}")
        else:
            self.logger.info(f"  ⚠ 无关键词数据")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.5 竞品对标分析
        self.logger.info("")
        self.logger.info("4.5 竞品对标分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析竞品数据...")

        competitor_analysis = self.competitor_analyzer.analyze(products, sellerspirit_data)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 竞品对标分析完成")
        self.logger.info(f"  - Top竞品数: {len(competitor_analysis.get('top_competitors', []))}")
        self.logger.info(f"  - 品牌数量: {competitor_analysis.get('brand_count', 0)}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.6 市场细分分析
        self.logger.info("")
        self.logger.info("4.6 市场细分分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析市场细分...")

        segmentation_analysis = self.segmentation_analyzer.analyze(products, sellerspirit_data)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 市场细分分析完成")
        self.logger.info(f"  - 价格段数: {len(segmentation_analysis.get('price_segments', []))}")
        self.logger.info(f"  - 品牌段数: {len(segmentation_analysis.get('brand_segments', []))}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.7 趋势预测分析
        self.logger.info("")
        self.logger.info("4.7 趋势预测分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析市场趋势...")

        trend_analysis = self.trend_analyzer.analyze(products, sellerspirit_data)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 趋势预测分析完成")
        market_trend = trend_analysis.get('market_trend', {})
        self.logger.info(f"  - 市场趋势: {market_trend.get('trend_direction', 'N/A')}")
        self.logger.info(f"  - 趋势强度: {market_trend.get('trend_strength', 0)}/100")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.8 蓝海产品分析
        self.logger.info("")
        self.logger.info("4.8 蓝海产品分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在识别蓝海产品...")

        blue_ocean_analysis = self.blue_ocean_analyzer.analyze(products, sellerspirit_data)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 蓝海产品分析完成")
        self.logger.info(f"  - 蓝海产品数: {blue_ocean_analysis.get('blue_ocean_count', 0)}")
        self.logger.info(f"  - 蓝海产品占比: {blue_ocean_analysis.get('blue_ocean_rate', 0):.1f}%")
        self.logger.info(f"  - 平均竞争指数: {blue_ocean_analysis.get('avg_competition_index', 0):.1f}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 更新产品的蓝海评分到数据库
        if blue_ocean_analysis.get('scored_products'):
            self.logger.info(f"  - 正在更新产品蓝海评分到数据库...")
            updated_count = 0
            for product in blue_ocean_analysis['scored_products']:
                self.db.update_product(product)
                updated_count += 1
            self.logger.info(f"  ✓ 已更新 {updated_count} 个产品的蓝海评分")

        # 4.9 广告成本分析
        self.logger.info("")
        self.logger.info("4.9 广告成本分析")
        self.logger.info(f"  - 分析产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析广告成本...")

        advertising_analysis = self.advertising_analyzer.analyze(products, sellerspirit_data)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 广告成本分析完成")
        if advertising_analysis.get('bid_analysis'):
            self.logger.info(f"  - 建议竞价: ${advertising_analysis['bid_analysis'].get('suggested_bid', 0):.2f}")
            self.logger.info(f"  - 预估CPC: ${advertising_analysis['cpc_analysis'].get('estimated_cpc', 0):.2f}")
            self.logger.info(f"  - 预估ACoS: {advertising_analysis['acos_analysis'].get('estimated_acos', 0):.1f}%")
            self.logger.info(f"  - 广告可行性: {advertising_analysis['advertising_feasibility'].get('feasibility_level', 'N/A')}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.10 季节性分析
        self.logger.info("")
        self.logger.info("4.10 季节性分析")
        self.logger.info(f"  - 关键词: {keyword}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在分析季节性趋势...")

        seasonality_analysis = self.seasonality_analyzer.analyze(
            products=products, sellerspirit_data=sellerspirit_data, keyword=keyword
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 季节性分析完成")
        if seasonality_analysis.get('seasonality_level'):
            self.logger.info(f"  - 季节性等级: {seasonality_analysis.get('seasonality_level', 'N/A')}")
            self.logger.info(f"  - 季节性指数: {seasonality_analysis.get('seasonality_index', 0)}")
            self.logger.info(f"  - 当前季节状态: {seasonality_analysis.get('current_season_status', {}).get('status', 'N/A')}")
        else:
            self.logger.info(f"  ⚠ 无季节性数据（可能缺少卖家精灵月度搜索数据）")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.11 综合评分 (4大方法论)
        self.logger.info("")
        self.logger.info("4.11 综合评分 (4大方法论)")
        self.logger.info(f"  - 评分产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在计算综合市场评分...")

        # 准备综合评分所需的所有分析数据
        all_analysis_data = {
            'market_analysis': market_analysis,
            'lifecycle_analysis': lifecycle_analysis,
            'price_analysis': price_analysis,
            'keyword_analysis': keyword_analysis,
            'competitor_analysis': competitor_analysis,
            'segmentation_analysis': segmentation_analysis,
            'trend_analysis': trend_analysis,
            'blue_ocean_analysis': blue_ocean_analysis,
            'advertising_analysis': advertising_analysis,
            'seasonality_analysis': seasonality_analysis
        }

        comprehensive_score_obj = self.scoring_system.calculate_comprehensive_score(
            blue_ocean_result=blue_ocean_analysis,
            seasonality_result=seasonality_analysis,
            sellerspirit_data=sellerspirit_data,
            products=products
        )
        comprehensive_score = self.scoring_system.score_to_dict(comprehensive_score_obj)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 综合评分完成")
        self.logger.info(f"  - 综合总分: {comprehensive_score.get('total_score', 0):.1f}/100")
        self.logger.info(f"  - 市场等级: {comprehensive_score.get('grade', 'N/A')}")
        self.logger.info(f"  - 等级说明: {comprehensive_score.get('grade_desc', 'N/A')}")
        recommendations = comprehensive_score.get('recommendations', [])
        first_recommendation = recommendations[0] if recommendations else 'N/A'
        self.logger.info(f"  - 建议: {first_recommendation[:50]}...")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 4.12 基础市场评分 (兼容旧版，使用综合评分数据)
        self.logger.info("")
        self.logger.info("4.12 基础市场评分")
        self.logger.info(f"  - 评分产品数: {len(products)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在计算市场评分...")

        # 使用综合评分数据构建兼容的 market_score
        market_score = {
            'total_score': comprehensive_score.get('total_score', 0),
            'grade': comprehensive_score.get('grade', 'N/A'),
            'recommendation': comprehensive_score.get('recommendations', ['无建议'])[0] if comprehensive_score.get('recommendations') else '无建议',
            'key_factors': comprehensive_score.get('risk_factors', [])
        }

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 综合评分完成")
        self.logger.info(f"  - 市场总分: {market_score.get('total_score', 0)}/100")
        self.logger.info(f"  - 市场评级: {market_score.get('grade', 'N/A')}")
        self.logger.info(f"  - 建议: {market_score.get('recommendation', 'N/A')}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        self.logger.info("")
        self.logger.info(f"✓ 步骤4完成 - 数据分析完成")
        self.logger.info("=" * 60)

        return {
            'market_analysis': market_analysis,
            'lifecycle_analysis': lifecycle_analysis,
            'price_analysis': price_analysis,
            'keyword_analysis': keyword_analysis,
            'competitor_analysis': competitor_analysis,
            'segmentation_analysis': segmentation_analysis,
            'trend_analysis': trend_analysis,
            'blue_ocean_analysis': blue_ocean_analysis,
            'advertising_analysis': advertising_analysis,
            'seasonality_analysis': seasonality_analysis,
            'comprehensive_score': comprehensive_score,
            'market_score': market_score
        }

    def _generate_reports(
        self,
        keyword: str,
        products: list,
        analysis_data: Dict[str, Any],
        task_timestamp: str
    ) -> Dict[str, str]:
        """
        生成报告阶段

        Args:
            keyword: 搜索关键词
            products: 产品列表
            analysis_data: 分析数据
            task_timestamp: 任务时间戳

        Returns:
            报告文件路径字典
        """
        from datetime import datetime

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("步骤5: 生成报告")
        self.logger.info("=" * 60)

        self.logger.info(f"  - 报告时间戳: {task_timestamp}")

        # 创建任务专属目录
        task_reports_dir = self.config.get_task_reports_dir(keyword, task_timestamp)
        task_exports_dir = self.config.get_task_exports_dir(keyword, task_timestamp)
        self.logger.info(f"  - 任务输出目录: {self.config.get_task_output_dir(keyword, task_timestamp)}")
        self.logger.info(f"  - 报告目录: {task_reports_dir}")
        self.logger.info(f"  - 导出目录: {task_exports_dir}")

        # 动态创建报告生成器（使用任务专属目录）
        self.html_generator = HTMLGenerator(task_reports_dir)
        self.csv_exporter = CSVExporter(task_exports_dir)

        # 获取新品列表
        self.logger.info(f"  - 正在提取新品列表...")
        new_products = analysis_data['lifecycle_analysis'].get('new_products', [])
        new_products_objs = [Product.from_dict(p) for p in new_products]
        self.logger.info(f"  ✓ 新品数量: {len(new_products_objs)}")

        # 获取AI验证统计数据
        self.logger.info("")
        self.logger.info("5.1 获取AI验证统计数据")
        self.logger.info(f"  - 正在从数据库加载验证结果...")

        start_time = datetime.now()
        validation_stats = self._get_validation_statistics(products)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        if validation_stats.get('has_data'):
            self.logger.info(f"  ✓ 验证统计数据加载完成")
            self.logger.info(f"  - 已验证产品: {validation_stats['validated']}/{validation_stats['total']}")
            self.logger.info(f"  - 相关产品: {validation_stats['relevant']} ({validation_stats['relevant_rate']:.1f}%)")
            self.logger.info(f"  - 分类正确: {validation_stats['correct_category']} ({validation_stats['correct_rate']:.1f}%)")
        else:
            self.logger.info(f"  ⚠ 无验证统计数据")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 获取模型对比结果
        self.logger.info("")
        self.logger.info("5.2 获取模型对比结果")
        self.logger.info(f"  - 正在从数据库加载对比结果...")

        start_time = datetime.now()
        model_comparison = self.db.get_model_comparison(keyword)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        if model_comparison:
            self.logger.info(f"  ✓ 模型对比结果加载完成")
            self.logger.info(f"  - 一致率: {model_comparison.get('agreement_rate', 'N/A')}")
            self.logger.info(f"  - 不一致数: {len(model_comparison.get('disagreement_asins', []))}")
        else:
            self.logger.info(f"  ⚠ 无模型对比结果")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 5.3 构建图表
        self.logger.info("")
        self.logger.info("5.3 构建图表")
        self.logger.info(f"  - 产品数: {len(products)}")
        self.logger.info(f"  - 新品数: {len(new_products_objs)}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在生成图表...")

        charts = self.chart_builder.build_all_charts(
            products, new_products_objs, analysis_data
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 图表构建完成")
        self.logger.info(f"  - 图表数量: {len(charts)}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 5.4 生成HTML报告
        self.logger.info("")
        self.logger.info("5.4 生成HTML报告")
        filename = f"report_{keyword}_{task_timestamp}.html"
        self.logger.info(f"  - 文件名: {filename}")

        # 获取卖家精灵数据
        self.logger.info(f"  - 正在加载卖家精灵数据...")
        sellerspirit_data_obj = self.db.get_sellerspirit_data(keyword)
        sellerspirit_data = None
        if sellerspirit_data_obj:
            # 解析关键词扩展 JSON 字符串
            keyword_extensions = []
            if sellerspirit_data_obj.keyword_extensions:
                try:
                    import json
                    extensions_data = json.loads(sellerspirit_data_obj.keyword_extensions)
                    # 如果是列表，直接使用；如果是字典，提取关键词
                    if isinstance(extensions_data, list):
                        keyword_extensions = extensions_data
                    elif isinstance(extensions_data, dict):
                        # 如果是字典格式，尝试提取关键词列表
                        keyword_extensions = extensions_data.get('keywords', [])
                except json.JSONDecodeError as e:
                    self.logger.warning(f"  ⚠ 解析关键词扩展数据失败: {e}")
                    keyword_extensions = []

            sellerspirit_data = {
                'monthly_searches': sellerspirit_data_obj.monthly_searches,
                'purchase_rate': sellerspirit_data_obj.purchase_rate,
                'click_rate': sellerspirit_data_obj.click_rate,
                'conversion_rate': sellerspirit_data_obj.conversion_rate,
                'monopoly_rate': sellerspirit_data_obj.monopoly_rate,
                'cr4': sellerspirit_data_obj.cr4,
                'keyword_extensions': keyword_extensions
            }
            self.logger.info(f"  ✓ 已加载卖家精灵数据")
            self.logger.info(f"  - 关键词扩展数: {len(keyword_extensions)}")
        else:
            self.logger.info(f"  ⚠ 未找到卖家精灵数据")

        # 获取蓝海分析数据
        self.logger.info(f"  - 正在加载蓝海分析数据...")
        blue_ocean_analysis = analysis_data.get('blue_ocean_analysis')
        if blue_ocean_analysis:
            self.logger.info(f"  ✓ 已加载蓝海分析数据")
            self.logger.info(f"  - 蓝海产品数: {blue_ocean_analysis.get('blue_ocean_count', 0)}")
        else:
            self.logger.info(f"  ⚠ 未找到蓝海分析数据")

        # 获取广告成本分析数据
        self.logger.info(f"  - 正在加载广告成本分析数据...")
        advertising_analysis = analysis_data.get('advertising_analysis')
        if advertising_analysis and advertising_analysis.get('bid_analysis'):
            self.logger.info(f"  ✓ 已加载广告成本分析数据")
            self.logger.info(f"  - 建议竞价: ${advertising_analysis['bid_analysis'].get('suggested_bid', 0):.2f}")
        else:
            self.logger.info(f"  ⚠ 未找到广告成本分析数据")

        # 获取季节性分析数据
        self.logger.info(f"  - 正在加载季节性分析数据...")
        seasonality_analysis = analysis_data.get('seasonality_analysis')
        if seasonality_analysis and seasonality_analysis.get('seasonality_level'):
            self.logger.info(f"  ✓ 已加载季节性分析数据")
            self.logger.info(f"  - 季节性等级: {seasonality_analysis.get('seasonality_level', 'N/A')}")
        else:
            self.logger.info(f"  ⚠ 未找到季节性分析数据")

        # 获取综合评分数据
        self.logger.info(f"  - 正在加载综合评分数据...")
        comprehensive_score = analysis_data.get('comprehensive_score')
        if comprehensive_score and comprehensive_score.get('total_score'):
            self.logger.info(f"  ✓ 已加载综合评分数据")
            self.logger.info(f"  - 综合总分: {comprehensive_score.get('total_score', 0):.1f}/100")
        else:
            self.logger.info(f"  ⚠ 未找到综合评分数据")

        start_time = datetime.now()
        self.logger.info(f"  - 正在生成HTML报告...")

        html_path = self.html_generator.generate_report(
            keyword=keyword,
            products=products,
            new_products=new_products_objs,
            analysis_data=analysis_data,
            charts=charts,
            validation_stats=validation_stats,
            model_comparison=model_comparison,
            sellerspirit_data=sellerspirit_data,
            blue_ocean_analysis=blue_ocean_analysis,
            advertising_analysis=advertising_analysis,
            seasonality_analysis=seasonality_analysis,
            comprehensive_score=comprehensive_score,
            filename=filename
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ HTML报告生成完成")
        self.logger.info(f"  - 文件路径: {html_path}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        # 5.5 导出CSV数据
        self.logger.info("")
        self.logger.info("5.5 导出CSV数据")
        self.logger.info(f"  - 时间戳: {task_timestamp}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在导出CSV文件...")

        csv_paths = self.csv_exporter.export_all(
            products=products,
            new_products=new_products_objs,
            analysis_data=analysis_data,
            timestamp=task_timestamp
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ CSV导出完成")
        self.logger.info(f"  - 导出文件数: {len(csv_paths)}")
        for name, path in csv_paths.items():
            self.logger.info(f"    • {name}: {path}")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        self.logger.info("")
        self.logger.info(f"✓ 步骤5完成 - 报告生成完成")
        self.logger.info(f"  - 所有文件已保存到: {self.config.get_task_output_dir(keyword, task_timestamp)}")
        self.logger.info("=" * 60)

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

        # 计算统计数据（当category_validator为None时直接计算）
        if self.category_validator:
            stats = self.category_validator.get_statistics(validations)
        else:
            # 直接计算统计数据（与CategoryValidator.get_statistics逻辑一致）
            total = len(validations)
            relevant = sum(1 for v in validations if v.is_relevant)
            correct = sum(1 for v in validations if v.category_is_correct)
            stats = {
                'total': total,
                'relevant': relevant,
                'irrelevant': total - relevant,
                'correct_category': correct,
                'incorrect_category': total - correct,
                'relevant_rate': relevant / total if total > 0 else 0,
                'correct_rate': correct / total if total > 0 else 0
            }
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
        from datetime import datetime

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("步骤6: 保存分析结果")
        self.logger.info("=" * 60)

        market_blank_index = analysis_data['market_analysis'].get('market_blank_index', 0)
        new_product_count = analysis_data['lifecycle_analysis'].get('new_product_count', 0)

        self.logger.info(f"  - 关键词: {keyword}")
        self.logger.info(f"  - 市场空白指数: {market_blank_index}")
        self.logger.info(f"  - 新品数量: {new_product_count}")
        self.logger.info(f"  - 报告路径: {report_paths.get('html_report', '')}")

        start_time = datetime.now()
        self.logger.info(f"  - 正在保存到数据库...")

        result = AnalysisResult(
            keyword=keyword,
            market_blank_index=market_blank_index,
            new_product_count=new_product_count,
            analysis_data=json.dumps(analysis_data, ensure_ascii=False),
            report_path=report_paths.get('html_report', '')
        )

        self.db.insert_analysis_result(result)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.logger.info(f"  ✓ 分析结果已保存到数据库")
        self.logger.info(f"  - 耗时: {elapsed:.2f}秒")

        self.logger.info("")
        self.logger.info(f"✓ 步骤6完成 - 分析结果已保存")
        self.logger.info("=" * 60)

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
