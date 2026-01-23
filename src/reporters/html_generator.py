"""
HTML报告生成器模块
生成交互式HTML分析报告
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from jinja2 import Template

from src.database.models import Product
from src.utils.logger import get_logger


class HTMLGenerator:
    """HTML报告生成器"""

    def __init__(self, output_dir: Path):
        """
        初始化HTML生成器

        Args:
            output_dir: 输出目录
        """
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        keyword: str,
        products: List[Product],
        new_products: List[Product],
        analysis_data: Dict[str, Any],
        charts: Dict[str, str],
        validation_stats: Dict[str, Any] = None,
        model_comparison: Dict[str, Any] = None,
        sellerspirit_data: Dict[str, Any] = None,
        blue_ocean_analysis: Dict[str, Any] = None,
        advertising_analysis: Dict[str, Any] = None,
        seasonality_analysis: Dict[str, Any] = None,
        comprehensive_score: Dict[str, Any] = None,
        filename: str = "report.html"
    ) -> str:
        """
        生成完整的HTML报告 - 增强版

        Args:
            keyword: 搜索关键词
            products: 产品列表
            new_products: 新品列表
            analysis_data: 分析数据
            charts: 图表JSON字典
            validation_stats: AI验证统计数据
            model_comparison: 模型对比结果
            sellerspirit_data: 卖家精灵数据
            blue_ocean_analysis: 蓝海分析结果
            advertising_analysis: 广告成本分析结果
            seasonality_analysis: 季节性分析结果
            comprehensive_score: 综合评分结果
            filename: 文件名

        Returns:
            报告文件路径
        """
        self.logger.info(f"开始生成HTML报告: {filename}")

        # 构建报告数据
        report_data = {
            'keyword': keyword,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_products': len(products),
            'new_products_count': len(new_products),
            'market_analysis': analysis_data.get('market_analysis', {}),
            'lifecycle_analysis': analysis_data.get('lifecycle_analysis', {}),
            'price_analysis': analysis_data.get('price_analysis', {}),
            'keyword_analysis': analysis_data.get('keyword_analysis', {}),
            'competitor_analysis': analysis_data.get('competitor_analysis', {}),
            'segmentation_analysis': analysis_data.get('segmentation_analysis', {}),
            'trend_analysis': analysis_data.get('trend_analysis', {}),
            'market_score': analysis_data.get('market_score', {}),
            'validation_stats': validation_stats or {},
            'model_comparison': model_comparison or {},
            'sellerspirit_data': sellerspirit_data or {},
            'blue_ocean_analysis': blue_ocean_analysis or {},
            'advertising_analysis': advertising_analysis or {},
            'seasonality_analysis': seasonality_analysis or {},
            'comprehensive_score': comprehensive_score or {},
            'charts': charts,
            'new_products': [self._format_product(p) for p in new_products[:100]],
            'top_products': [self._format_product(p) for p in
                           sorted(products, key=lambda x: x.reviews_count or 0, reverse=True)[:20]]
        }

        # 生成HTML
        html_content = self._render_template(report_data)

        # 写入文件
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.logger.info(f"HTML报告已生成: {filepath}")
        return str(filepath)

    def _format_product(self, product: Product) -> Dict[str, Any]:
        """
        格式化产品数据用于显示

        Args:
            product: 产品对象

        Returns:
            格式化的产品字典
        """
        return {
            'asin': product.asin,
            'name': product.name,
            'brand': product.brand or 'N/A',
            'price': f"${product.price:.2f}" if product.price else 'N/A',
            'rating': f"{product.rating:.1f}" if product.rating else 'N/A',
            'reviews': product.reviews_count or 0,
            'bsr_rank': product.bsr_rank or 'N/A',
            'available_date': product.available_date or 'N/A'
        }

    def _render_template(self, data: Dict[str, Any]) -> str:
        """
        渲染HTML模板

        Args:
            data: 报告数据

        Returns:
            HTML字符串
        """
        template_str = self._get_template()
        template = Template(template_str)
        return template.render(**data)

    def _get_template(self) -> str:
        """
        获取HTML模板

        Returns:
            HTML模板字符串
        """
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>亚马逊市场分析报告 - {{ keyword }}</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .metric-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .metric-subtitle {
            font-size: 0.85em;
            color: #999;
            margin-top: 5px;
        }
        .metric-source {
            font-size: 0.75em;
            color: #aaa;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px dashed #eee;
        }
        .metric-source::before {
            content: "📊 ";
        }
        .section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section-title {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        .chart-container {
            margin: 20px 0;
            min-height: 400px;
        }
        table.dataTable {
            width: 100% !important;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        .badge-info {
            background: #d1ecf1;
            color: #0c5460;
        }
        .insight-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 4px;
        }
        .insight-title {
            font-weight: bold;
            color: #667eea;
            margin-bottom: 8px;
        }
        footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 亚马逊市场分析报告</h1>
            <div class="subtitle">关键词: {{ keyword }} | 生成时间: {{ generated_at }}</div>
        </header>

        <!-- 核心指标卡片 -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">总产品数</div>
                <div class="metric-value">{{ total_products }}</div>
                <div class="metric-subtitle">ASIN数量</div>
                <div class="metric-source">来源: ScraperAPI + Apify</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">月搜索量</div>
                <div class="metric-value">{{ market_analysis.market_size.monthly_searches or 'N/A' }}</div>
                <div class="metric-subtitle">{{ market_analysis.market_size.size_rating }}</div>
                <div class="metric-source">来源: 卖家精灵</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">购买率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.purchase_rate %}{{ "%.2f"|format(sellerspirit_data.purchase_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">搜索转购买比例</div>
                <div class="metric-source">来源: 卖家精灵</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">点击率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.click_rate %}{{ "%.2f"|format(sellerspirit_data.click_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">搜索转点击比例</div>
                <div class="metric-source">来源: 卖家精灵</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">转化率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.conversion_rate %}{{ "%.2f"|format(sellerspirit_data.conversion_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">点击转购买比例</div>
                <div class="metric-source">来源: 卖家精灵</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">垄断率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.monopoly_rate %}{{ "%.2f"|format(sellerspirit_data.monopoly_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">市场垄断程度</div>
                <div class="metric-source">来源: 卖家精灵</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">竞争强度</div>
                <div class="metric-value">{{ market_analysis.competition.intensity }}</div>
                <div class="metric-subtitle">竞争分数: {{ market_analysis.competition.competition_score }}</div>
                <div class="metric-source">来源: 系统计算</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">市场空白指数</div>
                <div class="metric-value">{{ market_analysis.market_blank_index }}</div>
                <div class="metric-subtitle">{% if market_analysis.market_blank_index > 100 %}高机会{% elif market_analysis.market_blank_index > 50 %}中等机会{% else %}低机会{% endif %}</div>
                <div class="metric-source">来源: 系统计算 (月搜索量/竞品数)</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">新品机会</div>
                <div class="metric-value">{{ new_products_count }}</div>
                <div class="metric-subtitle">近6个月新品</div>
                <div class="metric-source">来源: 系统计算</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">品牌集中度</div>
                <div class="metric-value">{{ market_analysis.brand_concentration.cr4 }}%</div>
                <div class="metric-subtitle">CR4 - {{ market_analysis.brand_concentration.concentration_level }}</div>
                <div class="metric-source">来源: 系统计算</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">平均价格</div>
                <div class="metric-value">${{ price_analysis.statistics.mean }}</div>
                <div class="metric-subtitle">中位数: ${{ price_analysis.statistics.median }}</div>
                <div class="metric-source">来源: Apify API</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">平均评分</div>
                <div class="metric-value">{{ market_analysis.competition.average_rating }}</div>
                <div class="metric-subtitle">平均评论: {{ market_analysis.competition.average_reviews }}</div>
                <div class="metric-source">来源: Apify API</div>
            </div>
        </div>

        <!-- 市场洞察 -->
        <div class="section">
            <h2 class="section-title">📊 市场洞察</h2>
            <div class="insight-box">
                <div class="insight-title">市场机会评估</div>
                <p>
                    该市场属于<strong>{{ market_analysis.market_size.size_rating }}</strong>，
                    竞争强度为<strong>{{ market_analysis.competition.intensity }}</strong>，
                    品牌集中度<strong>{{ market_analysis.brand_concentration.concentration_level }}</strong>。
                    市场空白指数为<strong>{{ market_analysis.market_blank_index }}</strong>，
                    {% if market_analysis.market_blank_index > 100 %}
                    表明存在较大的市场机会。
                    {% elif market_analysis.market_blank_index > 50 %}
                    表明存在中等的市场机会。
                    {% else %}
                    表明市场机会较小，竞争激烈。
                    {% endif %}
                </p>
            </div>
            <div class="insight-box">
                <div class="insight-title">新品趋势</div>
                <p>
                    近6个月发现<strong>{{ new_products_count }}</strong>个新品机会，
                    趋势方向为<strong>{{ lifecycle_analysis.trend.trend_direction }}</strong>
                    {% if lifecycle_analysis.trend.growth_rate %}
                    （增长率: {{ lifecycle_analysis.trend.growth_rate }}%）
                    {% endif %}。
                    新品平均价格为<strong>${{ lifecycle_analysis.characteristics.average_price }}</strong>，
                    平均评分<strong>{{ lifecycle_analysis.characteristics.average_rating }}</strong>。
                </p>
            </div>

            {% if lifecycle_analysis.success_analysis %}
            <div class="insight-box">
                <div class="insight-title">新品成功率分析</div>
                <p>
                    <strong>成功率：</strong>在{{ lifecycle_analysis.success_analysis.total_new_products }}个新品中，
                    <strong>{{ lifecycle_analysis.success_analysis.successful_count }}</strong>个成功
                    （成功率: {{ lifecycle_analysis.success_analysis.success_rate }}%），
                    <strong>{{ lifecycle_analysis.success_analysis.partial_success_count }}</strong>个部分成功，
                    <strong>{{ lifecycle_analysis.success_analysis.failed_count }}</strong>个未达预期。
                    {% if lifecycle_analysis.success_analysis.success_difficulty %}
                    <br><br>
                    <strong>成功难度：</strong>{{ lifecycle_analysis.success_analysis.success_difficulty.difficulty_level | default('未知') }} -
                    {{ lifecycle_analysis.success_analysis.success_difficulty.description | default('') }}
                    <br>
                    <strong>建议：</strong>{{ lifecycle_analysis.success_analysis.success_difficulty.recommendation | default('') }}
                    {% endif %}
                </p>
            </div>
            {% endif %}

            {% if lifecycle_analysis.entry_timing %}
            <div class="insight-box">
                <div class="insight-title">市场进入时机评估</div>
                <p>
                    <strong>时机评分：</strong>{{ lifecycle_analysis.entry_timing.timing_score }}/100 -
                    <span class="badge {% if lifecycle_analysis.entry_timing.timing_grade == '优秀' %}badge-success{% elif lifecycle_analysis.entry_timing.timing_grade == '良好' %}badge-info{% elif lifecycle_analysis.entry_timing.timing_grade == '一般' %}badge-warning{% else %}badge-danger{% endif %}">
                        {{ lifecycle_analysis.entry_timing.timing_grade }}
                    </span>
                    <br><br>
                    <strong>评估因素：</strong>
                    新品占比 {{ lifecycle_analysis.entry_timing.factors.new_product_rate }}%，
                    趋势方向 {{ lifecycle_analysis.entry_timing.factors.trend_direction }}，
                    平均竞品评论数 {{ lifecycle_analysis.entry_timing.factors.avg_competitor_reviews }}
                    <br><br>
                    <strong>建议：</strong>{{ lifecycle_analysis.entry_timing.timing_recommendation }}
                </p>
            </div>
            {% endif %}

            {% if lifecycle_analysis.lifecycle_distribution %}
            <div class="insight-box">
                <div class="insight-title">生命周期阶段分布</div>
                <p>
                    <strong>市场成熟度：</strong>{{ lifecycle_analysis.lifecycle_distribution.market_maturity }} -
                    {{ lifecycle_analysis.lifecycle_distribution.market_maturity_desc }}
                </p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">生命周期阶段</th>
                            <th style="padding: 10px; text-align: center;">产品数量</th>
                            <th style="padding: 10px; text-align: center;">占比</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for stage, count in lifecycle_analysis.lifecycle_distribution.counts.items() %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">{{ stage }}</td>
                            <td style="padding: 10px; text-align: center;">{{ count }}</td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge badge-info">{{ lifecycle_analysis.lifecycle_distribution.percentages[stage] }}%</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}

            {% if lifecycle_analysis.opportunity_score %}
            <div class="insight-box" style="background: linear-gradient(135deg, #f5f7fa 0%, #e8f4f8 100%);">
                <div class="insight-title">新品机会评分</div>
                <div style="display: flex; align-items: center; margin-top: 15px;">
                    <div style="font-size: 3em; font-weight: bold; color: {% if lifecycle_analysis.opportunity_score.grade == 'A' %}#28a745{% elif lifecycle_analysis.opportunity_score.grade == 'B' %}#17a2b8{% elif lifecycle_analysis.opportunity_score.grade == 'C' %}#ffc107{% else %}#dc3545{% endif %};">
                        {{ lifecycle_analysis.opportunity_score.grade }}
                    </div>
                    <div style="margin-left: 20px;">
                        <div style="font-size: 1.5em; font-weight: bold;">{{ lifecycle_analysis.opportunity_score.total_score }}/100</div>
                        <div style="color: #666;">{{ lifecycle_analysis.opportunity_score.grade_desc }}</div>
                    </div>
                </div>
                <p style="margin-top: 15px;">
                    <strong>建议：</strong>{{ lifecycle_analysis.opportunity_score.recommendation }}
                </p>
            </div>
            {% endif %}
            {# 关键词扩展建议 - 暂时屏蔽，需要时再启用 #}
            {# {% if sellerspirit_data and sellerspirit_data.keyword_extensions %}
            <div class="insight-box">
                <div class="insight-title">🔍 关键词扩展建议</div>
                <p>基于卖家精灵数据分析，以下是相关的关键词扩展建议，可用于优化产品listing和广告投放：</p>
                <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 8px;">
                    {% for keyword in sellerspirit_data.keyword_extensions %}
                    <span class="badge badge-info">{{ keyword }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %} #}
        </div>

        <!-- AI分类验证 -->
        {% if validation_stats.has_data %}
        <div class="section">
            <h2 class="section-title">🤖 AI分类验证</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">已验证产品</div>
                    <div class="metric-value">{{ validation_stats.validated }}</div>
                    <div class="metric-subtitle">总产品: {{ validation_stats.total }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">相关产品</div>
                    <div class="metric-value">{{ validation_stats.relevant }}</div>
                    <div class="metric-subtitle">相关率: {{ "%.1f"|format(validation_stats.relevant_rate * 100) }}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">不相关产品</div>
                    <div class="metric-value">{{ validation_stats.irrelevant }}</div>
                    <div class="metric-subtitle">需要过滤</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">分类正确</div>
                    <div class="metric-value">{{ validation_stats.correct_category }}</div>
                    <div class="metric-subtitle">准确率: {{ "%.1f"|format(validation_stats.correct_rate * 100) }}%</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">AI验证结果分析</div>
                <p>
                    通过AI分析，在{{ validation_stats.total }}个产品中，
                    <strong>{{ validation_stats.relevant }}</strong>个产品（{{ "%.1f"|format(validation_stats.relevant_rate * 100) }}%）与关键词相关，
                    符合亚马逊搜索结果的相关性要求。
                    {% if validation_stats.irrelevant > 0 %}
                    发现<strong>{{ validation_stats.irrelevant }}</strong>个不相关产品，建议从分析中排除。
                    {% endif %}
                    <br><br>
                    在分类准确性方面，<strong>{{ validation_stats.correct_category }}</strong>个产品（{{ "%.1f"|format(validation_stats.correct_rate * 100) }}%）
                    的分类符合亚马逊的分类标准。
                    {% if validation_stats.incorrect_category > 0 %}
                    有<strong>{{ validation_stats.incorrect_category }}</strong>个产品的分类可能需要优化。
                    {% endif %}
                </p>
            </div>
        </div>
        {% endif %}

        <!-- 模型对比分析 -->
        {% if model_comparison.total_compared %}
        <div class="section">
            <h2 class="section-title">🔬 AI模型对比分析</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">对比产品数</div>
                    <div class="metric-value">{{ model_comparison.total_compared }}</div>
                    <div class="metric-subtitle">Claude vs Gemini</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">整体一致率</div>
                    <div class="metric-value">{{ "%.1f"|format(model_comparison.overall_agreement_rate * 100) }}%</div>
                    <div class="metric-subtitle">两个模型的总体一致性</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">相关性一致率</div>
                    <div class="metric-value">{{ "%.1f"|format(model_comparison.relevance_agreement_rate * 100) }}%</div>
                    <div class="metric-subtitle">不一致: {{ model_comparison.relevance_disagreement_count }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">分类一致率</div>
                    <div class="metric-value">{{ "%.1f"|format(model_comparison.category_agreement_rate * 100) }}%</div>
                    <div class="metric-subtitle">不一致: {{ model_comparison.category_disagreement_count }}</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">模型对比结果分析</div>
                <p>
                    对比了Claude和Gemini两个AI模型对<strong>{{ model_comparison.total_compared }}</strong>个产品的分类验证结果。
                    <br><br>
                    <strong>整体一致性：</strong>两个模型的整体一致率为<strong>{{ "%.1f"|format(model_comparison.overall_agreement_rate * 100) }}%</strong>，
                    {% if model_comparison.overall_agreement_rate >= 0.9 %}
                    表明两个模型的判断高度一致，验证结果可信度高。
                    {% elif model_comparison.overall_agreement_rate >= 0.8 %}
                    表明两个模型的判断基本一致，验证结果较为可靠。
                    {% else %}
                    存在一定差异，建议人工复核不一致的产品。
                    {% endif %}
                    <br><br>
                    <strong>相关性判断：</strong>在产品相关性判断上，两个模型的一致率为<strong>{{ "%.1f"|format(model_comparison.relevance_agreement_rate * 100) }}%</strong>，
                    有<strong>{{ model_comparison.relevance_disagreement_count }}</strong>个产品的相关性判断存在分歧。
                    <br><br>
                    <strong>分类准确性：</strong>在分类准确性判断上，两个模型的一致率为<strong>{{ "%.1f"|format(model_comparison.category_agreement_rate * 100) }}%</strong>，
                    有<strong>{{ model_comparison.category_disagreement_count }}</strong>个产品的分类判断存在分歧。
                    {% if model_comparison.disagreement_asins %}
                    <br><br>
                    <strong>不一致产品：</strong>共发现<strong>{{ model_comparison.disagreement_asins|length }}</strong>个产品存在判断差异，
                    已导出到CSV文件供进一步分析。
                    {% endif %}
                </p>
            </div>

            {% if model_comparison.disagreement_details %}
            <div class="insight-box" style="margin-top: 20px;">
                <div class="insight-title">不一致产品详情（前10个）</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">ASIN</th>
                            <th style="padding: 10px; text-align: left;">产品名称</th>
                            <th style="padding: 10px; text-align: center;">Claude判断</th>
                            <th style="padding: 10px; text-align: center;">Gemini判断</th>
                            <th style="padding: 10px; text-align: left;">差异类型</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for detail in model_comparison.disagreement_details[:10] %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">{{ detail.asin }}</td>
                            <td style="padding: 10px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {{ detail.product_name }}
                            </td>
                            <td style="padding: 10px; text-align: center;">
                                <span style="color: {% if detail.claude_relevant %}green{% else %}red{% endif %};">
                                    {{ '相关' if detail.claude_relevant else '不相关' }}
                                </span>
                                {% if detail.claude_category_correct is not none %}
                                / <span style="color: {% if detail.claude_category_correct %}green{% else %}orange{% endif %};">
                                    {{ '分类正确' if detail.claude_category_correct else '分类错误' }}
                                </span>
                                {% endif %}
                            </td>
                            <td style="padding: 10px; text-align: center;">
                                <span style="color: {% if detail.gemini_relevant %}green{% else %}red{% endif %};">
                                    {{ '相关' if detail.gemini_relevant else '不相关' }}
                                </span>
                                {% if detail.gemini_category_correct is not none %}
                                / <span style="color: {% if detail.gemini_category_correct %}green{% else %}orange{% endif %};">
                                    {{ '分类正确' if detail.gemini_category_correct else '分类错误' }}
                                </span>
                                {% endif %}
                            </td>
                            <td style="padding: 10px;">
                                {% if detail.relevance_disagree %}
                                <span style="background: #ffe6e6; padding: 2px 8px; border-radius: 3px;">相关性</span>
                                {% endif %}
                                {% if detail.category_disagree %}
                                <span style="background: #fff3e6; padding: 2px 8px; border-radius: 3px;">分类</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <!-- 价格分析 -->
        <div class="section">
            <h2 class="section-title">💰 价格分析</h2>
            <div class="chart-container" id="priceDistChart"></div>
            <div class="chart-container" id="priceRatingChart"></div>
        </div>

        <!-- 品牌分析 -->
        <div class="section">
            <h2 class="section-title">🏢 品牌分析</h2>
            <div class="chart-container" id="brandChart"></div>
        </div>

        <!-- 新品分析 -->
        <div class="section">
            <h2 class="section-title">🆕 新品分析</h2>
            <div class="chart-container" id="newProductTrendChart"></div>
            <div class="chart-container" id="newProductPriceChart"></div>
        </div>

        <!-- 综合评分 -->
        {% if market_score.total_score %}
        <div class="section">
            <h2 class="section-title">⭐ 市场综合评分</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">市场总分</div>
                    <div class="metric-value">{{ market_score.total_score }}</div>
                    <div class="metric-subtitle">满分100分</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">市场评级</div>
                    <div class="metric-value">{{ market_score.grade }}</div>
                    <div class="metric-subtitle">
                        {% if market_score.grade in ['A+', 'A'] %}优秀
                        {% elif market_score.grade in ['B+', 'B'] %}良好
                        {% elif market_score.grade in ['C+', 'C'] %}一般
                        {% else %}较差{% endif %}
                    </div>
                </div>
                <div class="metric-card" style="grid-column: span 2;">
                    <div class="metric-label">市场建议</div>
                    <div class="metric-value" style="font-size: 1.2em;">{{ market_score.recommendation }}</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">评分维度分析</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">评分维度</th>
                            <th style="padding: 10px; text-align: center;">得分</th>
                            <th style="padding: 10px; text-align: center;">满分</th>
                            <th style="padding: 10px; text-align: center;">完成度</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for factor in market_score.key_factors %}
                        {% if factor is mapping %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">{{ factor.factor }}</td>
                            <td style="padding: 10px; text-align: center;">{{ factor.score }}</td>
                            <td style="padding: 10px; text-align: center;">{{ factor.max_score }}</td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if factor.percentage >= 80 %}badge-success{% elif factor.percentage >= 60 %}badge-info{% elif factor.percentage >= 40 %}badge-warning{% else %}badge-danger{% endif %}">
                                    {{ factor.percentage }}%
                                </span>
                            </td>
                        </tr>
                        {% endif %}
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <!-- 竞品对标分析 -->
        {% if competitor_analysis.top_competitors %}
        <div class="section">
            <h2 class="section-title">🎯 竞品对标分析</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">品牌数量</div>
                    <div class="metric-value">{{ competitor_analysis.brand_count }}</div>
                    <div class="metric-subtitle">市场品牌总数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Top竞品数</div>
                    <div class="metric-value">{{ competitor_analysis.top_competitors|length }}</div>
                    <div class="metric-subtitle">头部竞争对手</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">平均市场份额</div>
                    <div class="metric-value">{{ "%.1f"|format(competitor_analysis.average_market_share) }}%</div>
                    <div class="metric-subtitle">Top竞品平均份额</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">竞争格局</div>
                    <div class="metric-value">{{ competitor_analysis.competition_pattern }}</div>
                    <div class="metric-subtitle">市场集中度</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">Top 10 竞品详情</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">排名</th>
                            <th style="padding: 10px; text-align: left;">品牌</th>
                            <th style="padding: 10px; text-align: center;">产品数</th>
                            <th style="padding: 10px; text-align: center;">市场份额</th>
                            <th style="padding: 10px; text-align: center;">平均价格</th>
                            <th style="padding: 10px; text-align: center;">平均评分</th>
                            <th style="padding: 10px; text-align: center;">平均评论数</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for comp in competitor_analysis.top_competitors[:10] %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">{{ loop.index }}</td>
                            <td style="padding: 10px;"><strong>{{ comp.brand }}</strong></td>
                            <td style="padding: 10px; text-align: center;">{{ comp.product_count }}</td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if comp.market_share >= 10 %}badge-danger{% elif comp.market_share >= 5 %}badge-warning{% else %}badge-info{% endif %}">
                                    {{ "%.1f"|format(comp.market_share) }}%
                                </span>
                            </td>
                            <td style="padding: 10px; text-align: center;">${{ "%.2f"|format(comp.avg_price) }}</td>
                            <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(comp.avg_rating) }}</td>
                            <td style="padding: 10px; text-align: center;">{{ comp.avg_reviews }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <!-- 市场细分分析 -->
        {% if segmentation_analysis.price_segments %}
        <div class="section">
            <h2 class="section-title">📊 市场细分分析</h2>
            <h3 style="margin: 20px 0 10px 0; color: #667eea;">价格段分析</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <thead>
                    <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                        <th style="padding: 10px; text-align: left;">价格段</th>
                        <th style="padding: 10px; text-align: center;">产品数</th>
                        <th style="padding: 10px; text-align: center;">占比</th>
                        <th style="padding: 10px; text-align: center;">平均价格</th>
                        <th style="padding: 10px; text-align: center;">平均评分</th>
                        <th style="padding: 10px; text-align: center;">平均销量</th>
                    </tr>
                </thead>
                <tbody>
                    {% for seg_name, seg_data in segmentation_analysis.price_segments.segments.items() %}
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;"><strong>{{ seg_name }}</strong></td>
                        <td style="padding: 10px; text-align: center;">{{ seg_data.product_count }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(seg_data.market_share) }}%</td>
                        <td style="padding: 10px; text-align: center;">${{ "%.2f"|format(seg_data.avg_price) }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(seg_data.avg_rating) }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.0f"|format(seg_data.avg_sales) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <h3 style="margin: 20px 0 10px 0; color: #667eea;">品牌段分析 (Top 10)</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                        <th style="padding: 10px; text-align: left;">品牌</th>
                        <th style="padding: 10px; text-align: center;">产品数</th>
                        <th style="padding: 10px; text-align: center;">市场份额</th>
                        <th style="padding: 10px; text-align: center;">平均价格</th>
                        <th style="padding: 10px; text-align: center;">平均评分</th>
                        <th style="padding: 10px; text-align: center;">总销量</th>
                    </tr>
                </thead>
                <tbody>
                    {% for brand in segmentation_analysis.brand_segments.top_brands[:10] %}
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;"><strong>{{ brand.brand }}</strong></td>
                        <td style="padding: 10px; text-align: center;">{{ brand.product_count }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(brand.market_share) }}%</td>
                        <td style="padding: 10px; text-align: center;">${{ "%.2f"|format(brand.avg_price) }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(brand.avg_rating) }}</td>
                        <td style="padding: 10px; text-align: center;">{{ brand.total_sales }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <!-- 趋势预测分析 -->
        {% if trend_analysis.market_trend %}
        <div class="section">
            <h2 class="section-title">📈 趋势预测分析</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">市场趋势</div>
                    <div class="metric-value">{{ trend_analysis.market_trend.trend_direction }}</div>
                    <div class="metric-subtitle">整体走向</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">趋势强度</div>
                    <div class="metric-value">{{ trend_analysis.market_trend.trend_strength }}/100</div>
                    <div class="metric-subtitle">
                        {% if trend_analysis.market_trend.trend_strength >= 70 %}强劲
                        {% elif trend_analysis.market_trend.trend_strength >= 40 %}中等
                        {% else %}微弱{% endif %}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">新品占比</div>
                    <div class="metric-value">{{ "%.1f"|format(trend_analysis.new_product_trend.new_product_rate) }}%</div>
                    <div class="metric-subtitle">{{ trend_analysis.new_product_trend.new_product_count }} 个新品</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">竞争趋势</div>
                    <div class="metric-value">{{ trend_analysis.competition_trend.trend }}</div>
                    <div class="metric-subtitle">{{ trend_analysis.competition_trend.competition_level }}</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">趋势分析洞察</div>
                <p>
                    <strong>市场趋势：</strong>当前市场呈现<strong>{{ trend_analysis.market_trend.trend_direction }}</strong>趋势，
                    趋势强度为<strong>{{ trend_analysis.market_trend.trend_strength }}/100</strong>。
                    {% if trend_analysis.market_trend.trend_direction == 'growing' %}
                    市场正在快速增长，是进入的好时机。
                    {% elif trend_analysis.market_trend.trend_direction == 'stable' %}
                    市场相对稳定，适合稳健经营。
                    {% else %}
                    市场可能面临挑战，需谨慎评估。
                    {% endif %}
                    <br><br>
                    <strong>新品动态：</strong>新品占比为<strong>{{ "%.1f"|format(trend_analysis.new_product_trend.new_product_rate) }}%</strong>，
                    {% if trend_analysis.new_product_trend.new_product_rate > 20 %}
                    表明市场活跃度高，创新机会多。
                    {% elif trend_analysis.new_product_trend.new_product_rate > 10 %}
                    市场保持一定活力。
                    {% else %}
                    新品进入速度放缓。
                    {% endif %}
                    <br><br>
                    <strong>竞争态势：</strong>{{ trend_analysis.competition_trend.interpretation }}
                </p>
            </div>
        </div>
        {% endif %}

        <!-- 蓝海产品分析 -->
        {% if blue_ocean_analysis.blue_ocean_count %}
        <div class="section">
            <h2 class="section-title">🌊 蓝海产品分析</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">蓝海产品数</div>
                    <div class="metric-value">{{ blue_ocean_analysis.blue_ocean_count }}</div>
                    <div class="metric-subtitle">占比: {{ "%.1f"|format(blue_ocean_analysis.blue_ocean_rate) }}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">市场竞争指数</div>
                    <div class="metric-value">{{ "%.1f"|format(blue_ocean_analysis.market_competition.competition_index) }}</div>
                    <div class="metric-subtitle">
                        {% if blue_ocean_analysis.market_competition.competition_index < 40 %}低竞争
                        {% elif blue_ocean_analysis.market_competition.competition_index < 60 %}中等竞争
                        {% else %}高竞争{% endif %}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">市场机会等级</div>
                    <div class="metric-value">{{ blue_ocean_analysis.opportunity_assessment.opportunity_desc }}</div>
                    <div class="metric-subtitle">{{ blue_ocean_analysis.opportunity_assessment.opportunity_level }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">平均蓝海评分</div>
                    <div class="metric-value">{{ "%.1f"|format(blue_ocean_analysis.blue_ocean_products[0].blue_ocean_score if blue_ocean_analysis.blue_ocean_products else 0) }}</div>
                    <div class="metric-subtitle">满分100分</div>
                </div>
            </div>

            <div class="insight-box">
                <div class="insight-title">🎯 市场机会评估</div>
                <p>
                    <strong>蓝海产品占比：</strong>在{{ blue_ocean_analysis.market_competition.total_brands }}个产品中，
                    发现<strong>{{ blue_ocean_analysis.blue_ocean_count }}</strong>个蓝海产品机会，
                    占比<strong>{{ "%.1f"|format(blue_ocean_analysis.blue_ocean_rate) }}%</strong>。
                    <br><br>
                    <strong>竞争环境：</strong>市场竞争指数为<strong>{{ "%.1f"|format(blue_ocean_analysis.market_competition.competition_index) }}</strong>，
                    平均评论数<strong>{{ "%.0f"|format(blue_ocean_analysis.market_competition.avg_reviews) }}</strong>，
                    平均评分<strong>{{ "%.1f"|format(blue_ocean_analysis.market_competition.avg_rating) }}</strong>，
                    高评分产品占比<strong>{{ "%.1f"|format(blue_ocean_analysis.market_competition.high_rating_rate) }}%</strong>。
                    <br><br>
                    <strong>机会评估：</strong>{{ blue_ocean_analysis.opportunity_assessment.opportunity_desc }}。
                    {% for rec in blue_ocean_analysis.opportunity_assessment.recommendations %}
                    <br>• {{ rec }}
                    {% endfor %}
                </p>
            </div>

            {% if blue_ocean_analysis.segments %}
            <div class="insight-box" style="margin-top: 20px;">
                <div class="insight-title">💰 价格区间分析</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">价格区间</th>
                            <th style="padding: 10px; text-align: center;">产品数</th>
                            <th style="padding: 10px; text-align: center;">平均评分</th>
                            <th style="padding: 10px; text-align: center;">平均销量</th>
                            <th style="padding: 10px; text-align: center;">平均竞争指数</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for seg in blue_ocean_analysis.segments %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;"><strong>{{ seg.price_range }}</strong></td>
                            <td style="padding: 10px; text-align: center;">{{ seg.count }}</td>
                            <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(seg.avg_rating) }}</td>
                            <td style="padding: 10px; text-align: center;">{{ "%.0f"|format(seg.avg_sales) }}</td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if seg.avg_competition < 40 %}badge-success{% elif seg.avg_competition < 60 %}badge-info{% else %}badge-warning{% endif %}">
                                    {{ "%.1f"|format(seg.avg_competition) }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}

            {% if blue_ocean_analysis.top_opportunities %}
            <div class="insight-box" style="margin-top: 20px;">
                <div class="insight-title">🏆 Top 10 蓝海产品机会</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">ASIN</th>
                            <th style="padding: 10px; text-align: left;">产品名称</th>
                            <th style="padding: 10px; text-align: center;">价格</th>
                            <th style="padding: 10px; text-align: center;">月销量</th>
                            <th style="padding: 10px; text-align: center;">评论数</th>
                            <th style="padding: 10px; text-align: center;">评分</th>
                            <th style="padding: 10px; text-align: center;">蓝海评分</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for product in blue_ocean_analysis.top_opportunities[:10] %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">{{ product.asin }}</td>
                            <td style="padding: 10px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {{ product.name }}
                            </td>
                            <td style="padding: 10px; text-align: center;">${{ "%.2f"|format(product.price) }}</td>
                            <td style="padding: 10px; text-align: center;">{{ product.sales_volume }}</td>
                            <td style="padding: 10px; text-align: center;">{{ product.reviews_count }}</td>
                            <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(product.rating) }}</td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if product.blue_ocean_score >= 70 %}badge-success{% elif product.blue_ocean_score >= 50 %}badge-info{% else %}badge-warning{% endif %}">
                                    {{ "%.1f"|format(product.blue_ocean_score) }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <!-- 广告成本分析 -->
        {% if advertising_analysis.bid_analysis %}
        <div class="section">
            <h2 class="section-title">💰 广告成本分析</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">建议竞价</div>
                    <div class="metric-value">${{ "%.2f"|format(advertising_analysis.bid_analysis.suggested_bid) }}</div>
                    <div class="metric-subtitle">竞价范围: ${{ "%.2f"|format(advertising_analysis.bid_analysis.bid_range.min) }} - ${{ "%.2f"|format(advertising_analysis.bid_analysis.bid_range.max) }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">预估CPC</div>
                    <div class="metric-value">${{ "%.2f"|format(advertising_analysis.cpc_analysis.estimated_cpc) }}</div>
                    <div class="metric-subtitle">CPC等级: {{ advertising_analysis.cpc_analysis.cpc_level }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">预估ACoS</div>
                    <div class="metric-value">{{ "%.1f"|format(advertising_analysis.acos_analysis.estimated_acos) }}%</div>
                    <div class="metric-subtitle">ACoS等级: {{ advertising_analysis.acos_analysis.acos_level }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">广告可行性</div>
                    <div class="metric-value">{{ advertising_analysis.advertising_feasibility.feasibility_level }}</div>
                    <div class="metric-subtitle">评分: {{ advertising_analysis.advertising_feasibility.feasibility_score }}/100</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">广告投放建议</div>
                <p>
                    <strong>竞价策略：</strong>{{ advertising_analysis.bid_analysis.bid_strategy }}<br><br>
                    <strong>ACoS分析：</strong>{{ advertising_analysis.acos_analysis.acos_interpretation }}<br><br>
                    <strong>可行性评估：</strong>{{ advertising_analysis.advertising_feasibility.recommendation }}
                </p>
            </div>
            {% if advertising_analysis.roi_projection %}
            <div class="insight-box" style="margin-top: 20px;">
                <div class="insight-title">ROI预测</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">指标</th>
                            <th style="padding: 10px; text-align: center;">保守估计</th>
                            <th style="padding: 10px; text-align: center;">中等估计</th>
                            <th style="padding: 10px; text-align: center;">乐观估计</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">月广告支出</td>
                            <td style="padding: 10px; text-align: center;">${{ "%.0f"|format(advertising_analysis.roi_projection.scenarios.conservative.monthly_ad_spend) }}</td>
                            <td style="padding: 10px; text-align: center;">${{ "%.0f"|format(advertising_analysis.roi_projection.scenarios.moderate.monthly_ad_spend) }}</td>
                            <td style="padding: 10px; text-align: center;">${{ "%.0f"|format(advertising_analysis.roi_projection.scenarios.optimistic.monthly_ad_spend) }}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">预估销售额</td>
                            <td style="padding: 10px; text-align: center;">${{ "%.0f"|format(advertising_analysis.roi_projection.scenarios.conservative.estimated_sales) }}</td>
                            <td style="padding: 10px; text-align: center;">${{ "%.0f"|format(advertising_analysis.roi_projection.scenarios.moderate.estimated_sales) }}</td>
                            <td style="padding: 10px; text-align: center;">${{ "%.0f"|format(advertising_analysis.roi_projection.scenarios.optimistic.estimated_sales) }}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;">预估ROI</td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if advertising_analysis.roi_projection.scenarios.conservative.roi > 0 %}badge-success{% else %}badge-danger{% endif %}">
                                    {{ "%.1f"|format(advertising_analysis.roi_projection.scenarios.conservative.roi) }}%
                                </span>
                            </td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if advertising_analysis.roi_projection.scenarios.moderate.roi > 0 %}badge-success{% else %}badge-danger{% endif %}">
                                    {{ "%.1f"|format(advertising_analysis.roi_projection.scenarios.moderate.roi) }}%
                                </span>
                            </td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if advertising_analysis.roi_projection.scenarios.optimistic.roi > 0 %}badge-success{% else %}badge-danger{% endif %}">
                                    {{ "%.1f"|format(advertising_analysis.roi_projection.scenarios.optimistic.roi) }}%
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <!-- 季节性分析 -->
        {% if seasonality_analysis.seasonality_level %}
        <div class="section">
            <h2 class="section-title">📅 季节性分析</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">季节性等级</div>
                    <div class="metric-value">{{ seasonality_analysis.seasonality_level }}</div>
                    <div class="metric-subtitle">季节性指数: {{ seasonality_analysis.seasonality_index }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">当前季节状态</div>
                    <div class="metric-value">{{ seasonality_analysis.current_season_status.status }}</div>
                    <div class="metric-subtitle">{{ seasonality_analysis.current_season_status.recommendation }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">销售高峰月份</div>
                    <div class="metric-value">{{ seasonality_analysis.peak_months|join(', ') if seasonality_analysis.peak_months else 'N/A' }}</div>
                    <div class="metric-subtitle">最佳销售时机</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">销售低谷月份</div>
                    <div class="metric-value">{{ seasonality_analysis.low_months|join(', ') if seasonality_analysis.low_months else 'N/A' }}</div>
                    <div class="metric-subtitle">需要注意的时期</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">季节性洞察</div>
                <p>
                    <strong>季节性特征：</strong>{{ seasonality_analysis.seasonality_description }}<br><br>
                    <strong>当前状态：</strong>{{ seasonality_analysis.current_season_status.description }}<br><br>
                    {% if seasonality_analysis.entry_timing_recommendation %}
                    <strong>进入时机建议：</strong>{{ seasonality_analysis.entry_timing_recommendation.recommendation }}<br>
                    最佳进入月份: {{ seasonality_analysis.entry_timing_recommendation.best_entry_months|join(', ') if seasonality_analysis.entry_timing_recommendation.best_entry_months else '全年均可' }}
                    {% endif %}
                </p>
            </div>
            {% if seasonality_analysis.monthly_analysis %}
            <div class="insight-box" style="margin-top: 20px;">
                <div class="insight-title">月度趋势分析</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: center;">月份</th>
                            <th style="padding: 10px; text-align: center;">搜索指数</th>
                            <th style="padding: 10px; text-align: center;">季节性标签</th>
                            <th style="padding: 10px; text-align: center;">建议</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for month_data in seasonality_analysis.monthly_analysis %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; text-align: center;">{{ month_data.month }}月</td>
                            <td style="padding: 10px; text-align: center;">{{ month_data.index }}</td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if month_data.tag == '高峰' %}badge-success{% elif month_data.tag == '低谷' %}badge-danger{% else %}badge-info{% endif %}">
                                    {{ month_data.tag }}
                                </span>
                            </td>
                            <td style="padding: 10px; text-align: center;">{{ month_data.suggestion }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <!-- 综合评分 (增强版) -->
        {% if comprehensive_score.total_score %}
        <div class="section">
            <h2 class="section-title">🎯 市场综合评分 (4大方法论)</h2>
            <div class="metrics-grid">
                <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">综合总分</div>
                    <div class="metric-value" style="color: white; font-size: 3em;">{{ "%.1f"|format(comprehensive_score.total_score) }}</div>
                    <div class="metric-subtitle" style="color: rgba(255,255,255,0.8);">满分100分</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">市场等级</div>
                    <div class="metric-value" style="font-size: 2.5em;">{{ comprehensive_score.grade }}</div>
                    <div class="metric-subtitle">{{ comprehensive_score.grade_description }}</div>
                </div>
                <div class="metric-card" style="grid-column: span 2;">
                    <div class="metric-label">综合建议</div>
                    <div class="metric-value" style="font-size: 1.2em; line-height: 1.5;">{{ comprehensive_score.recommendation }}</div>
                </div>
            </div>

            <div class="insight-box">
                <div class="insight-title">4大维度评分详情</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <thead>
                        <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">评分维度</th>
                            <th style="padding: 10px; text-align: center;">得分</th>
                            <th style="padding: 10px; text-align: center;">权重</th>
                            <th style="padding: 10px; text-align: center;">加权得分</th>
                            <th style="padding: 10px; text-align: left;">说明</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if comprehensive_score.dimension_scores %}
                        {% for dim_name, dim_data in comprehensive_score.dimension_scores.items() %}
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px;"><strong>{{ dim_data.name if dim_data.name else dim_name }}</strong></td>
                            <td style="padding: 10px; text-align: center;">
                                <span class="badge {% if dim_data.score >= 70 %}badge-success{% elif dim_data.score >= 50 %}badge-info{% elif dim_data.score >= 30 %}badge-warning{% else %}badge-danger{% endif %}">
                                    {{ "%.1f"|format(dim_data.score) }}
                                </span>
                            </td>
                            <td style="padding: 10px; text-align: center;">{{ "%.0f"|format(dim_data.weight * 100) }}%</td>
                            <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(dim_data.weighted_score) }}</td>
                            <td style="padding: 10px;">{{ dim_data.description if dim_data.description else '' }}</td>
                        </tr>
                        {% endfor %}
                        {% endif %}
                    </tbody>
                </table>
            </div>

            {% if comprehensive_score.key_insights %}
            <div class="insight-box" style="margin-top: 20px;">
                <div class="insight-title">关键洞察</div>
                <ul style="margin-top: 10px; padding-left: 20px;">
                    {% for insight in comprehensive_score.key_insights %}
                    <li style="margin-bottom: 8px;">{{ insight }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}

            {% if comprehensive_score.risk_factors %}
            <div class="insight-box" style="margin-top: 20px; border-left-color: #dc3545;">
                <div class="insight-title" style="color: #dc3545;">风险因素</div>
                <ul style="margin-top: 10px; padding-left: 20px;">
                    {% for risk in comprehensive_score.risk_factors %}
                    <li style="margin-bottom: 8px;">{{ risk }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}

            {% if comprehensive_score.opportunity_factors %}
            <div class="insight-box" style="margin-top: 20px; border-left-color: #28a745;">
                <div class="insight-title" style="color: #28a745;">机会因素</div>
                <ul style="margin-top: 10px; padding-left: 20px;">
                    {% for opp in comprehensive_score.opportunity_factors %}
                    <li style="margin-bottom: 8px;">{{ opp }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <!-- 新品机会列表 -->
        <div class="section">
            <h2 class="section-title">🎯 新品机会列表 (Top 100)</h2>
            <table id="newProductsTable" class="display">
                <thead>
                    <tr>
                        <th>ASIN</th>
                        <th>产品名称</th>
                        <th>品牌</th>
                        <th>价格</th>
                        <th>评分</th>
                        <th>评论数</th>
                        <th>BSR排名</th>
                        <th>上架时间</th>
                    </tr>
                </thead>
                <tbody>
                    {% for product in new_products %}
                    <tr>
                        <td>{{ product.asin }}</td>
                        <td>{{ product.name }}</td>
                        <td>{{ product.brand }}</td>
                        <td>{{ product.price }}</td>
                        <td>{{ product.rating }}</td>
                        <td>{{ product.reviews }}</td>
                        <td>{{ product.bsr_rank }}</td>
                        <td>{{ product.available_date }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Top产品 -->
        <div class="section">
            <h2 class="section-title">🏆 Top 20 热销产品</h2>
            <table id="topProductsTable" class="display">
                <thead>
                    <tr>
                        <th>ASIN</th>
                        <th>产品名称</th>
                        <th>品牌</th>
                        <th>价格</th>
                        <th>评分</th>
                        <th>评论数</th>
                        <th>BSR排名</th>
                    </tr>
                </thead>
                <tbody>
                    {% for product in top_products %}
                    <tr>
                        <td>{{ product.asin }}</td>
                        <td>{{ product.name }}</td>
                        <td>{{ product.brand }}</td>
                        <td>{{ product.price }}</td>
                        <td>{{ product.rating }}</td>
                        <td>{{ product.reviews }}</td>
                        <td>{{ product.bsr_rank }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <footer>
            <p>© 2024 亚马逊市场分析系统 | 数据仅供参考</p>
        </footer>
    </div>

    <script>
        // 初始化DataTables
        $(document).ready(function() {
            $('#newProductsTable').DataTable({
                order: [[5, 'desc']],
                pageLength: 25,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/zh.json'
                }
            });

            $('#topProductsTable').DataTable({
                order: [[5, 'desc']],
                pageLength: 20,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/zh.json'
                }
            });
        });

        // 渲染图表
        {% if charts.price_distribution %}
        Plotly.newPlot('priceDistChart', {{ charts.price_distribution|safe }}.data, {{ charts.price_distribution|safe }}.layout);
        {% endif %}

        {% if charts.price_rating_scatter %}
        Plotly.newPlot('priceRatingChart', {{ charts.price_rating_scatter|safe }}.data, {{ charts.price_rating_scatter|safe }}.layout);
        {% endif %}

        {% if charts.brand_concentration %}
        Plotly.newPlot('brandChart', {{ charts.brand_concentration|safe }}.data, {{ charts.brand_concentration|safe }}.layout);
        {% endif %}

        {% if charts.new_product_trend %}
        Plotly.newPlot('newProductTrendChart', {{ charts.new_product_trend|safe }}.data, {{ charts.new_product_trend|safe }}.layout);
        {% endif %}

        {% if charts.new_product_price %}
        Plotly.newPlot('newProductPriceChart', {{ charts.new_product_price|safe }}.data, {{ charts.new_product_price|safe }}.layout);
        {% endif %}
    </script>
</body>
</html>"""
