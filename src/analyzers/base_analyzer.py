"""
分析器基类模块
提供所有分析器的公共功能和工具方法
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import statistics
import math

from src.database.models import Product, SellerSpiritData
from src.utils.logger import get_logger


class GradeLevel(Enum):
    """评分等级枚举"""
    A_PLUS = ('A+', 90, 100, '极佳')
    A = ('A', 80, 89, '优秀')
    B_PLUS = ('B+', 70, 79, '良好')
    B = ('B', 60, 69, '较好')
    C = ('C', 50, 59, '一般')
    D = ('D', 35, 49, '较差')
    F = ('F', 0, 34, '不推荐')

    def __init__(self, grade: str, min_score: int, max_score: int, desc: str):
        self.grade = grade
        self.min_score = min_score
        self.max_score = max_score
        self.desc = desc

    @classmethod
    def from_score(cls, score: float) -> 'GradeLevel':
        """根据分数获取等级"""
        score = max(0, min(100, score))
        for level in cls:
            if level.min_score <= score <= level.max_score:
                return level
        return cls.F


@dataclass
class StatisticsResult:
    """统计结果数据类"""
    count: int
    mean: float
    median: float
    std: float
    min_val: float
    max_val: float
    q1: float  # 25th percentile
    q3: float  # 75th percentile
    iqr: float  # Interquartile range

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'count': self.count,
            'mean': round(self.mean, 2),
            'median': round(self.median, 2),
            'std': round(self.std, 2),
            'min': round(self.min_val, 2),
            'max': round(self.max_val, 2),
            'q1': round(self.q1, 2),
            'q3': round(self.q3, 2),
            'iqr': round(self.iqr, 2)
        }


class BaseAnalyzer(ABC):
    """
    分析器基类

    提供所有分析器共用的工具方法：
    - 统计计算
    - 分数归一化
    - 等级评定
    - 异常值过滤
    - 安全除法
    """

    def __init__(self, name: str = "BaseAnalyzer"):
        """
        初始化分析器

        Args:
            name: 分析器名称
        """
        self.name = name
        self.logger = get_logger()

    @abstractmethod
    def analyze(
        self,
        products: List[Product],
        sellerspirit_data: Optional[SellerSpiritData] = None
    ) -> Dict[str, Any]:
        """
        执行分析（子类必须实现）

        Args:
            products: 产品列表
            sellerspirit_data: 卖家精灵数据

        Returns:
            分析结果字典
        """
        pass

    # ==================== 统计计算方法 ====================

    def calculate_statistics(
        self,
        values: List[Union[int, float]],
        filter_outliers: bool = False
    ) -> StatisticsResult:
        """
        计算统计指标

        Args:
            values: 数值列表
            filter_outliers: 是否过滤异常值

        Returns:
            StatisticsResult 统计结果
        """
        if not values:
            return StatisticsResult(
                count=0, mean=0, median=0, std=0,
                min_val=0, max_val=0, q1=0, q3=0, iqr=0
            )

        # 过滤 None 和无效值
        clean_values = [v for v in values if v is not None and not math.isnan(v)]

        if not clean_values:
            return StatisticsResult(
                count=0, mean=0, median=0, std=0,
                min_val=0, max_val=0, q1=0, q3=0, iqr=0
            )

        # 可选：过滤异常值
        if filter_outliers and len(clean_values) >= 4:
            clean_values = self.filter_outliers_iqr(clean_values)

        count = len(clean_values)
        mean = statistics.mean(clean_values)
        median = statistics.median(clean_values)
        std = statistics.stdev(clean_values) if count > 1 else 0
        min_val = min(clean_values)
        max_val = max(clean_values)

        # 计算四分位数
        sorted_values = sorted(clean_values)
        q1 = self.calculate_percentile(sorted_values, 25)
        q3 = self.calculate_percentile(sorted_values, 75)
        iqr = q3 - q1

        return StatisticsResult(
            count=count,
            mean=mean,
            median=median,
            std=std,
            min_val=min_val,
            max_val=max_val,
            q1=q1,
            q3=q3,
            iqr=iqr
        )

    def calculate_percentile(
        self,
        values: List[Union[int, float]],
        percentile: float
    ) -> float:
        """
        计算百分位数

        Args:
            values: 已排序的数值列表
            percentile: 百分位 (0-100)

        Returns:
            百分位数值
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)

        if n == 1:
            return sorted_values[0]

        # 使用线性插值
        k = (n - 1) * (percentile / 100)
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return sorted_values[int(k)]

        return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)

    def calculate_percentile_rank(
        self,
        value: float,
        values: List[Union[int, float]]
    ) -> float:
        """
        计算某个值在列表中的百分位排名

        Args:
            value: 要计算排名的值
            values: 数值列表

        Returns:
            百分位排名 (0-100)
        """
        if not values:
            return 50.0

        sorted_values = sorted(values)
        n = len(sorted_values)

        # 计算小于该值的数量
        count_below = sum(1 for v in sorted_values if v < value)
        count_equal = sum(1 for v in sorted_values if v == value)

        # 使用中间排名法
        percentile = ((count_below + 0.5 * count_equal) / n) * 100
        return percentile

    # ==================== 分数归一化方法 ====================

    def normalize_score(
        self,
        value: float,
        min_val: float,
        max_val: float,
        inverse: bool = False
    ) -> float:
        """
        将值归一化到 0-100 范围

        Args:
            value: 原始值
            min_val: 最小值
            max_val: 最大值
            inverse: 是否反向（值越小分数越高）

        Returns:
            归一化后的分数 (0-100)
        """
        if max_val == min_val:
            return 50.0

        # 限制在范围内
        value = max(min_val, min(max_val, value))

        # 归一化
        normalized = (value - min_val) / (max_val - min_val) * 100

        if inverse:
            normalized = 100 - normalized

        return round(normalized, 2)

    def normalize_score_log(
        self,
        value: float,
        min_val: float = 1,
        max_val: float = 10000,
        inverse: bool = False
    ) -> float:
        """
        使用对数尺度归一化（适用于跨度大的数据如销量、评论数）

        Args:
            value: 原始值
            min_val: 最小值
            max_val: 最大值
            inverse: 是否反向

        Returns:
            归一化后的分数 (0-100)
        """
        if value <= 0:
            return 0.0 if not inverse else 100.0

        value = max(min_val, min(max_val, value))

        log_value = math.log10(value)
        log_min = math.log10(max(min_val, 1))
        log_max = math.log10(max_val)

        if log_max == log_min:
            return 50.0

        normalized = (log_value - log_min) / (log_max - log_min) * 100

        if inverse:
            normalized = 100 - normalized

        return round(normalized, 2)

    def normalize_score_sigmoid(
        self,
        value: float,
        midpoint: float,
        steepness: float = 0.1
    ) -> float:
        """
        使用 Sigmoid 函数归一化（适用于需要平滑过渡的场景）

        Args:
            value: 原始值
            midpoint: 中点值（对应50分）
            steepness: 陡峭度

        Returns:
            归一化后的分数 (0-100)
        """
        try:
            score = 100 / (1 + math.exp(-steepness * (value - midpoint)))
            return round(score, 2)
        except OverflowError:
            return 100.0 if value > midpoint else 0.0

    # ==================== 等级评定方法 ====================

    def grade_score(self, score: float) -> str:
        """
        根据分数评定等级

        Args:
            score: 分数 (0-100)

        Returns:
            等级字符串 (A+, A, B+, B, C, D, F)
        """
        return GradeLevel.from_score(score).grade

    def grade_score_with_desc(self, score: float) -> Tuple[str, str]:
        """
        根据分数评定等级并返回描述

        Args:
            score: 分数 (0-100)

        Returns:
            (等级, 描述) 元组
        """
        level = GradeLevel.from_score(score)
        return level.grade, level.desc

    def categorize_value(
        self,
        value: float,
        thresholds: List[Tuple[float, str]]
    ) -> str:
        """
        根据阈值分类

        Args:
            value: 要分类的值
            thresholds: [(阈值, 类别名称), ...] 按阈值升序排列

        Returns:
            类别名称
        """
        for threshold, category in thresholds:
            if value <= threshold:
                return category
        return thresholds[-1][1] if thresholds else "未知"

    # ==================== 异常值处理方法 ====================

    def filter_outliers_iqr(
        self,
        values: List[Union[int, float]],
        multiplier: float = 1.5
    ) -> List[Union[int, float]]:
        """
        使用 IQR 方法过滤异常值

        Args:
            values: 数值列表
            multiplier: IQR 乘数（默认1.5）

        Returns:
            过滤后的列表
        """
        if len(values) < 4:
            return values

        sorted_values = sorted(values)
        q1 = self.calculate_percentile(sorted_values, 25)
        q3 = self.calculate_percentile(sorted_values, 75)
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        return [v for v in values if lower_bound <= v <= upper_bound]

    def filter_outliers_zscore(
        self,
        values: List[Union[int, float]],
        threshold: float = 3.0
    ) -> List[Union[int, float]]:
        """
        使用 Z-score 方法过滤异常值

        Args:
            values: 数值列表
            threshold: Z-score 阈值（默认3.0）

        Returns:
            过滤后的列表
        """
        if len(values) < 3:
            return values

        mean = statistics.mean(values)
        std = statistics.stdev(values)

        if std == 0:
            return values

        return [v for v in values if abs((v - mean) / std) <= threshold]

    # ==================== 安全计算方法 ====================

    def safe_divide(
        self,
        numerator: float,
        denominator: float,
        default: float = 0.0
    ) -> float:
        """
        安全除法

        Args:
            numerator: 分子
            denominator: 分母
            default: 除数为0时的默认值

        Returns:
            除法结果或默认值
        """
        if denominator == 0:
            return default
        return numerator / denominator

    def safe_percentage(
        self,
        part: float,
        total: float,
        decimals: int = 2
    ) -> float:
        """
        安全计算百分比

        Args:
            part: 部分
            total: 总数
            decimals: 小数位数

        Returns:
            百分比值
        """
        if total == 0:
            return 0.0
        return round((part / total) * 100, decimals)

    # ==================== 数据提取方法 ====================

    def extract_values(
        self,
        products: List[Product],
        attribute: str,
        filter_none: bool = True
    ) -> List[Any]:
        """
        从产品列表中提取指定属性值

        Args:
            products: 产品列表
            attribute: 属性名称
            filter_none: 是否过滤 None 值

        Returns:
            属性值列表
        """
        values = [getattr(p, attribute, None) for p in products]
        if filter_none:
            values = [v for v in values if v is not None]
        return values

    def extract_numeric_values(
        self,
        products: List[Product],
        attribute: str
    ) -> List[float]:
        """
        从产品列表中提取数值属性

        Args:
            products: 产品列表
            attribute: 属性名称

        Returns:
            数值列表
        """
        values = []
        for p in products:
            val = getattr(p, attribute, None)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        return values

    # ==================== 分组分析方法 ====================

    def group_by_range(
        self,
        values: List[float],
        ranges: List[Tuple[float, float, str]]
    ) -> Dict[str, int]:
        """
        按范围分组统计

        Args:
            values: 数值列表
            ranges: [(min, max, label), ...] 范围定义

        Returns:
            {label: count} 分组统计
        """
        result = {label: 0 for _, _, label in ranges}

        for value in values:
            for min_val, max_val, label in ranges:
                if min_val <= value < max_val:
                    result[label] += 1
                    break

        return result

    def group_products_by_attribute(
        self,
        products: List[Product],
        attribute: str
    ) -> Dict[Any, List[Product]]:
        """
        按属性分组产品

        Args:
            products: 产品列表
            attribute: 分组属性

        Returns:
            {属性值: [产品列表]} 分组结果
        """
        groups = {}
        for product in products:
            key = getattr(product, attribute, None)
            if key not in groups:
                groups[key] = []
            groups[key].append(product)
        return groups

    # ==================== 日志方法 ====================

    def log_info(self, message: str):
        """记录信息日志"""
        self.logger.info(f"[{self.name}] {message}")

    def log_warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(f"[{self.name}] {message}")

    def log_error(self, message: str):
        """记录错误日志"""
        self.logger.error(f"[{self.name}] {message}")

    def log_debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(f"[{self.name}] {message}")
