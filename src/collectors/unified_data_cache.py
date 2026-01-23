"""
统一数据缓存管理器

将4种数据源（sellerspirit、apifyAPI、scraperAPI_search、scraperAPI_product）
的缓存统一到主数据库的 raw_data_cache 表中。

通过 (source, key_type, key_value) 三元组唯一标识每条缓存记录。

使用示例:
    cache = UnifiedDataCache()

    # 缓存卖家精灵数据（按关键词）
    cache.set(DataSource.SELLERSPIRIT, "camping", {"monthly_searches": 50000})

    # 缓存产品详情（按ASIN）
    cache.set(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H", {"name": "Product"})

    # 获取缓存
    data = cache.get(DataSource.SCRAPER_PRODUCT, "B0D4RL8V3H")

    # 批量获取
    results = cache.get_batch(DataSource.SCRAPER_PRODUCT, ["ASIN1", "ASIN2"])
"""

import json
import hashlib
import sqlite3
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager

from src.utils.logger import get_logger


class DataSource(Enum):
    """数据源枚举"""
    SELLERSPIRIT = "sellerspirit"           # 卖家精灵市场数据
    APIFY_API = "apify_api"                 # Apify API产品详情
    SCRAPER_SEARCH = "scraper_search"       # ScraperAPI搜索结果
    SCRAPER_PRODUCT = "scraper_product"     # ScraperAPI产品详情


# 各数据源的默认TTL（小时）
DEFAULT_TTL_HOURS = {
    DataSource.SELLERSPIRIT: 168,       # 7天，市场数据变化较慢
    DataSource.APIFY_API: 24,           # 1天，产品详情/价格
    DataSource.SCRAPER_SEARCH: 24,      # 1天，搜索结果
    DataSource.SCRAPER_PRODUCT: 24,     # 1天，产品详情
}

# 各数据源的键类型
KEY_TYPES = {
    DataSource.SELLERSPIRIT: "keyword",
    DataSource.APIFY_API: "asin",
    DataSource.SCRAPER_SEARCH: "keyword",
    DataSource.SCRAPER_PRODUCT: "asin",
}


@dataclass
class RawDataCacheEntry:
    """缓存条目数据模型"""
    source: str                                 # 数据源
    key_type: str                               # 键类型: keyword/asin
    key_value: str                              # 键值
    data_json: str                              # 原始数据（JSON字符串）
    data_hash: Optional[str] = None             # 数据哈希
    ttl_hours: int = 24                         # 缓存有效期（小时）
    created_at: Optional[str] = None            # 创建时间
    updated_at: Optional[str] = None            # 更新时间
    expires_at: Optional[str] = None            # 过期时间
    hit_count: int = 0                          # 命中次数
    id: Optional[int] = None                    # 自增主键

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now() > expires
        except (ValueError, TypeError):
            return False

    @property
    def data(self) -> Any:
        """解析JSON数据"""
        try:
            return json.loads(self.data_json)
        except (json.JSONDecodeError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source": self.source,
            "key_type": self.key_type,
            "key_value": self.key_value,
            "data_json": self.data_json,
            "data_hash": self.data_hash,
            "ttl_hours": self.ttl_hours,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawDataCacheEntry":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            source=data.get("source", ""),
            key_type=data.get("key_type", ""),
            key_value=data.get("key_value", ""),
            data_json=data.get("data_json", "{}"),
            data_hash=data.get("data_hash"),
            ttl_hours=data.get("ttl_hours", 24),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            expires_at=data.get("expires_at"),
            hit_count=data.get("hit_count", 0),
        )


