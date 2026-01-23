# 系统架构文档

## 数据流程

```
关键词输入 → API抓取ASIN → 卖家精灵补充数据 → AI分类校验 → 数据清洗整合 → 分析计算 → 生成HTML报告
```

## 项目结构

```
data_summary/
├── config/
│   └── config.json              # 配置文件
├── data/
│   ├── database/                # SQLite数据库
│   ├── cache/                   # 统一缓存目录
│   ├── keyword_cache/           # 关键词缓存
│   └── raw/                     # 原始数据
├── docs/                        # 文档目录
├── examples/                    # 示例代码
├── logs/                        # 日志文件
├── outputs/                     # 输出目录
├── scripts/                     # 工具脚本
├── src/
│   ├── analyzers/               # 分析器模块
│   │   ├── base_analyzer.py     # 分析器基类 ★
│   │   ├── advertising_analyzer.py
│   │   ├── blue_ocean_analyzer.py
│   │   ├── competitor_analyzer.py
│   │   ├── keyword_analyzer.py
│   │   ├── lifecycle_analyzer.py
│   │   ├── market_analyzer.py
│   │   ├── scoring_system.py
│   │   ├── seasonality_analyzer.py
│   │   ├── segmentation_analyzer.py
│   │   └── trend_analyzer.py
│   ├── collectors/              # 数据采集模块
│   │   ├── base_collector.py    # 收集器基类 ★
│   │   ├── cache_manager.py     # 统一缓存管理器 ★
│   │   ├── asin_collector.py
│   │   ├── keyword_cache_manager.py
│   │   ├── price_collector.py
│   │   └── sellerspirit_collector.py
│   ├── core/                    # 核心模块
│   │   ├── config_manager.py
│   │   └── orchestrator.py
│   ├── database/                # 数据库模块
│   │   ├── db_manager.py
│   │   └── models.py
│   ├── reporters/               # 报告生成模块
│   │   ├── chart_builder.py
│   │   ├── csv_exporter.py
│   │   └── html_generator.py
│   ├── utils/                   # 工具模块
│   │   ├── logger.py            # 增强日志系统 ★
│   │   ├── progress.py
│   │   └── retry.py
│   └── validators/              # 验证器模块
│       ├── category_validator.py
│       ├── data_quality_checker.py
│       ├── gemini_validator.py
│       └── model_comparator.py
├── tests/                       # 测试文件
├── external_apis/               # 外部API集成
└── main.py                      # 主入口

★ 标记为本次新增或重大更新的文件
```

## 输出目录结构

每次分析任务都会在 `outputs/` 目录下创建一个独立的任务目录：

```
outputs/
└── {keyword}/                          # 关键词目录
    └── {timestamp}/                    # 任务时间戳目录
        ├── exports/                    # CSV导出文件目录
        │   ├── products_{timestamp}.csv
        │   ├── new_products_{timestamp}.csv
        │   ├── analysis_summary_{timestamp}.csv
        │   ├── brand_ranking_{timestamp}.csv
        │   ├── keyword_opportunities_{timestamp}.csv
        │   ├── price_distribution_{timestamp}.csv
        │   ├── validation_gemini_{timestamp}.csv
        │   └── model_disagreements_{keyword}_{timestamp}.csv
        └── reports/                    # HTML报告目录
            └── report_{timestamp}.html
```

### 示例

对于关键词 "camping tent"，在 2024-01-22 12:00:00 执行的分析任务：

```
outputs/
└── camping_tent/
    └── 20240122_120000/
        ├── exports/
        │   ├── products_20240122_120000.csv
        │   ├── new_products_20240122_120000.csv
        │   └── ...
        └── reports/
            └── report_20240122_120000.html
```

### 文件说明

**CSV导出文件 (exports/)**：
- `products_{timestamp}.csv` - 所有产品的详细信息
- `new_products_{timestamp}.csv` - 新产品列表
- `analysis_summary_{timestamp}.csv` - 分析摘要统计
- `brand_ranking_{timestamp}.csv` - 品牌排名数据
- `keyword_opportunities_{timestamp}.csv` - 关键词机会分析
- `price_distribution_{timestamp}.csv` - 价格分布数据
- `validation_gemini_{timestamp}.csv` - Gemini AI分类校验结果
- `model_disagreements_{keyword}_{timestamp}.csv` - Claude和Gemini模型结果对比

