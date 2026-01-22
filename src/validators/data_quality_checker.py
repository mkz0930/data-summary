"""
数据质量检查器模块
检查产品数据的完整性和异常情况
"""

from typing import List, Dict, Any, Set
from datetime import datetime, timedelta

from src.database.models import Product
from src.utils.logger import get_logger


class DataQualityChecker:
    """数据质量检查器"""

    def __init__(self):
        """初始化数据质量检查器"""
        self.logger = get_logger()

    def check_product(self, product: Product) -> Dict[str, Any]:
        """
        检查单个产品的数据质量

        Args:
            product: 产品对象

        Returns:
            检查结果字典
        """
        issues = []
        warnings = []

        # 检查必需字段
        if not product.asin:
            issues.append("缺少ASIN")
        if not product.name:
            issues.append("缺少产品名称")

        # 检查价格
        if product.price is None:
            warnings.append("缺少价格信息")
        elif product.price <= 0:
            issues.append(f"价格异常: ${product.price}")
        elif product.price > 10000:
            warnings.append(f"价格过高: ${product.price}")

        # 检查评分
        if product.rating is not None:
            if product.rating < 0 or product.rating > 5:
                issues.append(f"评分超出范围: {product.rating}")
        else:
            warnings.append("缺少评分信息")

        # 检查评论数
        if product.reviews_count is not None:
            if product.reviews_count < 0:
                issues.append(f"评论数异常: {product.reviews_count}")
        else:
            warnings.append("缺少评论数信息")

        # 检查BSR排名
        if product.bsr_rank is not None:
            if product.bsr_rank <= 0:
                issues.append(f"BSR排名异常: {product.bsr_rank}")
        else:
            warnings.append("缺少BSR排名信息")

        # 检查销量
        if product.sales_volume is not None:
            if product.sales_volume < 0:
                issues.append(f"销量异常: {product.sales_volume}")

        # 检查上架时间
        if product.available_date:
            try:
                available_date = datetime.fromisoformat(product.available_date.replace('Z', '+00:00'))
                if available_date > datetime.now():
                    issues.append(f"上架时间在未来: {product.available_date}")
            except Exception as e:
                warnings.append(f"上架时间格式错误: {product.available_date}")

        # 检查品牌
        if not product.brand:
            warnings.append("缺少品牌信息")

        # 检查分类
        if not product.category:
            warnings.append("缺少分类信息")

        return {
            'asin': product.asin,
            'has_issues': len(issues) > 0,
            'has_warnings': len(warnings) > 0,
            'issues': issues,
            'warnings': warnings,
            'quality_score': self._calculate_quality_score(product, issues, warnings)
        }

    def check_batch(self, products: List[Product]) -> Dict[str, Any]:
        """
        批量检查产品数据质量

        Args:
            products: 产品列表

        Returns:
            批量检查结果
        """
        self.logger.info(f"开始检查 {len(products)} 个产品的数据质量")

        results = []
        for product in products:
            result = self.check_product(product)
            results.append(result)

        # 统计信息
        total = len(results)
        with_issues = sum(1 for r in results if r['has_issues'])
        with_warnings = sum(1 for r in results if r['has_warnings'])
        avg_quality_score = sum(r['quality_score'] for r in results) / total if total > 0 else 0

        # 收集所有问题类型
        all_issues = {}
        all_warnings = {}

        for result in results:
            for issue in result['issues']:
                all_issues[issue] = all_issues.get(issue, 0) + 1
            for warning in result['warnings']:
                all_warnings[warning] = all_warnings.get(warning, 0) + 1

        summary = {
            'total_products': total,
            'products_with_issues': with_issues,
            'products_with_warnings': with_warnings,
            'average_quality_score': round(avg_quality_score, 2),
            'issue_types': all_issues,
            'warning_types': all_warnings,
            'details': results
        }

        self.logger.info(f"质量检查完成: {with_issues} 个产品有问题, "
                        f"{with_warnings} 个产品有警告, "
                        f"平均质量分: {avg_quality_score:.2f}")

        return summary

    def _calculate_quality_score(
        self,
        product: Product,
        issues: List[str],
        warnings: List[str]
    ) -> float:
        """
        计算产品数据质量分数（0-100）

        Args:
            product: 产品对象
            issues: 问题列表
            warnings: 警告列表

        Returns:
            质量分数
        """
        score = 100.0

        # 每个严重问题扣20分
        score -= len(issues) * 20

        # 每个警告扣5分
        score -= len(warnings) * 5

        # 确保分数在0-100之间
        return max(0.0, min(100.0, score))

    def find_duplicates(self, products: List[Product]) -> List[str]:
        """
        查找重复的ASIN

        Args:
            products: 产品列表

        Returns:
            重复的ASIN列表
        """
        asin_counts = {}
        for product in products:
            asin_counts[product.asin] = asin_counts.get(product.asin, 0) + 1

        duplicates = [asin for asin, count in asin_counts.items() if count > 1]

        if duplicates:
            self.logger.warning(f"发现 {len(duplicates)} 个重复ASIN")

        return duplicates

    def find_outliers(
        self,
        products: List[Product],
        field: str = 'price',
        threshold: float = 3.0
    ) -> List[Product]:
        """
        查找异常值产品（使用标准差方法）

        Args:
            products: 产品列表
            field: 要检查的字段名
            threshold: 标准差倍数阈值

        Returns:
            异常产品列表
        """
        # 提取有效值
        values = []
        valid_products = []

        for product in products:
            value = getattr(product, field, None)
            if value is not None and value > 0:
                values.append(value)
                valid_products.append(product)

        if len(values) < 3:
            return []

        # 计算均值和标准差
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5

        # 查找异常值
        outliers = []
        for product, value in zip(valid_products, values):
            z_score = abs(value - mean) / std_dev if std_dev > 0 else 0
            if z_score > threshold:
                outliers.append(product)

        if outliers:
            self.logger.info(f"在字段 '{field}' 中发现 {len(outliers)} 个异常值")

        return outliers

    def check_completeness(self, products: List[Product]) -> Dict[str, float]:
        """
        检查数据完整性（各字段的填充率）

        Args:
            products: 产品列表

        Returns:
            各字段的完整率字典
        """
        if not products:
            return {}

        total = len(products)
        fields = ['name', 'brand', 'category', 'price', 'rating',
                 'reviews_count', 'sales_volume', 'bsr_rank', 'available_date']

        completeness = {}
        for field in fields:
            filled = sum(1 for p in products if getattr(p, field, None) is not None)
            completeness[field] = round(filled / total * 100, 2)

        return completeness

    def mark_anomalies(
        self,
        products: List[Product],
        quality_threshold: float = 60.0
    ) -> List[Product]:
        """
        标记异常产品

        Args:
            products: 产品列表
            quality_threshold: 质量分数阈值

        Returns:
            标记后的产品列表
        """
        marked_count = 0

        for product in products:
            result = self.check_product(product)
            if result['quality_score'] < quality_threshold or result['has_issues']:
                product.has_anomaly = True
                marked_count += 1

        self.logger.info(f"标记了 {marked_count} 个异常产品")

        return products

    def get_quality_report(self, products: List[Product]) -> str:
        """
        生成数据质量报告

        Args:
            products: 产品列表

        Returns:
            报告文本
        """
        check_result = self.check_batch(products)
        completeness = self.check_completeness(products)
        duplicates = self.find_duplicates(products)

        report = f"""
数据质量报告
{'=' * 50}

总体统计:
- 总产品数: {check_result['total_products']}
- 有问题的产品: {check_result['products_with_issues']}
- 有警告的产品: {check_result['products_with_warnings']}
- 平均质量分: {check_result['average_quality_score']}/100

数据完整性:
"""
        for field, rate in completeness.items():
            report += f"- {field}: {rate}%\n"

        if duplicates:
            report += f"\n重复ASIN: {len(duplicates)} 个\n"

        if check_result['issue_types']:
            report += "\n主要问题:\n"
            for issue, count in sorted(check_result['issue_types'].items(),
                                      key=lambda x: x[1], reverse=True):
                report += f"- {issue}: {count} 次\n"

        if check_result['warning_types']:
            report += "\n主要警告:\n"
            for warning, count in sorted(check_result['warning_types'].items(),
                                        key=lambda x: x[1], reverse=True)[:5]:
                report += f"- {warning}: {count} 次\n"

        return report
