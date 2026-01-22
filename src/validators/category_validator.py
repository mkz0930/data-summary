"""
AI分类校验器模块
使用Claude API验证产品分类的准确性和相关性
"""

import time
from typing import List, Dict, Any, Optional
from anthropic import Anthropic

from src.database.models import Product, CategoryValidation
from src.utils.logger import get_logger
from src.utils.retry import retry


class CategoryValidator:
    """AI分类校验器"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", db_manager=None):
        """
        初始化分类校验器

        Args:
            api_key: Anthropic API密钥
            model: 使用的模型名称
            db_manager: 数据库管理器（用于检查已验证的ASIN）
        """
        self.logger = get_logger()
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.rate_limit_delay = 0.5  # API调用间隔（秒）
        self.db_manager = db_manager
        self.validated_asins = set()  # 缓存已验证的ASIN

        # 如果提供了数据库管理器，加载已验证的ASIN
        if self.db_manager:
            self.validated_asins = self.db_manager.get_validated_asins()
            if self.validated_asins:
                self.logger.info(f"已加载 {len(self.validated_asins)} 个已验证的ASIN")

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def validate_product(
        self,
        product: Product,
        keyword: str,
        custom_categories: Optional[List[str]] = None
    ) -> CategoryValidation:
        """
        验证单个产品的分类

        Args:
            product: 产品对象
            keyword: 搜索关键词
            custom_categories: 自定义分类列表（如：家庭露营、背包徒步等）

        Returns:
            CategoryValidation对象
        """
        self.logger.info(f"验证产品分类: {product.asin}")

        # 构建提示词
        prompt = self._build_validation_prompt(product, keyword, custom_categories)

        # 调用Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # 解析响应
            result = self._parse_response(response.content[0].text, product.asin)

            # API限流延迟
            time.sleep(self.rate_limit_delay)

            return result

        except Exception as e:
            self.logger.error(f"API调用失败: {e}")
            # 返回默认结果
            return CategoryValidation(
                asin=product.asin,
                is_relevant=True,
                category_is_correct=True,
                validation_reason=f"API调用失败: {str(e)}"
            )

    def validate_batch(
        self,
        products: List[Product],
        keyword: str,
        custom_categories: Optional[List[str]] = None,
        skip_validated: bool = True
    ) -> List[CategoryValidation]:
        """
        批量验证产品分类

        Args:
            products: 产品列表
            keyword: 搜索关键词
            custom_categories: 自定义分类列表
            skip_validated: 是否跳过已验证的产品（默认True）

        Returns:
            CategoryValidation对象列表
        """
        self.logger.info(f"开始批量验证 {len(products)} 个产品")

        # 过滤已验证的产品
        if skip_validated and self.db_manager:
            products_to_validate = []
            skipped_count = 0

            for product in products:
                if product.asin in self.validated_asins:
                    skipped_count += 1
                    self.logger.debug(f"跳过已验证的产品: {product.asin}")
                else:
                    products_to_validate.append(product)

            if skipped_count > 0:
                self.logger.info(f"跳过 {skipped_count} 个已验证的产品，剩余 {len(products_to_validate)} 个待验证")

            products = products_to_validate

        if not products:
            self.logger.info("所有产品均已验证，无需重复验证")
            return []

        results = []
        for i, product in enumerate(products, 1):
            self.logger.info(f"进度: {i}/{len(products)}")
            result = self.validate_product(product, keyword, custom_categories)
            results.append(result)

            # 将新验证的ASIN添加到缓存
            self.validated_asins.add(product.asin)

        # 统计结果
        relevant_count = sum(1 for r in results if r.is_relevant)
        correct_count = sum(1 for r in results if r.category_is_correct)

        self.logger.info(f"验证完成: 相关产品 {relevant_count}/{len(products)}, "
                        f"分类正确 {correct_count}/{len(products)}")

        return results

    def _build_validation_prompt(
        self,
        product: Product,
        keyword: str,
        custom_categories: Optional[List[str]] = None
    ) -> str:
        """构建验证提示词"""

        custom_cat_text = ""
        if custom_categories:
            custom_cat_text = f"\n自定义分类选项: {', '.join(custom_categories)}"

        prompt = f"""你是一个产品分类专家。请分析以下产品是否与搜索关键词"{keyword}"相关，以及其分类是否准确。

产品信息：
- ASIN: {product.asin}
- 标题: {product.name}
- 品牌: {product.brand or '未知'}
- 当前分类: {product.category or '未知'}
- 价格: ${product.price or '未知'}
- 特性: {product.feature_bullets or '无'}
{custom_cat_text}

请按以下格式回答（每行一个字段）：
1. 是否相关（YES/NO）: 该产品是否与关键词"{keyword}"相关？
2. 分类是否正确（YES/NO）: 当前分类是否准确描述了该产品？
3. 建议分类: 如果分类不正确，建议的分类是什么？（如果正确则写"无"）
4. 原因: 简要说明你的判断理由（50字以内）

示例回答格式：
1. YES
2. NO
3. Camping Tents
4. 该产品是露营帐篷，应归类为Camping Tents而非Outdoor Recreation
"""

        return prompt

    def _parse_response(self, response_text: str, asin: str) -> CategoryValidation:
        """解析API响应"""

        lines = [line.strip() for line in response_text.strip().split('\n') if line.strip()]

        # 默认值
        is_relevant = True
        category_is_correct = True
        suggested_category = None
        validation_reason = "解析失败"

        try:
            # 解析每一行
            for line in lines:
                if line.startswith('1.'):
                    is_relevant = 'YES' in line.upper()
                elif line.startswith('2.'):
                    category_is_correct = 'YES' in line.upper()
                elif line.startswith('3.'):
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        suggested = parts[1].strip()
                        if suggested and suggested.lower() not in ['无', 'none', 'n/a']:
                            suggested_category = suggested
                elif line.startswith('4.'):
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        validation_reason = parts[1].strip()

        except Exception as e:
            self.logger.error(f"解析响应失败: {e}")
            validation_reason = f"解析错误: {str(e)}"

        return CategoryValidation(
            asin=asin,
            is_relevant=is_relevant,
            category_is_correct=category_is_correct,
            suggested_category=suggested_category,
            validation_reason=validation_reason
        )

    def get_irrelevant_products(
        self,
        validations: List[CategoryValidation]
    ) -> List[str]:
        """
        获取不相关产品的ASIN列表

        Args:
            validations: 验证结果列表

        Returns:
            不相关产品的ASIN列表
        """
        return [v.asin for v in validations if not v.is_relevant]

    def get_miscategorized_products(
        self,
        validations: List[CategoryValidation]
    ) -> List[CategoryValidation]:
        """
        获取分类错误的产品

        Args:
            validations: 验证结果列表

        Returns:
            分类错误的产品列表
        """
        return [v for v in validations if not v.category_is_correct]

    def get_statistics(
        self,
        validations: List[CategoryValidation]
    ) -> Dict[str, Any]:
        """
        获取验证统计信息

        Args:
            validations: 验证结果列表

        Returns:
            统计信息字典
        """
        total = len(validations)
        relevant = sum(1 for v in validations if v.is_relevant)
        correct = sum(1 for v in validations if v.category_is_correct)

        return {
            'total': total,
            'relevant': relevant,
            'irrelevant': total - relevant,
            'correct_category': correct,
            'incorrect_category': total - correct,
            'relevant_rate': relevant / total if total > 0 else 0,
            'correct_rate': correct / total if total > 0 else 0
        }
