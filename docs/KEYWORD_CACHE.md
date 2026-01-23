# 关键词 CSV 缓存功能

为 scraperapi 抓取的关键词数据提供专门的 CSV 缓存机制，避免重复下载，节省成本和时间。

## 核心特性

- **自动缓存** - 首次抓取后自动保存到 CSV
- **自动加载** - 再次抓取时自动从缓存读取
- **零配置** - 默认启用，无需修改代码
- **命令行工具** - 完整的缓存管理工具
- **性能提升** - 速度提升 150+ 倍
- **成本节省** - 避免重复 API 调用

## 快速开始

### 基本使用（无需修改代码）

```python
from src.collectors.asin_collector import ASINCollector

collector = ASINCollector(api_key="your_api_key")

# 第一次：从网络抓取并自动保存到缓存
products = collector.collect_asins(keyword="camping tent")

# 第二次：自动从缓存加载，不消耗 API！
products = collector.collect_asins(keyword="camping tent")
```

### 禁用缓存获取最新数据

```python
# 强制从网络抓取最新数据
products = collector.collect_asins(
    keyword="camping tent",
    use_cache=False
)
```

## 命令行工具

```bash
# 列出所有缓存
python scripts/manage_keyword_cache.py list

# 查看统计信息
python scripts/manage_keyword_cache.py stats

# 查看详细信息
python scripts/manage_keyword_cache.py info "camping tent"

# 清理 7 天前的缓存
python scripts/manage_keyword_cache.py clean --days 7

# 清除指定关键词
python scripts/manage_keyword_cache.py clear --keyword "camping tent"

# 清除所有缓存
python scripts/manage_keyword_cache.py clear --all

# 导出缓存列表
python scripts/manage_keyword_cache.py export --output cache_list.csv
```

## 性能对比

| 操作 | 不使用缓存 | 使用缓存 | 提升 |
|------|-----------|---------|------|
| 抓取 100 个产品 | ~30 秒 | ~0.2 秒 | **150x** |
| API 调用次数 | 5-10 次 | 0 次 | **节省 100%** |
| 成本 | $0.05-0.10 | $0 | **节省 100%** |

## 缓存位置

```
data/keyword_cache/
├── cache_metadata.json          # 缓存元数据
├── camping_tent_us.csv          # 关键词缓存文件
├── hiking_backpack_us.csv
└── ...
```

## 使用场景

### 开发调试（推荐使用缓存）

```python
products = collector.collect_asins(
    keyword="camping tent",
    use_cache=True  # 默认就是 True
)
```

**优势**：
- 第一次抓取后，后续运行秒级完成
- 不消耗 API 配额
- 可以反复测试分析逻辑

### 获取最新数据（禁用缓存）

```python
products = collector.collect_asins(
    keyword="camping tent",
    use_cache=False
)
```

**适用于**：
- 生产环境每日更新
- 需要最新市场数据
- 数据变化频繁的场景

## 高级用法

### 自定义缓存目录

```python
collector = ASINCollector(
    api_key="your_api_key",
    cache_dir="custom/cache/dir"
)
```

### 直接使用缓存管理器

```python
from src.collectors.keyword_cache_manager import KeywordCacheManager

cache_manager = KeywordCacheManager()

# 检查缓存
if cache_manager.has_cache("camping tent", "us"):
    # 加载缓存
    results = cache_manager.load_from_cache("camping tent", "us")
    print(f"加载了 {len(results)} 条记录")

# 获取统计信息
stats = cache_manager.get_cache_statistics()
print(f"总缓存: {stats['total_keywords']} 个关键词")
print(f"总记录: {stats['total_records']} 条")
print(f"缓存大小: {stats['total_size_mb']:.2f} MB")
```

## CSV 文件格式

| 字段 | 说明 | 示例 |
|------|------|------|
| asin | 产品 ASIN | B08XYZ123 |
| name | 产品名称 | Camping Tent 4 Person |
| brand | 品牌 | Coleman |
| category | 类别 | Sports & Outdoors |
| price | 价格 | 89.99 |
| rating | 评分 | 4.5 |
| reviews_count | 评论数 | 1234 |
| sales_volume | 销量 | 500 |
| purchase_history_message | 购买历史 | 500+ bought in past month |
| page | 页码 | 1 |
| position | 位置 | 5 |
| url | 产品链接 | https://amazon.com/dp/... |
| image_url | 图片链接 | https://... |

## 常见问题

### Q: 缓存会自动更新吗？
A: 不会。缓存不会自动过期，需要手动清除或禁用缓存来获取最新数据。

### Q: 如何知道数据是从缓存加载的？
A: 查看日志输出，会显示 "✓ 发现缓存数据，正在加载..." 和 "✓ 从缓存加载成功"。

### Q: 缓存占用多少空间？
A: 每个关键词约 50-200 KB，取决于产品数量。使用 `stats` 命令查看总大小。

### Q: 可以禁用缓存吗？
A: 可以。设置 `use_cache=False` 即可。

### Q: 缓存文件可以手动编辑吗？
A: 可以。缓存是标准的 CSV 文件，可以用 Excel 或文本编辑器打开。

## 最佳实践

### 推荐做法

- 开发时启用缓存，加快迭代速度
- 定期清理过期缓存（每周）
- 生产环境根据需求决定是否使用缓存
- 使用命令行工具监控缓存情况

### 不推荐做法

- 长期不清理缓存
- 在需要最新数据时使用缓存
- 手动修改 `cache_metadata.json`
- 在多进程环境中并发写入同一缓存

## 文件结构

```
src/collectors/
├── keyword_cache_manager.py      # 缓存管理器
└── asin_collector.py             # 已集成缓存功能

scripts/
└── manage_keyword_cache.py       # 命令行管理工具

tests/
└── test_keyword_cache.py         # 单元测试

examples/
├── keyword_cache_examples.py     # 交互式示例
└── cache_demo.py                 # 完整演示
```

## 测试

```bash
# 运行单元测试
python -m pytest tests/test_keyword_cache.py -v

# 运行功能验证
python scripts/verify_keyword_cache.py
```
