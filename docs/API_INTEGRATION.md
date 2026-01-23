# Apify API 集成文档

## 概述

本项目已集成 Apify API，支持高并发数据采集、智能重试、速率限制和本地缓存功能。

## 配置说明

### 1. API Token 配置

在 `.env` 文件中添加你的 Apify API Token：

```bash
APIFY_API_TOKEN=your_apify_api_token_here
```

### 2. 并发配置

在 `config/config.json` 中已配置以下参数：

```json
{
  "apify_max_concurrent": 25,           // 最大并发数（根据你的账户限制）
  "apify_rate_limit_delay": 0.1,        // API 调用间隔（秒）
  "apify_max_retries": 5,               // 最大重试次数
  "apify_retry_backoff_base": 2.0,      // 重试基础延迟（秒）
  "apify_retry_backoff_max": 60.0       // 重试最大延迟（秒）
}
```

**重要提示**：
- 你的账户支持 **25 个并发**，已配置为 `apify_max_concurrent: 25`
- 如果需要调整并发数，请修改 `config.json` 中的 `apify_max_concurrent` 值
- 建议保持 `rate_limit_delay` 为 0.1 秒，避免触发速率限制

## 核心功能

### 1. ApifyScraper（通用封装类）

支持运行任何 Apify Actor，提供以下功能：

- ✅ **异步并发执行**：支持自定义并发数（默认 25）
- ✅ **智能重试机制**：指数退避策略，自动处理 429/500/502/503/504 错误
- ✅ **速率限制**：避免超出 API 配额
- ✅ **本地缓存**：SQLite 数据库缓存，避免重复调用
- ✅ **批量任务管理**：支持批量运行 Actor 并跟踪进度

### 2. ApifyAmazonScraper（Amazon 专用封装）

专门用于 Amazon 产品数据采集：

- 根据 ASIN 批量抓取产品详情
- 搜索产品并获取结果
- 自动处理 Amazon 特定的数据格式

## 使用示例

### 示例 1：基础使用 - 运行单个 Actor

```python
from external_apis.apify_scraper import ApifyScraper
from src.core.config_manager import ConfigManager

# 初始化配置
config = ConfigManager()

# 创建 Scraper 实例
scraper = ApifyScraper(
    api_token=config.apify_api_token,
    max_concurrent=config.apify_max_concurrent,
    rate_limit_delay=config.apify_rate_limit_delay,
)

# 运行 Web Scraper
result = scraper.run_actor(
    actor_id="apify/web-scraper",
    input_data={
        "startUrls": [{"url": "https://www.example.com"}],
        "maxRequestsPerCrawl": 1,
    },
    use_cache=True,
)

print(result)
```

### 示例 2：Amazon 产品搜索

```python
from external_apis.apify_scraper import ApifyAmazonScraper
from src.core.config_manager import ConfigManager

# 初始化配置
config = ConfigManager()

# 创建 Amazon Scraper
amazon_scraper = ApifyAmazonScraper(
    api_token=config.apify_api_token,
    max_concurrent=config.apify_max_concurrent,
)

# 搜索产品
result = amazon_scraper.search_products(
    keyword="camping tent",
    country_code="us",
    max_results=20,
    use_cache=True,
)

if result and 'items' in result:
    for item in result['items']:
        print(f"ASIN: {item['asin']}, 标题: {item['title']}, 价格: ${item['price']}")
```

### 示例 3：批量抓取产品详情（并发 25 个）

```python
from external_apis.apify_scraper import ApifyAmazonScraper
from src.core.config_manager import ConfigManager

# 初始化配置
config = ConfigManager()

# 创建 Amazon Scraper
amazon_scraper = ApifyAmazonScraper(
    api_token=config.apify_api_token,
    max_concurrent=25,  # 使用你的账户最大并发数
)

# ASIN 列表
asins = ["B0D2KF98MC", "B08L5VPX9C", "B07QXMNF1F", "B08BHXG144", "B09JQVYZD1"]

# 批量抓取（并发执行）
results = amazon_scraper.scrape_products_by_asins(
    asins=asins,
    country_code="us",
    use_cache=True,
    show_progress=True,
)

# 处理结果
for asin, result in zip(asins, results):
    if result and 'items' in result:
        item = result['items'][0]
        print(f"ASIN: {asin}, 标题: {item['title']}")
```

