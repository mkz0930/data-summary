"""
数据模型定义
定义数据库表结构和数据类
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Product:
    """产品数据模型"""
    asin: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    sales_volume: Optional[int] = None
    bsr_rank: Optional[int] = None
    available_date: Optional[str] = None
    feature_bullets: Optional[str] = None
    has_anomaly: bool = False
    created_at: Optional[str] = None

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
            'created_at': self.created_at or datetime.now().isoformat()
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
            created_at=data.get('created_at')
        )


@dataclass
class CategoryValidation:
    """分类验证数据模型"""
    asin: str
    is_relevant: bool
    category_is_correct: bool
    suggested_category: Optional[str] = None
    validation_reason: Optional[str] = None
    validated_at: Optional[datetime] = None
    id: Optional[int] = None

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
    """卖家精灵数据模型"""
    keyword: str
    monthly_searches: Optional[int] = None
    cr4: Optional[float] = None
    keyword_extensions: Optional[str] = None  # JSON格式
    collected_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'keyword': self.keyword,
            'monthly_searches': self.monthly_searches,
            'cr4': self.cr4,
            'keyword_extensions': self.keyword_extensions,
            'collected_at': self.collected_at or datetime.now().isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SellerSpiritData':
        """从字典创建实例"""
        return cls(
            id=data.get('id'),
            keyword=data.get('keyword', ''),
            monthly_searches=data.get('monthly_searches'),
            cr4=data.get('cr4'),
            keyword_extensions=data.get('keyword_extensions'),
            collected_at=data.get('collected_at')
        )


@dataclass
class AnalysisResult:
    """分析结果数据模型"""
    keyword: str
    market_blank_index: Optional[float] = None
    new_product_count: Optional[int] = None
    analysis_data: Optional[str] = None  # JSON格式
    report_path: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None

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
-- 产品表
CREATE TABLE IF NOT EXISTS products (
    asin TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    price REAL,
    rating REAL,
    reviews_count INTEGER,
    sales_volume INTEGER,
    bsr_rank INTEGER,
    available_date TEXT,
    feature_bullets TEXT,
    has_anomaly BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 分类验证表
CREATE TABLE IF NOT EXISTS category_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asin TEXT NOT NULL,
    is_relevant BOOLEAN,
    category_is_correct BOOLEAN,
    suggested_category TEXT,
    validation_reason TEXT,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asin) REFERENCES products(asin)
);

-- 卖家精灵数据表
CREATE TABLE IF NOT EXISTS sellerspirit_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    monthly_searches INTEGER,
    cr4 REAL,
    keyword_extensions TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 分析结果表
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    market_blank_index REAL,
    new_product_count INTEGER,
    analysis_data TEXT,
    report_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型对比结果表
CREATE TABLE IF NOT EXISTS model_comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    total_compared INTEGER,
    relevance_disagreement_count INTEGER,
    category_disagreement_count INTEGER,
    relevance_agreement_rate REAL,
    category_agreement_rate REAL,
    overall_agreement_rate REAL,
    comparison_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_bsr_rank ON products(bsr_rank);
CREATE INDEX IF NOT EXISTS idx_category_validations_asin ON category_validations(asin);
CREATE INDEX IF NOT EXISTS idx_sellerspirit_keyword ON sellerspirit_data(keyword);
CREATE INDEX IF NOT EXISTS idx_analysis_keyword ON analysis_results(keyword);
CREATE INDEX IF NOT EXISTS idx_model_comparisons_keyword ON model_comparisons(keyword);
"""
