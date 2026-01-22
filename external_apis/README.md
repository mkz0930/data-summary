# External APIs

本目录包含从其他项目复用的API模块。

## 📁 文件说明

### 1. amazon_scraper.py (33KB)
- **来源**: `D:\Product\api\scraperAPI\src\amazon_scraper.py`
- **功能**: 亚马逊产品搜索和详情抓取
- **使用**: 被 `src/collectors/asin_collector.py` 调用
- **依赖**: ScraperAPI密钥

**主要功能**:
- 关键词搜索产品
- 获取产品详情（价格、评分、评论数等）
- 智能销量阈值停止
- 并发请求优化
- 自动重试机制

### 2. sellerspirit_main.py (14KB)
- **来源**: `D:\Product\plugin\sellerspirit\main.py`
- **功能**: 卖家精灵数据抓取（月搜索量、CR4等）
- **使用**: 被 `src/collectors/sellerspirit_collector.py` 调用
- **依赖**: Chrome浏览器 + 卖家精灵扩展

**主要功能**:
- 使用Puppeteer控制Chrome
- 自动登录Amazon
- 抓取关键词数据
- 导出Excel文件

### 3. product_classifier.py (8.5KB)
- **来源**: `D:\Product\agent_class\product_classifier.py`
- **功能**: AI驱动的产品分类验证
- **使用**: 参考实现，已集成到 `src/validators/category_validator.py`
- **依赖**: Anthropic API密钥

**主要功能**:
- 使用Claude API验证产品分类
- 批量处理产品
- 生成验证报告

## 🔗 依赖关系

```
项目结构:
D:\Product\data_summary\
├── external_apis/              # 外部API模块
│   ├── amazon_scraper.py       # ✅ 已复制
│   ├── sellerspirit_main.py    # ✅ 已复制
│   └── product_classifier.py   # ✅ 已复制
│
├── src/
│   ├── collectors/
│   │   ├── asin_collector.py   # 调用 amazon_scraper.py
│   │   └── sellerspirit_collector.py  # 调用 sellerspirit_main.py
│   └── validators/
│       └── category_validator.py  # 参考 product_classifier.py
```

## ⚙️ 配置要求

### 1. API密钥配置 (config/.env)
```bash
# ScraperAPI密钥（用于amazon_scraper.py）
SCRAPERAPI_KEY=your_scraperapi_key_here

# Anthropic API密钥（用于category_validator.py）
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Apify API令牌（可选）
APIFY_API_TOKEN=your_apify_token_here
```

### 2. 卖家精灵要求
- Chrome浏览器
- 卖家精灵扩展已安装
- Amazon账号已登录

## 📝 使用示例

### 使用amazon_scraper.py
```python
from external_apis.amazon_scraper import AmazonScraper

scraper = AmazonScraper(api_key="your_key")
products = scraper.search_products(keyword="camping", max_pages=10)
```

### 使用sellerspirit_main.py
```python
import subprocess

result = subprocess.run(
    ["python", "external_apis/sellerspirit_main.py", "camping"],
    capture_output=True
)
```

### 参考product_classifier.py
```python
# 已集成到 src/validators/category_validator.py
from src.validators.category_validator import CategoryValidator

validator = CategoryValidator(api_key="your_key")
validations = validator.validate_batch(products, keyword)
```

## ✅ 复制完成

所有必需的外部API文件已成功复制到项目中：
- ✅ amazon_scraper.py (33KB)
- ✅ sellerspirit_main.py (14KB)
- ✅ product_classifier.py (8.5KB)

项目现在可以独立运行，无需依赖外部项目路径！