### 示例 4：与项目数据库集成

```python
from external_apis.apify_scraper import ApifyAmazonScraper
from src.core.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager

# 初始化
config = ConfigManager()
db_manager = DatabaseManager(config)

# 从数据库读取 ASIN
asins = db_manager.get_all_asins(limit=100)

# 批量抓取
amazon_scraper = ApifyAmazonScraper(
    api_token=config.apify_api_token,
    max_concurrent=25,
)

results = amazon_scraper.scrape_products_by_asins(
    asins=asins,
    country_code="us",
    use_cache=True,
    show_progress=True,
)

# 保存结果到数据库或进行进一步处理
for asin, result in zip(asins, results):
    if result:
        # 处理结果...
        pass
```

## 支持的 Apify Actors

### 1. Amazon Product Scraper
- **Actor ID**: `apify/amazon-product-scraper`
- **功能**: 抓取 Amazon 产品详情、搜索结果
- **使用**: `ApifyAmazonScraper` 类

### 2. Web Scraper
- **Actor ID**: `apify/web-scraper`
- **功能**: 通用网页抓取
- **使用**: `ApifyScraper` 类

### 3. Google Search Scraper
- **Actor ID**: `apify/google-search-scraper`
- **功能**: Google 搜索结果抓取
- **使用**: `ApifyScraper` 类

### 4. 自定义 Actors
- 支持运行任何 Apify Actor
- 使用 `ApifyScraper.run_actor()` 方法

## 缓存机制

### 缓存数据库

- **位置**: `data/apify_results.db`
- **表结构**: `apify_runs` 表存储所有运行记录
- **缓存策略**: 基于 Actor ID 和输入参数的 MD5 哈希

### 缓存管理

```python
from external_apis.apify_scraper import ApifyScraper
import sqlite3

scraper = ApifyScraper(api_token="your_token")

# 查看缓存统计
with sqlite3.connect(scraper.db_path) as conn:
    total = conn.execute("SELECT COUNT(*) FROM apify_runs").fetchone()[0]
    success = conn.execute(
        "SELECT COUNT(*) FROM apify_runs WHERE status = 'SUCCEEDED'"
    ).fetchone()[0]

    print(f"总记录: {total}, 成功: {success}")

# 清空缓存（如需要）
with sqlite3.connect(scraper.db_path) as conn:
    conn.execute("DELETE FROM apify_runs")
```

## 性能优化建议

### 1. 并发数优化

根据你的账户类型调整并发数：

| 账户类型 | 建议并发数 | 配置值 |
|---------|-----------|--------|
| 免费账户 | 1-2 | `apify_max_concurrent: 2` |
| 个人套餐 | 5-10 | `apify_max_concurrent: 10` |
| 团队套餐 | 20-25 | `apify_max_concurrent: 25` |
| 企业套餐 | 50+ | `apify_max_concurrent: 50` |

**你的配置**: 25 个并发（已配置）

### 2. 速率限制

- 默认延迟：0.1 秒
- 如果遇到 429 错误，增加 `apify_rate_limit_delay` 值
- 建议范围：0.05 - 0.5 秒

### 3. 重试策略

- 最大重试次数：5 次（已配置）
- 指数退避：2^n 秒（n 为重试次数）
- 最大延迟：60 秒

### 4. 缓存使用

- 开发/测试阶段：`use_cache=True`（避免重复调用）
- 生产环境：根据数据新鲜度要求决定
- 定期清理过期缓存

## 错误处理

### 常见错误及解决方案

| 错误代码 | 说明 | 解决方案 |
|---------|------|---------|
| 401 | API Token 无效 | 检查 `.env` 中的 `APIFY_API_TOKEN` |
| 429 | 超出速率限制 | 增加 `apify_rate_limit_delay` 或减少 `apify_max_concurrent` |
| 500/502/503 | 服务器错误 | 自动重试（已配置） |
| 504 | 超时 | 增加 `request_timeout` 参数 |

### 日志记录