**HTML报告 (reports/)**：
- `report_{timestamp}.html` - 完整的分析报告

## 代码中获取路径

```python
from src.core.config_manager import ConfigManager

config = ConfigManager()
keyword = "camping tent"
timestamp = "20240122_120000"

# 获取任务输出目录
task_output_dir = config.get_task_output_dir(keyword, timestamp)

# 获取CSV导出目录
task_exports_dir = config.get_task_exports_dir(keyword, timestamp)

# 获取HTML报告目录
task_reports_dir = config.get_task_reports_dir(keyword, timestamp)
```

## 核心模块说明

### ConfigManager
配置管理器，负责加载和管理所有配置项。

### Orchestrator
流程编排器，协调各模块的执行顺序和数据传递。

### DatabaseManager
数据库管理器，负责数据的持久化存储和查询。

### 分析器模块

所有分析器继承自 `BaseAnalyzer` 基类，提供统一的接口和公共方法。

#### BaseAnalyzer 基类
提供所有分析器共用的功能：
- 统计计算 (`calculate_statistics`, `calculate_percentile`)
- 分数归一化 (`normalize_score`, `normalize_score_log`, `normalize_score_sigmoid`)
- 等级评定 (`grade_score`, `grade_score_with_desc`)
- 异常值过滤 (`filter_outliers_iqr`, `filter_outliers_zscore`)
- 安全计算 (`safe_divide`, `safe_percentage`)
- 数据提取 (`extract_values`, `extract_numeric_values`)
- 分组分析 (`group_by_range`, `group_products_by_attribute`)
- 日志方法 (`log_info`, `log_warning`, `log_error`, `log_debug`)

#### 分析器列表
- **MarketAnalyzer**: 市场整体分析
  - 市场规模、竞争强度、品牌集中度
  - 新增：市场成熟度、进入难度、健康度指数
- **KeywordAnalyzer**: 关键词分析
- **CompetitorAnalyzer**: 竞品对标分析
- **SegmentationAnalyzer**: 市场细分分析
- **TrendAnalyzer**: 趋势预测分析
- **ScoringSystem**: 综合评分系统
- **BlueOceanAnalyzer**: 蓝海产品分析
- **LifecycleAnalyzer**: 产品生命周期分析
- **SeasonalityAnalyzer**: 季节性分析
- **AdvertisingAnalyzer**: 广告成本分析

### 收集器模块

#### BaseCollector 基类
提供所有收集器共用的功能：
- 重试机制（指数退避、线性退避、固定间隔）
- 断路器模式（防止服务雪崩）
- 速率限制器（令牌桶算法）
- 批量处理（同步/异步）
- 统计信息收集

#### 收集器列表
- **ASINCollector**: ASIN 数据采集
- **PriceCollector**: 价格数据采集
- **SellerSpiritCollector**: 卖家精灵数据采集
- **KeywordCacheManager**: 关键词缓存管理

#### CacheManager 统一缓存
- 内存缓存（LRU 淘汰）
- 文件缓存（持久化）
- TTL 过期机制
- 缓存装饰器

### 验证器模块
- **CategoryValidator**: Claude AI 分类验证
- **GeminiValidator**: Gemini AI 分类验证

### 日志系统

增强的日志系统提供：
- 控制台输出（简洁模式）
- 文件输出（详细模式 + 日志轮转）
- JSON 结构化日志（可选）
- 性能追踪
  - `track_performance()` 上下文管理器
  - `log_api_call()` API 调用日志
  - `get_performance_summary()` 性能摘要
  - `@performance_tracker` 装饰器

## 类继承关系

```
BaseAnalyzer (ABC)
├── MarketAnalyzer
├── BlueOceanAnalyzer
├── KeywordAnalyzer
├── LifecycleAnalyzer
├── SegmentationAnalyzer
├── ScoringSystem
├── SeasonalityAnalyzer
├── AdvertisingAnalyzer
├── CompetitorAnalyzer
└── TrendAnalyzer

BaseCollector (ABC)
├── ASINCollector (待重构)
├── PriceCollector (待重构)
└── SellerSpiritCollector (待重构)
```
