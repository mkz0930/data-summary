"""
关键词 CSV 缓存管理器
专门管理 scraperapi 抓取的关键词数据，避免重复下载
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.utils.logger import get_logger


class KeywordCacheManager:
    """
    关键词 CSV 缓存管理器

    功能：
    1. 将关键词搜索结果保存为 CSV 文件
    2. 检查关键词是否已缓存
    3. 从缓存加载关键词数据
    4. 管理缓存元数据（下载时间、记录数等）
    """

    def __init__(self, cache_dir: str = "data/keyword_cache"):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 元数据文件路径
        self.metadata_file = self.cache_dir / "cache_metadata.json"

        self.logger = get_logger()
        self._init_metadata()

    def _init_metadata(self):
        """初始化元数据文件"""
        if not self.metadata_file.exists():
            self._save_metadata({})

    def _load_metadata(self) -> Dict[str, Any]:
        """
        加载元数据

        Returns:
            元数据字典
        """
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载元数据失败: {e}")
            return {}

    def _save_metadata(self, metadata: Dict[str, Any]):
        """
        保存元数据

        Args:
            metadata: 元数据字典
        """
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存元数据失败: {e}")

    def _get_cache_key(self, keyword: str, country_code: str = 'us') -> str:
        """
        生成缓存键

        Args:
            keyword: 关键词
            country_code: 国家代码

        Returns:
            缓存键
        """
        return f"{keyword}_{country_code}"

    def _get_csv_path(self, keyword: str, country_code: str = 'us') -> Path:
        """
        获取 CSV 文件路径

        Args:
            keyword: 关键词
            country_code: 国家代码

        Returns:
            CSV 文件路径
        """
        # 清理关键词中的特殊字符
        safe_keyword = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in keyword)
        safe_keyword = safe_keyword.replace(' ', '_')

        filename = f"{safe_keyword}_{country_code}.csv"
        return self.cache_dir / filename

    def has_cache(self, keyword: str, country_code: str = 'us') -> bool:
        """
        检查关键词是否已缓存

        Args:
            keyword: 关键词
            country_code: 国家代码

        Returns:
            True 如果已缓存，False 如果未缓存
        """
        cache_key = self._get_cache_key(keyword, country_code)
        metadata = self._load_metadata()

        # 检查元数据中是否存在
        if cache_key not in metadata:
            return False

        # 检查 CSV 文件是否存在
        csv_path = self._get_csv_path(keyword, country_code)
        return csv_path.exists()

    def get_cache_info(self, keyword: str, country_code: str = 'us') -> Optional[Dict[str, Any]]:
        """
        获取缓存信息

        Args:
            keyword: 关键词
            country_code: 国家代码

        Returns:
            缓存信息字典，如果不存在则返回 None
        """
        if not self.has_cache(keyword, country_code):
            return None

        cache_key = self._get_cache_key(keyword, country_code)
        metadata = self._load_metadata()

        return metadata.get(cache_key)

    def save_to_cache(
        self,
        keyword: str,
        search_results: List[Dict[str, Any]],
        country_code: str = 'us',
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        将搜索结果保存到 CSV 缓存

        Args:
            keyword: 关键词
            search_results: 搜索结果列表
            country_code: 国家代码
            additional_info: 额外信息（如页数、停止原因等）

        Returns:
            CSV 文件路径
        """
        csv_path = self._get_csv_path(keyword, country_code)

        try:
            # 定义 CSV 列
            fieldnames = [
                'asin', 'name', 'brand', 'category', 'price',
                'rating', 'reviews_count', 'sales_volume',
                'purchase_history_message', 'page', 'position',
                'url', 'image_url'
            ]

            # 写入 CSV
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for result in search_results:
                    # 提取销量
                    sales_volume = self._parse_purchase_count(
                        result.get('purchase_history_message')
                    )

                    # 准备行数据
                    row = {
                        'asin': result.get('asin', ''),
                        'name': result.get('name', ''),
                        'brand': result.get('brand', ''),
                        'category': result.get('category', ''),
                        'price': result.get('price', ''),
                        'rating': result.get('rating', ''),
                        'reviews_count': result.get('reviews_count') or result.get('ratings_total', ''),
                        'sales_volume': sales_volume or '',
                        'purchase_history_message': result.get('purchase_history_message', ''),
                        'page': result.get('page', ''),
                        'position': result.get('position', ''),
                        'url': result.get('url', ''),
                        'image_url': result.get('image', '')
                    }

                    writer.writerow(row)

            # 更新元数据
            cache_key = self._get_cache_key(keyword, country_code)
            metadata = self._load_metadata()

            metadata[cache_key] = {
                'keyword': keyword,
                'country_code': country_code,
                'csv_path': str(csv_path),
                'record_count': len(search_results),
                'cached_at': datetime.now().isoformat(),
                'additional_info': additional_info or {}
            }

            self._save_metadata(metadata)

            self.logger.info(f"✓ 关键词 '{keyword}' 已缓存到: {csv_path}")
            self.logger.info(f"  - 记录数: {len(search_results)}")

            return str(csv_path)

        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")
            raise

    def load_from_cache(
        self,
        keyword: str,
        country_code: str = 'us'
    ) -> Optional[List[Dict[str, Any]]]:
        """
        从缓存加载搜索结果

        Args:
            keyword: 关键词
            country_code: 国家代码

        Returns:
            搜索结果列表，如果不存在则返回 None
        """
        if not self.has_cache(keyword, country_code):
            return None

        csv_path = self._get_csv_path(keyword, country_code)

        try:
            results = []
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 转换数据类型
                    result = {
                        'asin': row['asin'],
                        'name': row['name'],
                        'brand': row['brand'] if row['brand'] else None,
                        'category': row['category'] if row['category'] else None,
                        'price': row['price'] if row['price'] else None,
                        'rating': float(row['rating']) if row['rating'] else None,
                        'reviews_count': int(row['reviews_count']) if row['reviews_count'] else None,
                        'sales_volume': int(row['sales_volume']) if row['sales_volume'] else None,
                        'purchase_history_message': row['purchase_history_message'] if row['purchase_history_message'] else None,
                        'page': int(row['page']) if row['page'] else None,
                        'position': int(row['position']) if row['position'] else None,
                        'url': row['url'] if row['url'] else None,
                        'image_url': row['image_url'] if row['image_url'] else None
                    }
                    results.append(result)

            self.logger.info(f"✓ 从缓存加载关键词 '{keyword}': {len(results)} 条记录")
            return results

        except Exception as e:
            self.logger.error(f"加载缓存失败: {e}")
            return None

    def _parse_purchase_count(self, purchase_history_message: Optional[str]) -> Optional[int]:
        """
        从 purchase_history_message 中提取购买数量

        Args:
            purchase_history_message: 购买历史消息

        Returns:
            提取的数量，如果无法解析则返回 None
        """
        if not purchase_history_message:
            return None

        import re

        # 匹配模式: "数字+单位" 或 "数字+"
        pattern = r'(\d+(?:\.\d+)?)\s*([KkMm])?\s*\+'
        match = re.search(pattern, purchase_history_message)

        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2)

        # 转换单位
        if unit:
            unit = unit.upper()
            if unit == 'K':
                number *= 1000
            elif unit == 'M':
                number *= 1000000

        return int(number)

    def clear_cache(self, keyword: Optional[str] = None, country_code: str = 'us'):
        """
        清除缓存

        Args:
            keyword: 关键词（如果为 None 则清除所有缓存）
            country_code: 国家代码
        """
        if keyword:
            # 清除指定关键词的缓存
            cache_key = self._get_cache_key(keyword, country_code)
            csv_path = self._get_csv_path(keyword, country_code)

            # 删除 CSV 文件
            if csv_path.exists():
                csv_path.unlink()
                self.logger.info(f"✓ 已删除缓存文件: {csv_path}")

            # 更新元数据
            metadata = self._load_metadata()
            if cache_key in metadata:
                del metadata[cache_key]
                self._save_metadata(metadata)
                self.logger.info(f"✓ 已删除缓存元数据: {cache_key}")
        else:
            # 清除所有缓存
            for csv_file in self.cache_dir.glob("*.csv"):
                csv_file.unlink()

            self._save_metadata({})
            self.logger.info(f"✓ 已清除所有缓存")

    def list_cached_keywords(self) -> List[Dict[str, Any]]:
        """
        列出所有已缓存的关键词

        Returns:
            缓存信息列表
        """
        metadata = self._load_metadata()
        return list(metadata.values())

    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        metadata = self._load_metadata()

        total_keywords = len(metadata)
        total_records = sum(info.get('record_count', 0) for info in metadata.values())

        # 计算缓存文件总大小
        total_size = 0
        for csv_file in self.cache_dir.glob("*.csv"):
            total_size += csv_file.stat().st_size

        return {
            'total_keywords': total_keywords,
            'total_records': total_records,
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir),
            'keywords': list(metadata.keys())
        }
