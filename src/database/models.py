"""
数据模型定义
定义数据库表结构和数据类

数据库架构说明：
================

1. 主数据库: data/database/analysis.db
   - products: 产品基础信息表（核心表）
   - category_validations: AI分类验证结果表
   - sellerspirit_data: 卖家精灵市场数据表
   - analysis_results: 分析结果汇总表
   - model_comparisons: AI模型对比结果表

2. 外部API缓存数据库:
   - data/scraper_results.db: ScraperAPI 抓取缓存（amazon_scraper.py 使用）
   - data/apify_results.db: Apify API 运行缓存（apify_scraper.py 使用）

数据流向：
=========
关键词输入 → ScraperAPI/Apify抓取ASIN → products表
         → 卖家精灵补充数据 → sellerspirit_data表
         → AI分类验证 → category_validations表
         → 数据分析 → analysis_results表
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Product:
    """
    产品数据模型

    存储Amazon产品的基础信息和蓝海评分数据
    主键: asin (Amazon标准识别号)
    """
    # === 基础信息 ===
    asin: str                                      # Amazon标准识别号（主键）
    name: str                                      # 产品名称
    brand: Optional[str] = None                    # 品牌名称
    category: Optional[str] = None                 # 产品类目
    price: Optional[float] = None                  # 售价（美元）
    rating: Optional[float] = None                 # 评分（1-5星）
    reviews_count: Optional[int] = None            # 评论数量
    sales_volume: Optional[int] = None             # 月销量估算
    bsr_rank: Optional[int] = None                 # BSR排名（Best Sellers Rank）
    available_date: Optional[str] = None           # 上架日期
    feature_bullets: Optional[str] = None          # 产品卖点（JSON格式）
    has_anomaly: bool = False                      # 是否存在数据异常
    created_at: Optional[str] = None               # 记录创建时间

    # === 蓝海评分（0-100分，越高越好）===
    blue_ocean_score: Optional[float] = None       # 蓝海综合评分
    demand_score: Optional[float] = None           # 需求评分（搜索量、销量）
    competition_score: Optional[float] = None      # 竞争评分（竞品数量、集中度）
    barrier_score: Optional[float] = None          # 进入壁垒评分（资金、技术门槛）
    profit_score: Optional[float] = None           # 利润评分（毛利率、利润额）

    # === 腰部蓝海分析字段 ===
    listing_quality_score: Optional[float] = None  # Listing质量分（0-100，评估图片、标题、描述）
    is_weak_listing: Optional[bool] = None         # 是否为弱listing（可超越的竞品）
    estimated_cost: Optional[float] = None         # 预估采购成本（美元）
    gross_margin: Optional[float] = None           # 毛利率（0-1）
    profit_amount: Optional[float] = None          # 单件利润额（美元）
    weight_lb: Optional[float] = None              # 产品重量（磅，用于计算FBA费用）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'asin': self.asin,
            'name': self.name,
            'brand': self.brand,
            'category': self.category,
            'price': self.price,
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'sales_volume': self.sales_volume,
            'bsr_rank': self.bsr_rank,
            'available_date': self.available_date,
            'feature_bullets': self.feature_bullets,
            'has_anomaly': self.has_anomaly,
            'created_at': self.created_at or datetime.now().isoformat(),
            'blue_ocean_score': self.blue_ocean_score,
            'demand_score': self.demand_score,
            'competition_score': self.competition_score,
            'barrier_score': self.barrier_score,
            'profit_score': self.profit_score,
            'listing_quality_score': self.listing_quality_score,
            'is_weak_listing': self.is_weak_listing,
            'estimated_cost': self.estimated_cost,
            'gross_margin': self.gross_margin,
            'profit_amount': self.profit_amount,
            'weight_lb': self.weight_lb
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """从字典创建实例"""
        return cls(
            asin=data.get('asin', ''),
            name=data.get('name', ''),
            brand=data.get('brand'),
            category=data.get('category'),
            price=data.get('price'),
            rating=data.get('rating'),
            reviews_count=data.get('reviews_count'),
            sales_volume=data.get('sales_volume'),
            bsr_rank=data.get('bsr_rank'),
            available_date=data.get('available_date'),
            feature_bullets=data.get('feature_bullets'),
            has_anomaly=data.get('has_anomaly', False),
            created_at=data.get('created_at'),
            blue_ocean_score=data.get('blue_ocean_score'),
            demand_score=data.get('demand_score'),
            competition_score=data.get('competition_score'),
            barrier_score=data.get('barrier_score'),
            profit_score=data.get('profit_score'),
            listing_quality_score=data.get('listing_quality_score'),
            is_weak_listing=data.get('is_weak_listing'),
            estimated_cost=data.get('estimated_cost'),
            gross_margin=data.get('gross_margin'),
            profit_amount=data.get('profit_amount'),
            weight_lb=data.get('weight_lb')
        )


@dataclass
class CategoryValidation:
    """
    分类验证数据模型

    存储AI（Claude/Gemini）对产品分类的验证结果
    用于过滤不相关产品，确保分析数据质量
    外键: asin -> products.asin
    """
    asin: str                                      # 产品ASIN（外键）
    is_relevant: bool                              # 是否与搜索关键词相关
    category_is_correct: bool                      # 原始分类是否正确
    suggested_category: Optional[str] = None       # AI建议的正确分类
    validation_reason: Optional[str] = None        # 验证理由说明
    validated_at: Optional[datetime] = None        # 验证时间
    id: Optional[int] = None                       # 自增主键

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'asin': self.asin,
            'is_relevant': self.is_relevant,
            'category_is_correct': self.category_is_correct,
            'suggested_category': self.suggested_category,
            'validation_reason': self.validation_reason,
            'validated_at': self.validated_at.isoformat() if self.validated_at else datetime.now().isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryValidation':
        """从字典创建实例"""
        validated_at = data.get('validated_at')
        if validated_at and isinstance(validated_at, str):
            validated_at = datetime.fromisoformat(validated_at)

        return cls(
            id=data.get('id'),
            asin=data.get('asin', ''),
            is_relevant=data.get('is_relevant', False),
            category_is_correct=data.get('category_is_correct', False),
            suggested_category=data.get('suggested_category'),
            validation_reason=data.get('validation_reason'),
            validated_at=validated_at
        )


@dataclass
class SellerSpiritData:
    """
    卖家精灵数据模型

    存储从卖家精灵Chrome扩展获取的市场数据
    包含关键词搜索量、转化率、竞争度等核心指标
    """
    keyword: str                                   # 搜索关键词
    monthly_searches: Optional[int] = None         # 月搜索量
    purchase_rate: Optional[float] = None          # 购买率（搜索后购买的比例）
    click_rate: Optional[float] = None             # 点击率（搜索后点击的比例）
    conversion_rate: Optional[float] = None        # 转化率（点击后购买的比例）
    monopoly_rate: Optional[float] = None          # 垄断率（头部卖家占比）
    cr4: Optional[float] = None                    # CR4市场集中度（Top4品牌份额）
    keyword_extensions: Optional[str] = None       # 相关长尾关键词（JSON格式）
    collected_at: Optional[str] = None             # 数据采集时间
    id: Optional[int] = None                       # 自增主键

    # === 广告与趋势分析字段 ===
    cpc_bid: Optional[float] = None                # CPC建议出价（美元）
    acos_estimate: Optional[float] = None          # 预估ACoS（广告销售成本比）
    seasonality_index: Optional[float] = None      # 季节性指数（0-100，越低越稳定）
    trend_direction: Optional[str] = None          # 趋势方向：up/stable/down
    long_tail_count: Optional[int] = None          # 长尾关键词数量
    search_trend_data: Optional[str] = None        # 12个月搜索趋势数据（JSON格式）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'keyword': self.keyword,
            'monthly_searches': self.monthly_searches,
            'purchase_rate': self.purchase_rate,
            'click_rate': self.click_rate,
            'conversion_rate': self.conversion_rate,
            'monopoly_rate': self.monopoly_rate,
            'cr4': self.cr4,
            'keyword_extensions': self.keyword_extensions,
            'collected_at': self.collected_at or datetime.now().isoformat(),
            'cpc_bid': self.cpc_bid,
            'acos_estimate': self.acos_estimate,
            'seasonality_index': self.seasonality_index,
            'trend_direction': self.trend_direction,
            'long_tail_count': self.long_tail_count,
            'search_trend_data': self.search_trend_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SellerSpiritData':
        """从字典创建实例"""
        return cls(
            id=data.get('id'),
            keyword=data.get('keyword', ''),
            monthly_searches=data.get('monthly_searches'),
            purchase_rate=data.get('purchase_rate'),
            click_rate=data.get('click_rate'),
            conversion_rate=data.get('conversion_rate'),
            monopoly_rate=data.get('monopoly_rate'),
            cr4=data.get('cr4'),
            keyword_extensions=data.get('keyword_extensions'),
            collected_at=data.get('collected_at'),
            cpc_bid=data.get('cpc_bid'),
            acos_estimate=data.get('acos_estimate'),
            seasonality_index=data.get('seasonality_index'),
            trend_direction=data.get('trend_direction'),
            long_tail_count=data.get('long_tail_count'),
            search_trend_data=data.get('search_trend_data')
        )


@dataclass
class AnalysisResult:
    """
    分析结果数据模型

    存储每次关键词分析的汇总结果
    包含市场空白指数、新品数量等核心决策指标
    """
    keyword: str                                   # 分析的关键词
    market_blank_index: Optional[float] = None     # 市场空白指数（月搜索量/竞品数，>100为高机会）
    new_product_count: Optional[int] = None        # 新品数量（上架<6个月且评论>50）
    analysis_data: Optional[str] = None            # 完整分析数据（JSON格式）
    report_path: Optional[str] = None              # 生成的HTML报告路径
    created_at: Optional[str] = None               # 分析时间
    id: Optional[int] = None                       # 自增主键

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'keyword': self.keyword,
            'market_blank_index': self.market_blank_index,
            'new_product_count': self.new_product_count,
            'analysis_data': self.analysis_data,
            'report_path': self.report_path,
            'created_at': self.created_at or datetime.now().isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """从字典创建实例"""
        return cls(
            id=data.get('id'),
            keyword=data.get('keyword', ''),
            market_blank_index=data.get('market_blank_index'),
            new_product_count=data.get('new_product_count'),
            analysis_data=data.get('analysis_data'),
            report_path=data.get('report_path'),
            created_at=data.get('created_at')
        )


# 数据库表结构SQL
CREATE_TABLES_SQL = """
-- ============================================================
-- 产品表 (products)
-- 核心表，存储Amazon产品基础信息和蓝海评分
-- 主键: asin
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    asin TEXT PRIMARY KEY,              -- Amazon标准识别号
    name TEXT NOT NULL,                 -- 产品名称
    brand TEXT,                         -- 品牌名称
    category TEXT,                      -- 产品类目
    price REAL,                         -- 售价（美元）
    rating REAL,                        -- 评分（1-5星）
    reviews_count INTEGER,              -- 评论数量
    sales_volume INTEGER,               -- 月销量估算
    bsr_rank INTEGER,                   -- BSR排名
    available_date TEXT,                -- 上架日期
    feature_bullets TEXT,               -- 产品卖点（JSON）
    has_anomaly BOOLEAN DEFAULT 0,      -- 数据异常标记
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 蓝海评分字段（0-100分）
    blue_ocean_score REAL,              -- 蓝海综合评分
    demand_score REAL,                  -- 需求评分
    competition_score REAL,             -- 竞争评分
    barrier_score REAL,                 -- 进入壁垒评分
    profit_score REAL,                  -- 利润评分
    -- 腰部蓝海分析字段
    listing_quality_score REAL,         -- Listing质量分（0-100）
    is_weak_listing BOOLEAN,            -- 是否为弱listing
    estimated_cost REAL,                -- 预估采购成本
    gross_margin REAL,                  -- 毛利率
    profit_amount REAL,                 -- 单件利润额
    weight_lb REAL                      -- 产品重量（磅）
);

