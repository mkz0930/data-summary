# 蓝海产品分析器

蓝海产品分析器（BlueOceanAnalyzer）用于识别和评估亚马逊腰部蓝海产品机会，通过多维度的市场竞争分析和产品评分，帮助卖家发现低竞争、高潜力的产品机会。

## 腰部蓝海产品特征

真正赚钱的不是头部爆款（竞争惨烈、利润摊薄），而是"腰部蓝海"产品：

- **月销量**：800~4000件（腰部）
- **月搜索量**：3000~15000（有需求但不卷）
- **前10名平均Review数** < 800（最好 < 500）
- **前10名有3~5个评分** < 4.3星或Review数 < 150的listing
- **利润率**：30%~50%（甚至更高）
- **最好是轻小件**（FBA费用低）或自发货高利润产品

## 核心功能

### 1. 市场竞争指数计算

分析整个市场的竞争程度：

| 指标 | 权重 | 说明 |
|------|------|------|
| 评论密度指数 | 30% | 评论数越多，竞争越激烈 |
| 评分质量指数 | 25% | 高评分产品占比越高，竞争越激烈 |
| 品牌集中度 | 25% | 品牌越集中，竞争越激烈 |
| 价格竞争度 | 20% | 价格越集中，竞争越激烈 |

### 2. 蓝海产品识别标准

- **腰部销量**：月销量在50-500之间（可配置）
- **评论数适中**：评论数在20-500之间（可配置）
- **评分合格**：评分≥3.8（可配置）
- **竞争指数低**：产品竞争指数低于阈值（默认50）

### 3. 产品评分模型（0-100分）

#### 需求评分（Demand Score）
- 月搜索量（40%）
- 购买率（30%）
- 点击率（20%）
- 转化率（10%）

#### 竞争评分（Competition Score）
- 评论数相对指数（40%）
- 评分相对指数（30%）
- 垄断率（20%）
- CR4集中度（10%）

#### 壁垒评分（Barrier Score）
- 评论数壁垒（50%）：评论数越少，进入壁垒越低
- 评分壁垒（30%）：评分越低，改进空间越大
- 品牌壁垒（20%）：品牌集中度越低，壁垒越低

#### 利润评分（Profit Score）
- 价格水平（60%）：价格越高，利润空间越大
- 销量水平（40%）：销量适中最佳

#### 综合评分（Blue Ocean Score）
- 需求评分（30%）
- 竞争评分（30%）
- 壁垒评分（25%）
- 利润评分（15%）

### 4. 细分市场分析

按价格区间分类：
- 低价区（<$20）
- 中价区（$20-$50）
- 高价区（>$50）

每个价格区间统计：产品数量、平均评分、平均销量、平均竞争指数

### 5. 市场机会评估

| 机会等级 | 条件 | 建议 |
|---------|------|------|
| 高机会 | 蓝海占比>30% 且 竞争指数<40 | 适合进入 |
| 中等机会 | 蓝海占比>20% 且 竞争指数<60 | 需要仔细选品 |
| 低机会 | 蓝海占比>10% 且 竞争指数<80 | 需要差异化策略 |
| 无明显机会 | 其他情况 | 不建议进入 |

## 使用方法

### 基本使用

```python
from src.analyzers.blue_ocean_analyzer import BlueOceanAnalyzer
from src.database.models import Product, SellerSpiritData

# 创建分析器实例
analyzer = BlueOceanAnalyzer()

# 准备产品数据
products = [...]  # Product对象列表

# 准备卖家精灵数据（可选）
sellerspirit_data = SellerSpiritData(
    keyword="关键词",
    monthly_searches=10000,
    purchase_rate=0.15,
    click_rate=0.25,
    conversion_rate=0.12,
    monopoly_rate=0.30,
    cr4=0.45
)

# 执行分析
result = analyzer.analyze(products, sellerspirit_data)
```

### 自定义配置

```python
analyzer = BlueOceanAnalyzer(
    competition_threshold=50.0,    # 竞争指数阈值
    min_sales_volume=50,           # 最小月销量
    max_sales_volume=500,          # 最大月销量
    min_reviews=20,                # 最小评论数
    max_reviews=500,               # 最大评论数
    min_rating=3.8,                # 最小评分
    max_avg_reviews=300            # 市场平均评论数上限
)
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| competition_threshold | 50.0 | 竞争指数阈值，低于此值认为是蓝海 |
| min_sales_volume | 50 | 最小月销量（腰部产品下限） |
| max_sales_volume | 500 | 最大月销量（腰部产品上限） |
| min_reviews | 20 | 最小评论数 |
| max_reviews | 500 | 最大评论数（避免成熟市场） |
| min_rating | 3.8 | 最小评分要求 |
| max_avg_reviews | 300 | 市场平均评论数上限 |

## 输出结果结构

```python
{
    'market_competition': {
        'competition_index': 45.67,           # 市场竞争指数
        'review_density_score': 35.20,        # 评论密度得分
        'rating_quality_score': 78.50,        # 评分质量得分
        'brand_concentration': 25.30,         # 品牌集中度
        'price_competition_score': 60.40,     # 价格竞争度
        'avg_reviews': 150.5,                 # 平均评论数
        'avg_rating': 4.2,                    # 平均评分
    },
    'blue_ocean_products': [...],             # 蓝海产品列表
    'blue_ocean_count': 25,                   # 蓝海产品数量
    'blue_ocean_rate': 25.5,                  # 蓝海产品占比（%）
    'segments': [...],                        # 细分市场分析
    'opportunity_assessment': {               # 市场机会评估
        'opportunity_level': 'high',
        'opportunity_desc': '高机会市场',
        'recommendations': [...]
    },
    'top_opportunities': [...]                # 前10个最佳机会
}
```

## 选品分析维度

### 1. 需求维度（有没有人买？）

- **月搜索量**：3000~15000（最佳5000~10000）
- **月销量总和**（Top 10总销量）：8000~25000件
- **趋势指标**：Google Trends过去12个月稳定或上升

### 2. 竞争维度（打不打得过？）

黄金筛选条件（同时满足3条以上极佳）：
- 前10名平均Review数 ≤ 600（最好 ≤ 400）
- 前10名至少有4~5个Review < 200的listing
- 前10名有3个以上评分 ≤ 4.4星
- 前10名有2~3个图片极差、主图违规、标题乱写的

### 3. 利润维度（能不能赚到钱？）

黄金标准：
- 利润率 ≥ 35%（轻小件）/ ≥ 45%（自发货或中大件）
- 利润额 ≥ $8（轻小件）/ ≥ $15（中大件）
- PPC建议出价 < $1.5（最好 < $1.0）

### 4. 季节性判断（会不会突然死？）

- 避免强季节性产品
- 优先常青款 + 微趋势
- Keepa价格轨迹过去1年价格波动 ≤ 30%

### 5. 差异化空间

问自己5个问题（至少满足2个）：
1. 我能把主图做得比前10名好3倍吗？
2. 我能做A+ Content把转化率做到15%+吗？
3. 我有独家供应链能做出别人没有的功能吗？
4. 我能做捆绑销售把客单价提升30%吗？
5. 我能做站外流量把销量做起来吗？

## 集成配置

在 `config.json` 中启用蓝海分析：

```json
{
    "analysis": {
        "enable_blue_ocean": true
    }
}
```

## 测试

```bash
python tests/test_blue_ocean_analyzer.py
```
