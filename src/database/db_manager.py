"""
数据库管理模块
负责SQLite数据库的连接、操作和管理
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import datetime

from src.database.models import (
    Product, CategoryValidation, SellerSpiritData, AnalysisResult,
    CREATE_TABLES_SQL
)
from src.utils.logger import get_logger


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.logger = get_logger()

        # 设置数据库路径
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "database" / "analysis.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库，创建表"""
        try:
            with self.get_connection() as conn:
                conn.executescript(CREATE_TABLES_SQL)
                conn.commit()
            self.logger.info(f"数据库初始化成功: {self.db_path}")
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）

        Yields:
            sqlite3.Connection: 数据库连接
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        try:
            yield conn
        finally:
            conn.close()

    # ==================== 产品表操作 ====================

    def insert_product(self, product: Product) -> bool:
        """
        插入产品数据

        Args:
            product: 产品对象

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                data = product.to_dict()
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                sql = f"INSERT OR REPLACE INTO products ({columns}) VALUES ({placeholders})"
                conn.execute(sql, list(data.values()))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"插入产品数据失败 (ASIN: {product.asin}): {e}")
            return False

    def insert_products_batch(self, products: List[Product]) -> int:
        """
        批量插入产品数据

        Args:
            products: 产品对象列表

        Returns:
            成功插入的数量
        """
        success_count = 0
        try:
            with self.get_connection() as conn:
                for product in products:
                    try:
                        data = product.to_dict()
                        columns = ', '.join(data.keys())
                        placeholders = ', '.join(['?' for _ in data])
                        sql = f"INSERT OR REPLACE INTO products ({columns}) VALUES ({placeholders})"
                        conn.execute(sql, list(data.values()))
                        success_count += 1
                    except Exception as e:
                        self.logger.warning(f"插入产品失败 (ASIN: {product.asin}): {e}")
                conn.commit()
            self.logger.info(f"批量插入产品: {success_count}/{len(products)}")
        except Exception as e:
            self.logger.error(f"批量插入产品失败: {e}")
        return success_count

    def get_product(self, asin: str) -> Optional[Product]:
        """
        获取产品数据

        Args:
            asin: 产品ASIN

        Returns:
            产品对象，如果不存在则返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM products WHERE asin = ?", (asin,))
                row = cursor.fetchone()
                if row:
                    return Product.from_dict(dict(row))
        except Exception as e:
            self.logger.error(f"获取产品数据失败 (ASIN: {asin}): {e}")
        return None

    def get_all_products(self) -> List[Product]:
        """
        获取所有产品数据

        Returns:
            产品对象列表
        """
        products = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM products")
                for row in cursor:
                    products.append(Product.from_dict(dict(row)))
        except Exception as e:
            self.logger.error(f"获取所有产品失败: {e}")
        return products

    def get_products_by_category(self, category: str) -> List[Product]:
        """
        按类别获取产品

        Args:
            category: 类别名称

        Returns:
            产品对象列表
        """
        products = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM products WHERE category = ?", (category,))
                for row in cursor:
                    products.append(Product.from_dict(dict(row)))
        except Exception as e:
            self.logger.error(f"按类别获取产品失败: {e}")
        return products

    def get_products_count(self) -> int:
        """
        获取产品总数

        Returns:
            产品数量
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM products")
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"获取产品数量失败: {e}")
            return 0

    # ==================== 分类验证表操作 ====================

    def insert_category_validation(self, validation: CategoryValidation) -> bool:
        """
        插入分类验证数据

        Args:
            validation: 分类验证对象

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                sql = """
                INSERT INTO category_validations
                (asin, is_relevant, category_is_correct, suggested_category, validation_reason)
                VALUES (?, ?, ?, ?, ?)
                """
                conn.execute(sql, (
                    validation.asin,
                    validation.is_relevant,
                    validation.category_is_correct,
                    validation.suggested_category,
                    validation.validation_reason
                ))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"插入分类验证失败 (ASIN: {validation.asin}): {e}")
            return False

    def insert_category_validations_batch(self, validations: List[CategoryValidation]) -> int:
        """
        批量插入分类验证数据

        Args:
            validations: 分类验证对象列表

        Returns:
            成功插入的数量
        """
        success_count = 0
        try:
            with self.get_connection() as conn:
                sql = """
                INSERT INTO category_validations
                (asin, is_relevant, category_is_correct, suggested_category, validation_reason, validated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                for validation in validations:
                    try:
                        validated_at = validation.validated_at.isoformat() if validation.validated_at else datetime.now().isoformat()
                        conn.execute(sql, (
                            validation.asin,
                            validation.is_relevant,
                            validation.category_is_correct,
                            validation.suggested_category,
                            validation.validation_reason,
                            validated_at
                        ))
                        success_count += 1
                    except Exception as e:
                        self.logger.warning(f"插入分类验证失败 (ASIN: {validation.asin}): {e}")
                conn.commit()
            self.logger.info(f"批量插入分类验证: {success_count}/{len(validations)}")
        except Exception as e:
            self.logger.error(f"批量插入分类验证失败: {e}")
        return success_count

    def save_category_validations(self, validations: List[CategoryValidation]) -> int:
        """
        保存分类验证数据（insert_category_validations_batch的别名）

        Args:
            validations: 分类验证对象列表

        Returns:
            成功插入的数量
        """
        return self.insert_category_validations_batch(validations)

    def get_category_validation(self, asin: str) -> Optional[CategoryValidation]:
        """
        获取分类验证数据

        Args:
            asin: 产品ASIN

        Returns:
            分类验证对象，如果不存在则返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM category_validations WHERE asin = ? ORDER BY id DESC LIMIT 1",
                    (asin,)
                )
                row = cursor.fetchone()
                if row:
                    return CategoryValidation.from_dict(dict(row))
        except Exception as e:
            self.logger.error(f"获取分类验证失败 (ASIN: {asin}): {e}")
        return None

    def get_validated_asins(self) -> set:
        """
        获取所有已验证的ASIN集合

        Returns:
            已验证的ASIN集合
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT DISTINCT asin FROM category_validations")
                return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            self.logger.error(f"获取已验证ASIN列表失败: {e}")
            return set()

    def is_asin_validated(self, asin: str) -> bool:
        """
        检查ASIN是否已验证

        Args:
            asin: 产品ASIN

        Returns:
            是否已验证
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM category_validations WHERE asin = ?",
                    (asin,)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            self.logger.error(f"检查ASIN验证状态失败 (ASIN: {asin}): {e}")
            return False

    # ==================== 卖家精灵数据表操作 ====================

    def insert_sellerspirit_data(self, data: SellerSpiritData) -> bool:
        """
        插入卖家精灵数据

        Args:
            data: 卖家精灵数据对象

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                sql = """
                INSERT INTO sellerspirit_data
                (keyword, monthly_searches, cr4, keyword_extensions, collected_at)
                VALUES (?, ?, ?, ?, ?)
                """
                conn.execute(sql, (
                    data.keyword,
                    data.monthly_searches,
                    data.cr4,
                    data.keyword_extensions,
                    data.collected_at
                ))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"插入卖家精灵数据失败: {e}")
            return False

    def get_sellerspirit_data(self, keyword: str) -> Optional[SellerSpiritData]:
        """
        获取卖家精灵数据

        Args:
            keyword: 关键词

        Returns:
            卖家精灵数据对象，如果不存在则返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM sellerspirit_data WHERE keyword = ? ORDER BY id DESC LIMIT 1",
                    (keyword,)
                )
                row = cursor.fetchone()
                if row:
                    return SellerSpiritData.from_dict(dict(row))
        except Exception as e:
            self.logger.error(f"获取卖家精灵数据失败: {e}")
        return None

    # ==================== 分析结果表操作 ====================

    def insert_analysis_result(self, result: AnalysisResult) -> bool:
        """
        插入分析结果

        Args:
            result: 分析结果对象

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                sql = """
                INSERT INTO analysis_results
                (keyword, market_blank_index, new_product_count, analysis_data, report_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                conn.execute(sql, (
                    result.keyword,
                    result.market_blank_index,
                    result.new_product_count,
                    result.analysis_data,
                    result.report_path,
                    result.created_at
                ))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"插入分析结果失败: {e}")
            return False

    def get_analysis_result(self, keyword: str) -> Optional[AnalysisResult]:
        """
        获取分析结果

        Args:
            keyword: 关键词

        Returns:
            分析结果对象，如果不存在则返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM analysis_results WHERE keyword = ? ORDER BY id DESC LIMIT 1",
                    (keyword,)
                )
                row = cursor.fetchone()
                if row:
                    return AnalysisResult.from_dict(dict(row))
        except Exception as e:
            self.logger.error(f"获取分析结果失败: {e}")
        return None

    # ==================== 模型对比结果操作 ====================

    def save_model_comparison(self, keyword: str, comparison_result: Dict[str, Any]) -> bool:
        """
        保存模型对比结果

        Args:
            keyword: 关键词
            comparison_result: 对比结果字典

        Returns:
            是否成功
        """
        import json
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO model_comparisons (
                        keyword,
                        total_compared,
                        relevance_disagreement_count,
                        category_disagreement_count,
                        relevance_agreement_rate,
                        category_agreement_rate,
                        overall_agreement_rate,
                        comparison_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    keyword,
                    comparison_result['total_compared'],
                    comparison_result['relevance_disagreement_count'],
                    comparison_result['category_disagreement_count'],
                    comparison_result['relevance_agreement_rate'],
                    comparison_result['category_agreement_rate'],
                    comparison_result['overall_agreement_rate'],
                    json.dumps(comparison_result, ensure_ascii=False)
                ))
                conn.commit()
            self.logger.info(f"模型对比结果已保存: {keyword}")
            return True
        except Exception as e:
            self.logger.error(f"保存模型对比结果失败: {e}")
            return False

    def get_model_comparison(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        获取模型对比结果

        Args:
            keyword: 关键词

        Returns:
            对比结果字典，如果不存在则返回None
        """
        import json
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM model_comparisons WHERE keyword = ? ORDER BY id DESC LIMIT 1",
                    (keyword,)
                )
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    if result.get('comparison_data'):
                        result['comparison_data'] = json.loads(result['comparison_data'])
                    return result
        except Exception as e:
            self.logger.error(f"获取模型对比结果失败: {e}")
        return None

    # ==================== 通用查询操作 ====================

    def execute_query(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """
        执行自定义查询

        Args:
            sql: SQL查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        results = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(sql, params)
                for row in cursor:
                    results.append(dict(row))
        except Exception as e:
            self.logger.error(f"执行查询失败: {e}")
        return results

    def clear_table(self, table_name: str) -> bool:
        """
        清空表数据

        Args:
            table_name: 表名

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                conn.execute(f"DELETE FROM {table_name}")
                conn.commit()
            self.logger.info(f"已清空表: {table_name}")
            return True
        except Exception as e:
            self.logger.error(f"清空表失败: {e}")
            return False


# 全局数据库实例
_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """
    获取全局数据库实例（单例模式）

    Returns:
        DatabaseManager实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


def init_db(db_path: Optional[Path] = None) -> DatabaseManager:
    """
    初始化全局数据库实例

    Args:
        db_path: 数据库文件路径

    Returns:
        DatabaseManager实例
    """
    global _db_instance
    _db_instance = DatabaseManager(db_path)
    return _db_instance