-- ============================================================
-- 分类验证表 (category_validations)
-- 存储AI对产品分类的验证结果，用于过滤不相关产品
-- 外键: asin -> products.asin
-- ============================================================
CREATE TABLE IF NOT EXISTS category_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asin TEXT NOT NULL,                 -- 产品ASIN（外键）
    is_relevant BOOLEAN,                -- 是否与关键词相关
    category_is_correct BOOLEAN,        -- 分类是否正确
    suggested_category TEXT,            -- AI建议的分类
    validation_reason TEXT,             -- 验证理由
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asin) REFERENCES products(asin)
);

-- ============================================================
-- 卖家精灵数据表 (sellerspirit_data)
-- 存储从卖家精灵获取的市场数据和关键词指标
-- ============================================================
CREATE TABLE IF NOT EXISTS sellerspirit_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,              -- 搜索关键词
    monthly_searches INTEGER,           -- 月搜索量
    purchase_rate REAL,                 -- 购买率
    click_rate REAL,                    -- 点击率
    conversion_rate REAL,               -- 转化率
    monopoly_rate REAL,                 -- 垄断率
    cr4 REAL,                           -- CR4市场集中度
    keyword_extensions TEXT,            -- 长尾关键词（JSON）
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 广告与趋势分析字段
    cpc_bid REAL,                       -- CPC建议出价
    acos_estimate REAL,                 -- 预估ACoS
    seasonality_index REAL,             -- 季节性指数（0-100）
    trend_direction TEXT,               -- 趋势方向
    long_tail_count INTEGER,            -- 长尾词数量
    search_trend_data TEXT              -- 12个月趋势（JSON）
);

