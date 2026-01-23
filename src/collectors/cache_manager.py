"""
统一缓存管理器模块
提供通用的缓存接口，支持 TTL 过期、LRU 淘汰、统计信息
"""

import json
import hashlib
import time
import os
import pickle
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import Lock
from datetime import datetime

from src.utils.logger import get_logger


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> float:
        """剩余 TTL（秒）"""
        if self.expires_at == 0:
            return float('inf')
        return max(0, self.expires_at - time.time())


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    expired_evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'evictions': self.evictions,
            'expired_evictions': self.expired_evictions,
            'hit_rate': round(self.hit_rate, 2),
            'total_size_bytes': self.total_size_bytes,
            'total_size_mb': round(self.total_size_bytes / 1024 / 1024, 2),
            'entry_count': self.entry_count
        }


class MemoryCache:
    """
    内存缓存

    支持 TTL 过期和 LRU 淘汰
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600
    ):
        """
        初始化内存缓存

        Args:
            max_size: 最大条目数
            default_ttl: 默认 TTL（秒），0 表示永不过期
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self.stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期返回 None
        """
        with self._lock:
            if key not in self._cache:
                self.stats.misses += 1
                return None

            entry = self._cache[key]

            # 检查过期
            if entry.is_expired:
                del self._cache[key]
                self.stats.misses += 1
                self.stats.expired_evictions += 1
                self.stats.entry_count -= 1
                return None

            # 更新访问信息（LRU）
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._cache.move_to_end(key)

            self.stats.hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: TTL（秒），None 使用默认值
        """
        with self._lock:
            # 计算过期时间
            ttl = ttl if ttl is not None else self.default_ttl
            expires_at = time.time() + ttl if ttl > 0 else 0

            # 估算大小
            try:
                size_bytes = len(pickle.dumps(value))
            except Exception:
                size_bytes = 0

            # 创建条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
                last_accessed=time.time(),
                size_bytes=size_bytes
            )

            # 如果已存在，更新
            if key in self._cache:
                old_entry = self._cache[key]
                self.stats.total_size_bytes -= old_entry.size_bytes
            else:
                self.stats.entry_count += 1

            self._cache[key] = entry
            self._cache.move_to_end(key)
            self.stats.sets += 1
            self.stats.total_size_bytes += size_bytes

            # LRU 淘汰
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                oldest_entry = self._cache.pop(oldest_key)
                self.stats.evictions += 1
                self.stats.entry_count -= 1
                self.stats.total_size_bytes -= oldest_entry.size_bytes

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self.stats.deletes += 1
                self.stats.entry_count -= 1
                self.stats.total_size_bytes -= entry.size_bytes
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self.stats.entry_count = 0
            self.stats.total_size_bytes = 0

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]

            for key in expired_keys:
                entry = self._cache.pop(key)
                self.stats.expired_evictions += 1
                self.stats.entry_count -= 1
                self.stats.total_size_bytes -= entry.size_bytes

            return len(expired_keys)


