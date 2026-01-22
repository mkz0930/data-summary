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
        filename: str = "report.html"
    ) -> str:
        """
        生成完整的HTML报告

        Args:
            keyword: 搜索关键词
            products: 产品列表
            new_products: 新品列表
            analysis_data: 分析数据
            charts: 图表JSON字典
            validation_stats: AI验证统计数据
            model_comparison: 模型对比结果
            sellerspirit_data: 卖家精灵数据
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
            </div>
            <div class="metric-card">
                <div class="metric-label">月搜索量</div>
                <div class="metric-value">{{ market_analysis.market_size.monthly_searches or 'N/A' }}</div>
                <div class="metric-subtitle">{{ market_analysis.market_size.size_rating }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">购买率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.purchase_rate %}{{ "%.2f"|format(sellerspirit_data.purchase_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">搜索转购买比例</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">点击率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.click_rate %}{{ "%.2f"|format(sellerspirit_data.click_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">搜索转点击比例</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">转化率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.conversion_rate %}{{ "%.2f"|format(sellerspirit_data.conversion_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">点击转购买比例</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">垄断率</div>
                <div class="metric-value">{% if sellerspirit_data and sellerspirit_data.monopoly_rate %}{{ "%.2f"|format(sellerspirit_data.monopoly_rate) }}%{% else %}N/A{% endif %}</div>
                <div class="metric-subtitle">市场垄断程度</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">竞争强度</div>
                <div class="metric-value">{{ market_analysis.competition.intensity }}</div>
                <div class="metric-subtitle">竞争分数: {{ market_analysis.competition.competition_score }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">市场空白指数</div>
                <div class="metric-value">{{ market_analysis.market_blank_index }}</div>
                <div class="metric-subtitle">{% if market_analysis.market_blank_index > 100 %}高机会{% elif market_analysis.market_blank_index > 50 %}中等机会{% else %}低机会{% endif %}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">新品机会</div>
                <div class="metric-value">{{ new_products_count }}</div>
                <div class="metric-subtitle">近6个月新品</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">品牌集中度</div>
                <div class="metric-value">{{ market_analysis.brand_concentration.cr4 }}%</div>
                <div class="metric-subtitle">CR4 - {{ market_analysis.brand_concentration.concentration_level }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">平均价格</div>
                <div class="metric-value">${{ price_analysis.statistics.mean }}</div>
                <div class="metric-subtitle">中位数: ${{ price_analysis.statistics.median }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">平均评分</div>
                <div class="metric-value">{{ market_analysis.competition.average_rating }}</div>
                <div class="metric-subtitle">平均评论: {{ market_analysis.competition.average_reviews }}</div>
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
            {% if sellerspirit_data and sellerspirit_data.keyword_extensions %}
            <div class="insight-box">
                <div class="insight-title">🔍 关键词扩展建议</div>
                <p>基于卖家精灵数据分析，以下是相关的关键词扩展建议，可用于优化产品listing和广告投放：</p>
                <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 8px;">
                    {% for keyword in sellerspirit_data.keyword_extensions %}
                    <span class="badge badge-info">{{ keyword }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
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
                        <th style="padding: 10px; text-align: center;">平均评分</th>
                        <th style="padding: 10px; text-align: center;">平均评论数</th>
                        <th style="padding: 10px; text-align: center;">竞争强度</th>
                    </tr>
                </thead>
                <tbody>
                    {% for seg in segmentation_analysis.price_segments %}
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;"><strong>{{ seg.segment }}</strong></td>
                        <td style="padding: 10px; text-align: center;">{{ seg.product_count }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(seg.percentage) }}%</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(seg.avg_rating) }}</td>
                        <td style="padding: 10px; text-align: center;">{{ seg.avg_reviews }}</td>
                        <td style="padding: 10px; text-align: center;">
                            <span class="badge {% if seg.competition_level == '激烈' %}badge-danger{% elif seg.competition_level == '中等' %}badge-warning{% else %}badge-success{% endif %}">
                                {{ seg.competition_level }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <h3 style="margin: 20px 0 10px 0; color: #667eea;">品牌段分析</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f5f7fa; border-bottom: 2px solid #ddd;">
                        <th style="padding: 10px; text-align: left;">品牌段</th>
                        <th style="padding: 10px; text-align: center;">产品数</th>
                        <th style="padding: 10px; text-align: center;">占比</th>
                        <th style="padding: 10px; text-align: center;">平均价格</th>
                        <th style="padding: 10px; text-align: center;">平均评分</th>
                        <th style="padding: 10px; text-align: center;">市场机会</th>
                    </tr>
                </thead>
                <tbody>
                    {% for seg in segmentation_analysis.brand_segments %}
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;"><strong>{{ seg.segment }}</strong></td>
                        <td style="padding: 10px; text-align: center;">{{ seg.product_count }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(seg.percentage) }}%</td>
                        <td style="padding: 10px; text-align: center;">${{ "%.2f"|format(seg.avg_price) }}</td>
                        <td style="padding: 10px; text-align: center;">{{ "%.1f"|format(seg.avg_rating) }}</td>
                        <td style="padding: 10px; text-align: center;">
                            <span class="badge {% if seg.opportunity_level == '高' %}badge-success{% elif seg.opportunity_level == '中' %}badge-info{% else %}badge-warning{% endif %}">
                                {{ seg.opportunity_level }}
                            </span>
                        </td>
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
                    <div class="metric-label">新品增长率</div>
                    <div class="metric-value">{{ "%.1f"|format(trend_analysis.new_product_growth.growth_rate) }}%</div>
                    <div class="metric-subtitle">近期新品增长</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">市场成熟度</div>
                    <div class="metric-value">{{ trend_analysis.market_maturity.maturity_level }}</div>
                    <div class="metric-subtitle">{{ trend_analysis.market_maturity.maturity_score }}/100</div>
                </div>
            </div>
            <div class="insight-box">
                <div class="insight-title">趋势分析洞察</div>
                <p>
                    <strong>市场趋势：</strong>当前市场呈现<strong>{{ trend_analysis.market_trend.trend_direction }}</strong>趋势，
                    趋势强度为<strong>{{ trend_analysis.market_trend.trend_strength }}/100</strong>。
                    {% if trend_analysis.market_trend.trend_direction == '上升' %}
                    市场正在快速增长，是进入的好时机。
                    {% elif trend_analysis.market_trend.trend_direction == '稳定' %}
                    市场相对稳定，适合稳健经营。
                    {% else %}
                    市场可能面临挑战，需谨慎评估。
                    {% endif %}
                    <br><br>
                    <strong>新品动态：</strong>新品增长率为<strong>{{ "%.1f"|format(trend_analysis.new_product_growth.growth_rate) }}%</strong>，
                    {% if trend_analysis.new_product_growth.growth_rate > 20 %}
                    表明市场活跃度高，创新机会多。
                    {% elif trend_analysis.new_product_growth.growth_rate > 0 %}
                    市场保持一定活力。
                    {% else %}
                    新品进入速度放缓。
                    {% endif %}
                    <br><br>
                    <strong>市场成熟度：</strong>市场成熟度为<strong>{{ trend_analysis.market_maturity.maturity_level }}</strong>
                    （{{ trend_analysis.market_maturity.maturity_score }}/100），
                    {% if trend_analysis.market_maturity.maturity_level == '成熟期' %}
                    市场已经成熟，竞争充分，需要差异化策略。
                    {% elif trend_analysis.market_maturity.maturity_level == '成长期' %}
                    市场处于成长阶段，仍有较大发展空间。
                    {% else %}
                    市场处于早期阶段，机会与风险并存。
                    {% endif %}
                </p>
            </div>
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