-- ============================================================
-- 分析结果表 (analysis_results)
-- 存储每次关键词分析的汇总结果
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,              -- 分析关键词
    market_blank_index REAL,            -- 市场空白指数
    new_product_count INTEGER,          -- 新品数量
    analysis_data TEXT,                 -- 完整分析数据（JSON）
    report_path TEXT,                   -- HTML报告路径
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模型对比结果表 (model_comparisons)
-- 存储Claude与Gemini模型验证结果的对比分析
-- ============================================================
CREATE TABLE IF NOT EXISTS model_comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,              -- 关键词
    total_compared INTEGER,             -- 对比产品总数
    relevance_disagreement_count INTEGER,   -- 相关性分歧数
    category_disagreement_count INTEGER,    -- 分类分歧数
    relevance_agreement_rate REAL,      -- 相关性一致率
    category_agreement_rate REAL,       -- 分类一致率
    overall_agreement_rate REAL,        -- 总体一致率
    comparison_data TEXT,               -- 详细对比数据（JSON）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 索引定义（优化查询性能）
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_bsr_rank ON products(bsr_rank);
CREATE INDEX IF NOT EXISTS idx_category_validations_asin ON category_validations(asin);
CREATE INDEX IF NOT EXISTS idx_sellerspirit_keyword ON sellerspirit_data(keyword);
CREATE INDEX IF NOT EXISTS idx_analysis_keyword ON analysis_results(keyword);
CREATE INDEX IF NOT EXISTS idx_model_comparisons_keyword ON model_comparisons(keyword);
"""