# 创建表的SQL
CREATE_RAW_DATA_CACHE_SQL = """
-- ============================================================
-- 原始数据缓存表 (raw_data_cache)
-- 统一存储4种数据源的原始数据，避免重复下载
-- 唯一约束: (source, key_type, key_value)
-- ============================================================
CREATE TABLE IF NOT EXISTS raw_data_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,               -- 数据源: sellerspirit/apify_api/scraper_search/scraper_product
    key_type TEXT NOT NULL,             -- 键类型: keyword/asin
    key_value TEXT NOT NULL,            -- 键值: 具体的关键词或ASIN
    data_json TEXT NOT NULL,            -- 原始数据（JSON格式）
    data_hash TEXT,                     -- 数据哈希（用于检测变化）
    ttl_hours INTEGER DEFAULT 24,       -- 缓存有效期（小时）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,               -- 过期时间
    hit_count INTEGER DEFAULT 0,        -- 命中次数（统计用）
    UNIQUE(source, key_type, key_value)
);

-- 索引：加速查询
CREATE INDEX IF NOT EXISTS idx_cache_lookup ON raw_data_cache(source, key_type, key_value);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON raw_data_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_source ON raw_data_cache(source);
"""


class UnifiedDataCache:
    """
    统一数据缓存管理器

    将4种数据源的缓存统一到主数据库，通过 (source, key_type, key_value) 唯一标识。
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化缓存管理器

        Args:
            db_path: 数据库路径，默认使用主数据库
        """
        self.logger = get_logger()

        # 设置数据库路径
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "database" / "analysis.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化表
        self._init_table()

    def _init_table(self) -> None:
        """初始化缓存表"""
        try:
            with self._get_connection() as conn:
                conn.executescript(CREATE_RAW_DATA_CACHE_SQL)
                conn.commit()
            self.logger.debug("raw_data_cache 表初始化成功")
        except Exception as e:
            self.logger.error(f"初始化缓存表失败: {e}")
            raise

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _compute_hash(self, data: Any) -> str:
        """计算数据哈希"""
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(json_str.encode()).hexdigest()

    def _get_key_type(self, source: DataSource) -> str:
        """获取数据源对应的键类型"""
        return KEY_TYPES.get(source, "key")

    def _get_default_ttl(self, source: DataSource) -> int:
        """获取数据源的默认TTL"""
        return DEFAULT_TTL_HOURS.get(source, 24)

    def get(
        self,
        source: DataSource,
        key_value: str,
        include_expired: bool = False
    ) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            source: 数据源
            key_value: 键值（关键词或ASIN）
            include_expired: 是否包含已过期的数据

        Returns:
            缓存的数据，不存在或已过期返回None
        """
        entry = self.get_entry(source, key_value)

        if entry is None:
            return None

        # 检查过期
        if not include_expired and entry.is_expired:
            return None

        # 更新命中次数
        self._increment_hit_count(source, key_value)

        return entry.data

    def get_entry(
        self,
        source: DataSource,
        key_value: str
    ) -> Optional[RawDataCacheEntry]:
        """
        获取缓存条目（包含元数据）

        Args:
            source: 数据源
            key_value: 键值

        Returns:
            缓存条目对象
        """
        key_type = self._get_key_type(source)

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM raw_data_cache
                    WHERE source = ? AND key_type = ? AND key_value = ?
                    """,
                    (source.value, key_type, key_value)
                )
                row = cursor.fetchone()

                if row:
                    return RawDataCacheEntry.from_dict(dict(row))
        except Exception as e:
            self.logger.error(f"获取缓存失败 [{source.value}:{key_value}]: {e}")

        return None

    def set(
        self,
        source: DataSource,
        key_value: str,
        data: Any,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        设置缓存数据

        Args:
            source: 数据源
            key_value: 键值（关键词或ASIN）
            data: 要缓存的数据
            ttl_hours: 缓存有效期（小时），None使用默认值

        Returns:
            是否成功
        """
        key_type = self._get_key_type(source)
        ttl = ttl_hours if ttl_hours is not None else self._get_default_ttl(source)

        # 计算过期时间
        now = datetime.now()
        expires_at = now + timedelta(hours=ttl)

        # 序列化数据
        try:
            data_json = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            self.logger.error(f"序列化数据失败: {e}")
            return False

        data_hash = self._compute_hash(data)

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO raw_data_cache
                    (source, key_type, key_value, data_json, data_hash, ttl_hours,
                     created_at, updated_at, expires_at, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(source, key_type, key_value) DO UPDATE SET
                        data_json = excluded.data_json,
                        data_hash = excluded.data_hash,
                        ttl_hours = excluded.ttl_hours,
                        updated_at = excluded.updated_at,
                        expires_at = excluded.expires_at
                    """,
                    (
                        source.value,
                        key_type,
                        key_value,
                        data_json,
                        data_hash,
                        ttl,
                        now.isoformat(),
                        now.isoformat(),
                        expires_at.isoformat(),
                    )
                )
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"设置缓存失败 [{source.value}:{key_value}]: {e}")
            return False

    def exists(
        self,
        source: DataSource,
        key_value: str,
        check_expired: bool = True
    ) -> bool:
        """
        检查缓存是否存在

        Args:
            source: 数据源
            key_value: 键值
            check_expired: 是否检查过期

        Returns:
            是否存在有效缓存
        """
        entry = self.get_entry(source, key_value)

        if entry is None:
            return False

        if check_expired and entry.is_expired:
            return False

        return True

    def delete(self, source: DataSource, key_value: str) -> bool:
        """
        删除缓存

        Args:
            source: 数据源
            key_value: 键值

        Returns:
            是否删除成功
        """
        key_type = self._get_key_type(source)

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM raw_data_cache
                    WHERE source = ? AND key_type = ? AND key_value = ?
                    """,
                    (source.value, key_type, key_value)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"删除缓存失败 [{source.value}:{key_value}]: {e}")
            return False

    def get_batch(
        self,
        source: DataSource,
        key_values: List[str],
        include_expired: bool = False
    ) -> Dict[str, Any]:
        """
        批量获取缓存

        Args:
            source: 数据源
            key_values: 键值列表
            include_expired: 是否包含已过期的数据

        Returns:
            {key_value: data} 字典，只包含存在的缓存
        """
        if not key_values:
            return {}

        key_type = self._get_key_type(source)
        results = {}

        try:
            with self._get_connection() as conn:
                # 构建IN查询
                placeholders = ",".join(["?" for _ in key_values])
                cursor = conn.execute(
                    f"""
                    SELECT * FROM raw_data_cache
                    WHERE source = ? AND key_type = ? AND key_value IN ({placeholders})
                    """,
                    [source.value, key_type] + list(key_values)
                )

                for row in cursor:
                    entry = RawDataCacheEntry.from_dict(dict(row))

                    # 检查过期
                    if not include_expired and entry.is_expired:
                        continue

                    results[entry.key_value] = entry.data

                # 批量更新命中次数
                if results:
                    hit_keys = list(results.keys())
                    placeholders = ",".join(["?" for _ in hit_keys])
                    conn.execute(
                        f"""
                        UPDATE raw_data_cache
                        SET hit_count = hit_count + 1
                        WHERE source = ? AND key_type = ? AND key_value IN ({placeholders})
                        """,
                        [source.value, key_type] + hit_keys
                    )
                    conn.commit()

        except Exception as e:
            self.logger.error(f"批量获取缓存失败 [{source.value}]: {e}")

        return results

    def set_batch(
        self,
        source: DataSource,
        data_dict: Dict[str, Any],
        ttl_hours: Optional[int] = None
    ) -> int:
        """
        批量设置缓存

        Args:
            source: 数据源
            data_dict: {key_value: data} 字典
            ttl_hours: 缓存有效期（小时）

        Returns:
            成功设置的数量
        """
        if not data_dict:
            return 0

        key_type = self._get_key_type(source)
        ttl = ttl_hours if ttl_hours is not None else self._get_default_ttl(source)
        now = datetime.now()
        expires_at = now + timedelta(hours=ttl)

        success_count = 0

        try:
            with self._get_connection() as conn:
                for key_value, data in data_dict.items():
                    try:
                        data_json = json.dumps(data, ensure_ascii=False)
                        data_hash = self._compute_hash(data)

                        conn.execute(
                            """
                            INSERT INTO raw_data_cache
                            (source, key_type, key_value, data_json, data_hash, ttl_hours,
                             created_at, updated_at, expires_at, hit_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                            ON CONFLICT(source, key_type, key_value) DO UPDATE SET
                                data_json = excluded.data_json,
                                data_hash = excluded.data_hash,
                                ttl_hours = excluded.ttl_hours,
                                updated_at = excluded.updated_at,
                                expires_at = excluded.expires_at
                            """,
                            (
                                source.value,
                                key_type,
                                key_value,
                                data_json,
                                data_hash,
                                ttl,
                                now.isoformat(),
                                now.isoformat(),
                                expires_at.isoformat(),
                            )
                        )
                        success_count += 1
                    except Exception as e:
                        self.logger.warning(f"设置缓存失败 [{key_value}]: {e}")

                conn.commit()
        except Exception as e:
            self.logger.error(f"批量设置缓存失败: {e}")

        return success_count

    def get_missing_keys(
        self,
        source: DataSource,
        key_values: List[str]
    ) -> List[str]:
        """
        获取缺失的键（未缓存或已过期）

        Args:
            source: 数据源
            key_values: 要检查的键值列表

        Returns:
            缺失的键值列表
        """
        if not key_values:
            return []

        cached = self.get_batch(source, key_values)
        return [k for k in key_values if k not in cached]

    def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的条目数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM raw_data_cache
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                    """,
                    (datetime.now().isoformat(),)
                )
                conn.commit()
                count = cursor.rowcount
                if count > 0:
                    self.logger.info(f"清理了 {count} 条过期缓存")
                return count
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_entries": 0,
            "by_source": {},
            "expired_count": 0,
            "total_hits": 0,
        }

        try:
            with self._get_connection() as conn:
                # 总条目数
                cursor = conn.execute("SELECT COUNT(*) FROM raw_data_cache")
                stats["total_entries"] = cursor.fetchone()[0]

                # 按数据源统计
                cursor = conn.execute(
                    """
                    SELECT source, COUNT(*) as count
                    FROM raw_data_cache
                    GROUP BY source
                    """
                )
                for row in cursor:
                    stats["by_source"][row["source"]] = row["count"]

                # 过期条目数
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM raw_data_cache
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                    """,
                    (datetime.now().isoformat(),)
                )
                stats["expired_count"] = cursor.fetchone()[0]

                # 总命中次数
                cursor = conn.execute("SELECT SUM(hit_count) FROM raw_data_cache")
                result = cursor.fetchone()[0]
                stats["total_hits"] = result if result else 0

        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")

        return stats

    def _increment_hit_count(self, source: DataSource, key_value: str) -> None:
        """递增命中次数"""
        key_type = self._get_key_type(source)

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE raw_data_cache
                    SET hit_count = hit_count + 1
                    WHERE source = ? AND key_type = ? AND key_value = ?
                    """,
                    (source.value, key_type, key_value)
                )
                conn.commit()
        except Exception:
            pass  # 命中计数失败不影响主流程

    def clear_source(self, source: DataSource) -> int:
        """
        清空指定数据源的所有缓存

        Args:
            source: 数据源

        Returns:
            清理的条目数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM raw_data_cache WHERE source = ?",
                    (source.value,)
                )
                conn.commit()
                count = cursor.rowcount
                self.logger.info(f"清空了 {source.value} 的 {count} 条缓存")
                return count
        except Exception as e:
            self.logger.error(f"清空缓存失败: {e}")
            return 0

    def clear_all(self) -> int:
        """
        清空所有缓存

        Returns:
            清理的条目数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM raw_data_cache")
                conn.commit()
                count = cursor.rowcount
                self.logger.info(f"清空了所有 {count} 条缓存")
                return count
        except Exception as e:
            self.logger.error(f"清空所有缓存失败: {e}")
            return 0


# 全局缓存实例
_cache_instance: Optional[UnifiedDataCache] = None


def get_unified_cache() -> UnifiedDataCache:
    """
    获取全局缓存实例（单例模式）

    Returns:
        UnifiedDataCache 实例
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = UnifiedDataCache()
    return _cache_instance
