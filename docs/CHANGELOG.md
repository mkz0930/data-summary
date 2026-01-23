# 变更日志

## [未发布] - 2026-01-23

### 新增功能
- **统一数据缓存管理器 (UnifiedDataCache)**
  - 新增 `src/collectors/unified_data_cache.py`
  - 将4种数据源缓存统一到主数据库 `raw_data_cache` 表
  - 支持的数据源：sellerspirit、apify_api、scraper_search、scraper_product
  - 通过 `(source, key_type, key_value)` 三元组唯一标识缓存
  - 各数据源独立TTL配置（卖家精灵7天，其他24小时）
  - 批量操作支持（get_batch、set_batch、get_missing_keys）
  - 缓存统计信息（命中次数、条目数、过期清理）

- **缓存适配器 (CacheAdapter)**
  - 新增 `src/collectors/cache_adapter.py`
  - 为采集器提供便捷的缓存接口
  - 向后兼容现有代码

### 架构改进
- **采集器集成统一缓存**
  - `SellerSpiritCollector` - 优先检查统一缓存，解析后自动保存
  - `ASINCollector` - 统一缓存优先，保留CSV缓存向后兼容
  - `PriceCollector` - 批量获取时先查缓存，减少API调用

### 数据库变更
- 新增 `raw_data_cache` 表
  - `source` - 数据源标识
  - `key_type` - 键类型（keyword/asin）
  - `key_value` - 键值
  - `data_json` - JSON格式原始数据
  - `data_hash` - 数据哈希（检测变化）
  - `ttl_hours` - 缓存有效期
  - `expires_at` - 过期时间
  - `hit_count` - 命中次数统计

---

## [未发布] - 2026-01-22

### 架构重构
- **分析器模块重构**
  - 所有分析器继承 `BaseAnalyzer` 基类
  - 统一日志记录方法 (`log_info`, `log_warning`, `log_error`)
  - 复用基类统计计算、分数归一化、等级评定等方法
  - 重构的分析器：
    - `MarketAnalyzer` - 新增市场成熟度、进入难度、健康度指数
    - `BlueOceanAnalyzer` - 继承基类，保持原有功能
    - `KeywordAnalyzer` - 继承基类，兼容基类接口
    - `LifecycleAnalyzer` - 继承基类
    - `SegmentationAnalyzer` - 继承基类
    - `ScoringSystem` - 继承基类，实现 analyze 方法
    - `SeasonalityAnalyzer` - 继承基类
    - `AdvertisingAnalyzer` - 继承基类

- **收集器基类 (BaseCollector)**
  - 新增 `src/collectors/base_collector.py`
  - 统一重试机制（指数退避、线性退避、固定间隔）
  - 断路器模式防止服务雪崩
  - 速率限制器（令牌桶算法）
  - 批量处理支持（同步/异步）
  - 收集器统计信息

- **统一缓存管理器 (CacheManager)**
  - 新增 `src/collectors/cache_manager.py`
  - 内存缓存（LRU 淘汰策略）
  - 文件缓存（持久化存储）
  - TTL 过期机制
  - 缓存命中率统计
  - 缓存装饰器支持

### 新增功能
- **MarketAnalyzer 新增分析维度**
  - `_analyze_market_maturity()` - 市场成熟度评估（新兴/成长/成熟/饱和）
  - `_calculate_entry_difficulty()` - 进入难度评分（竞争/品牌壁垒/资金/运营）
  - `_calculate_market_health_index()` - 市场健康度指数

- **日志系统增强**
  - 结构化日志支持（JSON 格式）
  - 性能追踪上下文管理器 `track_performance()`
  - API 调用日志 `log_api_call()`
  - 性能摘要统计 `get_performance_summary()`
  - 性能追踪装饰器 `@performance_tracker`

### 新增
- **Apify API 集成**
  - 支持高并发数据采集（25并发）
  - 智能重试机制（指数退避策略）
  - SQLite 本地缓存
  - Amazon 专用封装类

- **关键词缓存功能**
  - 自动缓存 scraperapi 抓取的关键词数据
  - 命令行缓存管理工具
  - 性能提升 150+ 倍

- **蓝海产品分析器**
  - 市场竞争指数计算
  - 蓝海产品识别（腰部销量、评论数适中）
  - 产品评分模型（需求、竞争、壁垒、利润）
  - 细分市场分析
  - 市场机会评估

- **自动跳过已验证ASIN**
  - 避免重复调用API
  - 支持中断续传
  - 增量验证新产品

- **HTML报告增强**
  - 卖家精灵关键指标展示（购买率、点击率、转化率、垄断率）
  - 关键词扩展列表展示区块

### 增强
- **竞争对手分析器 (CompetitorAnalyzer)**
  - 集成卖家精灵CR4数据分析市场集中度
  - 优先使用卖家精灵提供的CR4数据

- **市场细分分析器 (SegmentationAnalyzer)**
  - 新增关键词细分功能
  - 按搜索量将关键词分为高、中、低三个层级
  - 识别高潜力关键词和利基关键词

- **趋势预测分析器 (TrendAnalyzer)**
  - 集成购买率和转化率指标
  - 基于购买率和转化率生成针对性建议

- **验证器性能优化**
  - Gemini验证器：最大并发数提升至1000，处理速度提升20-50倍
  - Claude验证器：最大并发数提升至50，处理速度提升5-10倍

### 修复
- 确保卖家精灵数据在各分析器之间正确传递
- 修复orchestrator中分析器调用时缺少sellerspirit_data参数的问题

### 技术改进
- 所有新增分析器功能均通过单元测试验证
- 改进了数据流程的完整性和一致性
- 日志系统双重输出（控制台简洁模式 + 文件详细模式）

## [0.1.0] - 2026-01-21

### 初始版本
- 基础数据收集功能（ASIN抓取、价格数据、卖家精灵数据）
- AI智能分类校验（Claude + Gemini双模型）
- 市场分析功能（市场规模、竞争强度、价格分布）
- 产品生命周期分析（新品机会挖掘、趋势识别）
- HTML报告生成功能
- SQLite数据库存储