class FileCache:
    """
    文件缓存

    将缓存持久化到文件系统
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
        default_ttl_hours: int = 24,
        max_size_mb: int = 500
    ):
        """
        初始化文件缓存

        Args:
            cache_dir: 缓存目录
            default_ttl_hours: 默认 TTL（小时）
            max_size_mb: 最大缓存大小（MB）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_hours = default_ttl_hours
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.logger = get_logger()
        self.stats = CacheStats()

        # 元数据文件
        self.metadata_file = self.cache_dir / "_metadata.json"
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'entries': {}, 'total_size': 0}

    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            self.logger.warning(f"保存缓存元数据失败: {e}")

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用 MD5 哈希作为文件名
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期返回 None
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.stats.misses += 1
            return None

        # 检查元数据
        entry_meta = self._metadata.get('entries', {}).get(key)
        if entry_meta:
            expires_at = entry_meta.get('expires_at', 0)
            if expires_at > 0 and time.time() > expires_at:
                # 已过期，删除
                self.delete(key)
                self.stats.misses += 1
                self.stats.expired_evictions += 1
                return None

        try:
            with open(cache_path, 'rb') as f:
                value = pickle.load(f)
            self.stats.hits += 1

            # 更新访问时间
            if key in self._metadata.get('entries', {}):
                self._metadata['entries'][key]['last_accessed'] = time.time()
                self._metadata['entries'][key]['access_count'] = \
                    self._metadata['entries'][key].get('access_count', 0) + 1

            return value
        except Exception as e:
            self.logger.warning(f"读取缓存失败 {key}: {e}")
            self.stats.misses += 1
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_hours: Optional[int] = None
    ):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl_hours: TTL（小时），None 使用默认值
        """
        cache_path = self._get_cache_path(key)
        ttl_hours = ttl_hours if ttl_hours is not None else self.default_ttl_hours

        try:
            # 序列化并保存
            data = pickle.dumps(value)
            size_bytes = len(data)

            with open(cache_path, 'wb') as f:
                f.write(data)

            # 更新元数据
            expires_at = time.time() + ttl_hours * 3600 if ttl_hours > 0 else 0

            if 'entries' not in self._metadata:
                self._metadata['entries'] = {}

            # 如果已存在，减去旧大小
            if key in self._metadata['entries']:
                old_size = self._metadata['entries'][key].get('size_bytes', 0)
                self._metadata['total_size'] = self._metadata.get('total_size', 0) - old_size

            self._metadata['entries'][key] = {
                'created_at': time.time(),
                'expires_at': expires_at,
                'size_bytes': size_bytes,
                'last_accessed': time.time(),
                'access_count': 0
            }
            self._metadata['total_size'] = self._metadata.get('total_size', 0) + size_bytes

            self._save_metadata()
            self.stats.sets += 1
            self.stats.total_size_bytes = self._metadata.get('total_size', 0)
            self.stats.entry_count = len(self._metadata.get('entries', {}))

            # 检查是否需要清理
            if self._metadata.get('total_size', 0) > self.max_size_bytes:
                self._cleanup_lru()

        except Exception as e:
            self.logger.error(f"保存缓存失败 {key}: {e}")

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        cache_path = self._get_cache_path(key)

        try:
            if cache_path.exists():
                cache_path.unlink()

            if key in self._metadata.get('entries', {}):
                size_bytes = self._metadata['entries'][key].get('size_bytes', 0)
                del self._metadata['entries'][key]
                self._metadata['total_size'] = max(0, self._metadata.get('total_size', 0) - size_bytes)
                self._save_metadata()

            self.stats.deletes += 1
            return True
        except Exception as e:
            self.logger.warning(f"删除缓存失败 {key}: {e}")
            return False

    def _cleanup_lru(self):
        """LRU 清理"""
        entries = self._metadata.get('entries', {})
        if not entries:
            return

        # 按最后访问时间排序
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1].get('last_accessed', 0)
        )

        # 删除最旧的 20%
        to_delete = len(sorted_entries) // 5
        for key, _ in sorted_entries[:max(1, to_delete)]:
            self.delete(key)
            self.stats.evictions += 1

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        entries = self._metadata.get('entries', {})
        now = time.time()

        expired_keys = [
            key for key, meta in entries.items()
            if meta.get('expires_at', 0) > 0 and now > meta.get('expires_at', 0)
        ]

        for key in expired_keys:
            self.delete(key)
            self.stats.expired_evictions += 1

        return len(expired_keys)

    def clear(self):
        """清空缓存"""
        # 删除所有缓存文件
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
            except Exception:
                pass

        self._metadata = {'entries': {}, 'total_size': 0}
        self._save_metadata()
        self.stats.entry_count = 0
        self.stats.total_size_bytes = 0


class CacheManager:
    """
    统一缓存管理器

    提供统一的缓存接口，支持内存缓存和文件缓存
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
        memory_max_size: int = 500,
        memory_ttl: int = 3600,
        file_ttl_hours: int = 24,
        file_max_size_mb: int = 500,
        enable_memory_cache: bool = True,
        enable_file_cache: bool = True
    ):
        """
        初始化缓存管理器

        Args:
            cache_dir: 文件缓存目录
            memory_max_size: 内存缓存最大条目数
            memory_ttl: 内存缓存 TTL（秒）
            file_ttl_hours: 文件缓存 TTL（小时）
            file_max_size_mb: 文件缓存最大大小（MB）
            enable_memory_cache: 是否启用内存缓存
            enable_file_cache: 是否启用文件缓存
        """
        self.logger = get_logger()

        self.memory_cache = MemoryCache(
            max_size=memory_max_size,
            default_ttl=memory_ttl
        ) if enable_memory_cache else None

        self.file_cache = FileCache(
            cache_dir=cache_dir,
            default_ttl_hours=file_ttl_hours,
            max_size_mb=file_max_size_mb
        ) if enable_file_cache else None

    def get(self, key: str, use_file: bool = True) -> Optional[Any]:
        """
        获取缓存值

        优先从内存缓存获取，未命中则从文件缓存获取

        Args:
            key: 缓存键
            use_file: 是否使用文件缓存

        Returns:
            缓存值
        """
        # 先查内存缓存
        if self.memory_cache:
            value = self.memory_cache.get(key)
            if value is not None:
                return value

        # 再查文件缓存
        if use_file and self.file_cache:
            value = self.file_cache.get(key)
            if value is not None:
                # 回填到内存缓存
                if self.memory_cache:
                    self.memory_cache.set(key, value)
                return value

        return None

    def set(
        self,
        key: str,
        value: Any,
        memory_ttl: Optional[int] = None,
        file_ttl_hours: Optional[int] = None,
        persist: bool = True
    ):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            memory_ttl: 内存缓存 TTL（秒）
            file_ttl_hours: 文件缓存 TTL（小时）
            persist: 是否持久化到文件
        """
        # 写入内存缓存
        if self.memory_cache:
            self.memory_cache.set(key, value, memory_ttl)

        # 写入文件缓存
        if persist and self.file_cache:
            self.file_cache.set(key, value, file_ttl_hours)

    def delete(self, key: str):
        """
        删除缓存

        Args:
            key: 缓存键
        """
        if self.memory_cache:
            self.memory_cache.delete(key)
        if self.file_cache:
            self.file_cache.delete(key)

    def invalidate(self, key: str):
        """
        使缓存失效（delete 的别名）

        Args:
            key: 缓存键
        """
        self.delete(key)

    def clear(self, memory_only: bool = False):
        """
        清空缓存

        Args:
            memory_only: 是否只清空内存缓存
        """
        if self.memory_cache:
            self.memory_cache.clear()
        if not memory_only and self.file_cache:
            self.file_cache.clear()

    def cleanup_expired(self) -> Dict[str, int]:
        """
        清理过期条目

        Returns:
            清理统计 {'memory': count, 'file': count}
        """
        result = {'memory': 0, 'file': 0}

        if self.memory_cache:
            result['memory'] = self.memory_cache.cleanup_expired()
        if self.file_cache:
            result['file'] = self.file_cache.cleanup_expired()

        return result

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        stats = {}

        if self.memory_cache:
            stats['memory'] = self.memory_cache.stats.to_dict()
        if self.file_cache:
            stats['file'] = self.file_cache.stats.to_dict()

        # 计算总体统计
        total_hits = sum(s.get('hits', 0) for s in stats.values())
        total_misses = sum(s.get('misses', 0) for s in stats.values())
        total_requests = total_hits + total_misses

        stats['total'] = {
            'hits': total_hits,
            'misses': total_misses,
            'hit_rate': round(total_hits / total_requests * 100, 2) if total_requests > 0 else 0
        }

        return stats

    def cached(
        self,
        key_func: Optional[Callable[..., str]] = None,
        memory_ttl: Optional[int] = None,
        file_ttl_hours: Optional[int] = None,
        persist: bool = True
    ):
        """
        缓存装饰器

        Args:
            key_func: 生成缓存键的函数，接收与被装饰函数相同的参数
            memory_ttl: 内存缓存 TTL（秒）
            file_ttl_hours: 文件缓存 TTL（小时）
            persist: 是否持久化到文件

        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # 默认使用函数名和参数生成键
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = ":".join(key_parts)

                # 尝试从缓存获取
                cached_value = self.get(cache_key, use_file=persist)
                if cached_value is not None:
                    return cached_value

                # 执行函数
                result = func(*args, **kwargs)

                # 缓存结果
                self.set(
                    cache_key,
                    result,
                    memory_ttl=memory_ttl,
                    file_ttl_hours=file_ttl_hours,
                    persist=persist
                )

                return result

            return wrapper
        return decorator