所有 API 调用都会记录日志：

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 运行 Scraper（会自动输出日志）
scraper.run_actor(...)
```

## 运行示例代码

```bash
# 运行使用示例
python external_apis/apify_usage_example.py
```

示例代码包含：
1. 基础使用
2. Amazon 产品搜索
3. 批量抓取（并发 25 个）
4. 自定义 Actor
5. 缓存管理
6. 与项目数据库集成

## API 参考

### ApifyScraper 类

```python
class ApifyScraper:
    def __init__(
        self,
        api_token: str,                    # Apify API Token
        db_path: str = "data/apify_results.db",  # 缓存数据库路径
        max_concurrent: int = 25,          # 最大并发数
        rate_limit_delay: float = 0.1,     # API 调用间隔（秒）
        request_timeout: int = 300,        # 请求超时时间（秒）
        max_retries: int = 5,              # 最大重试次数
        retry_backoff_base: float = 2.0,   # 重试基础延迟
        retry_backoff_max: float = 60.0,   # 重试最大延迟
    )

    def run_actor(
        self,
        actor_id: str,                     # Actor ID
        input_data: Dict[str, Any],        # 输入参数
        use_cache: bool = True,            # 是否使用缓存
        wait_for_finish: bool = True,      # 是否等待完成
        timeout: int = 300,                # 超时时间（秒）
    ) -> Optional[Dict[str, Any]]

    def run_actors_batch(
        self,
        actor_id: str,                     # Actor ID
        input_list: List[Dict[str, Any]],  # 输入参数列表
        use_cache: bool = True,            # 是否使用缓存
        show_progress: bool = True,        # 是否显示进度
    ) -> List[Optional[Dict[str, Any]]]
```

### ApifyAmazonScraper 类

```python
class ApifyAmazonScraper(ApifyScraper):
    def scrape_products_by_asins(
        self,
        asins: List[str],                  # ASIN 列表
        country_code: str = 'us',          # 国家代码
        use_cache: bool = True,            # 是否使用缓存
        show_progress: bool = True,        # 是否显示进度
    ) -> List[Optional[Dict[str, Any]]]

    def search_products(
        self,
        keyword: str,                      # 搜索关键词
        country_code: str = 'us',          # 国家代码
        max_results: int = 100,            # 最大结果数
        use_cache: bool = True,            # 是否使用缓存
    ) -> Optional[Dict[str, Any]]
```

## 最佳实践

1. **使用缓存**：开发阶段始终启用缓存，避免重复调用
2. **批量处理**：使用 `run_actors_batch()` 进行批量操作，充分利用并发
3. **错误处理**：检查返回值是否为 `None`，处理失败情况
4. **日志监控**：启用日志记录，监控 API 调用状态
5. **配额管理**：定期检查 Apify 控制台的配额使用情况

## 与现有代码对比

### ScraperAPI vs Apify API

| 特性 | ScraperAPI | Apify API |
|-----|-----------|-----------|
| 并发数 | 20 | 25 |
| 重试机制 | 基础 | 智能指数退避 |
| 缓存 | 无 | SQLite 本地缓存 |
| Actor 支持 | 无 | 支持所有 Apify Actors |
| 批量处理 | 手动实现 | 内置批量方法 |

## 常见问题

### Q1: 如何查看我的 Apify 账户并发限制？

登录 [Apify Console](https://console.apify.com/)，查看 Account > Limits。

### Q2: 如何清空缓存？

```python
import sqlite3
with sqlite3.connect("data/apify_results.db") as conn:
    conn.execute("DELETE FROM apify_runs")
```

### Q3: 如何处理超时？

增加 `request_timeout` 参数：

```python
scraper = ApifyScraper(
    api_token=token,
    request_timeout=600,  # 10 分钟
)
```

### Q4: 如何监控 API 使用情况？

查看日志输出或访问 [Apify Console](https://console.apify.com/) 查看使用统计。

## 相关文件

- **核心实现**: [external_apis/apify_scraper.py](external_apis/apify_scraper.py)
- **使用示例**: [external_apis/apify_usage_example.py](external_apis/apify_usage_example.py)
- **配置文件**: [config/config.json](config/config.json)
- **配置管理**: [src/core/config_manager.py](src/core/config_manager.py)

## 更新日志

### 2026-01-22
- ✅ 集成 Apify API
- ✅ 配置并发数为 25（根据账户限制）
- ✅ 实现智能重试和速率限制
- ✅ 添加 SQLite 本地缓存
- ✅ 创建 Amazon 专用封装类
- ✅ 提供完整使用示例和文档
