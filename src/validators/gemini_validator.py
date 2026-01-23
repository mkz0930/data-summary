"""
Gemini AI分类校验器模块
使用Google Gemini API验证产品分类的准确性和相关性
"""

import time
import csv
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from src.database.models import Product, CategoryValidation
from src.utils.logger import get_logger
from src.utils.retry import retry


class GeminiCategoryValidator:
    """Gemini AI分类校验器"""

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview", db_manager=None, csv_output_dir: Optional[Path] = None, max_concurrent: int = 1000, rate_limit_delay: float = 0.01):
        """
        初始化分类校验器

        Args:
            api_key: Google API密钥
            model: 使用的模型名称
            db_manager: 数据库管理器（用于检查已验证的ASIN）
            csv_output_dir: CSV输出目录（默认为data/validation_results）
            max_concurrent: 最大并发数（默认1000，Gemini-3-Flash支持高并发）
            rate_limit_delay: API调用间隔（秒，默认0.01秒）
        """
        self.logger = get_logger()
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        self.rate_limit_delay = rate_limit_delay  # API调用间隔（秒）
        self.max_concurrent = max_concurrent
        self.db_manager = db_manager
        self.validated_asins = set()  # 缓存已验证的ASIN

        # 动态并发控制参数
        self._current_concurrent = 1  # 从1开始
        self._consecutive_successes = 0  # 连续成功计数
        self._success_threshold = 5  # 连续成功多少次后增加并发
        self._concurrency_lock = None  # 异步锁，在运行时初始化

        # 设置CSV输出目录
        if csv_output_dir is None:
            csv_output_dir = Path("data/validation_results")
        self.csv_output_dir = Path(csv_output_dir)
        self.csv_output_dir.mkdir(parents=True, exist_ok=True)

        # 如果提供了数据库管理器，加载已验证的ASIN
        if self.db_manager:
            self.validated_asins = self.db_manager.get_validated_asins()
            if self.validated_asins:
                self.logger.info(f"[Gemini] 已加载 {len(self.validated_asins)} 个已验证的ASIN")

    async def _adjust_concurrency(self, success: bool, error_msg: str = ""):
        """
        动态调整并发数

        Args:
            success: 请求是否成功
            error_msg: 错误信息（用于判断是否为服务端错误）
        """
        if self._concurrency_lock is None:
            self._concurrency_lock = asyncio.Lock()

        async with self._concurrency_lock:
            if success:
                self._consecutive_successes += 1
                # 连续成功达到阈值，增加并发数
                if self._consecutive_successes >= self._success_threshold:
                    old_concurrent = self._current_concurrent
                    self._current_concurrent = min(self._current_concurrent + 1, self.max_concurrent)
                    if self._current_concurrent > old_concurrent:
                        self.logger.info(f"[Gemini] 并发数增加: {old_concurrent} -> {self._current_concurrent}")
                    self._consecutive_successes = 0
            else:
                # 检查是否为服务端错误 (503, 504, Internal Server Error)
                is_server_error = any(err in error_msg for err in ['503', '504', 'Internal Server Error', '超时', 'timeout', 'RESOURCE_EXHAUSTED'])
                if is_server_error:
                    self._consecutive_successes = 0
                    old_concurrent = self._current_concurrent
                    # 降低并发数，最低为1
                    self._current_concurrent = max(1, self._current_concurrent // 2)
                    if self._current_concurrent < old_concurrent:
                        self.logger.warning(f"[Gemini] 检测到服务端错误，并发数降低: {old_concurrent} -> {self._current_concurrent}")

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    async def validate_product_async(
        self,
        product: Product,
        keyword: str,
        custom_categories: Optional[List[str]] = None
    ) -> Optional[CategoryValidation]:
        """
        异步验证单个产品的分类

        Args:
            product: 产品对象
            keyword: 搜索关键词
            custom_categories: 自定义分类列表（如：家庭露营、背包徒步等）

        Returns:
            CategoryValidation对象，API调用失败时返回None（不入库）
        """
        self.logger.debug(f"[Gemini] 验证产品分类: {product.asin}")

        # 构建提示词
        prompt = self._build_validation_prompt(product, keyword, custom_categories)

        # 调用Gemini API（注意：Gemini SDK可能不支持原生async，需要在线程池中运行）
        try:
            # 在线程池中运行同步API调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            )

            # 解析响应
            result = self._parse_response(response.text, product.asin)

            # 标记成功，调整并发数
            await self._adjust_concurrency(success=True)

            # API限流延迟（仅在设置了延迟时才等待）
            if self.rate_limit_delay > 0:
                await asyncio.sleep(self.rate_limit_delay)

            return result

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"[Gemini] API调用失败: {error_msg}")
            # 标记失败，调整并发数
            await self._adjust_concurrency(success=False, error_msg=error_msg)
            # API调用失败返回None，不入库
            return None

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def validate_product(
        self,
        product: Product,
        keyword: str,
        custom_categories: Optional[List[str]] = None
    ) -> Optional[CategoryValidation]:
        """
        验证单个产品的分类（同步版本，保持向后兼容）

        Args:
            product: 产品对象
            keyword: 搜索关键词
            custom_categories: 自定义分类列表（如：家庭露营、背包徒步等）

        Returns:
            CategoryValidation对象，API调用失败时返回None（不入库）
        """
        self.logger.info(f"[Gemini] 验证产品分类: {product.asin}")

        # 构建提示词
        prompt = self._build_validation_prompt(product, keyword, custom_categories)

        # 调用Gemini API
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )

            # 解析响应
            result = self._parse_response(response.text, product.asin)

            # API限流延迟（仅在设置了延迟时才等待）
            if self.rate_limit_delay > 0:
                time.sleep(self.rate_limit_delay)

            return result

        except Exception as e:
            self.logger.error(f"[Gemini] API调用失败: {e}")
            # API调用失败返回None，不入库
            return None

    async def validate_batch_async(
        self,
        products: List[Product],
        keyword: str,
        custom_categories: Optional[List[str]] = None,
        skip_validated: bool = True
    ) -> List[CategoryValidation]:
        """
        异步批量验证产品分类（使用动态并发）

        Args:
            products: 产品列表
            keyword: 搜索关键词
            custom_categories: 自定义分类列表
            skip_validated: 是否跳过已验证的产品（默认True）

        Returns:
            CategoryValidation对象列表
        """
        # 重置动态并发控制状态
        self._current_concurrent = 1
        self._consecutive_successes = 0
        self._concurrency_lock = asyncio.Lock()

        self.logger.info(f"[Gemini] 开始异步批量验证 {len(products)} 个产品 (初始并发数: 1, 最大并发数: {self.max_concurrent})")

        # 过滤已验证的产品
        if skip_validated and self.db_manager:
            products_to_validate = []
            skipped_count = 0

            for product in products:
                if product.asin in self.validated_asins:
                    skipped_count += 1
                    self.logger.debug(f"[Gemini] 跳过已验证的产品: {product.asin}")
                else:
                    products_to_validate.append(product)

            if skipped_count > 0:
                self.logger.info(f"[Gemini] 跳过 {skipped_count} 个已验证的产品，剩余 {len(products_to_validate)} 个待验证")

            products = products_to_validate

        if not products:
            self.logger.info("[Gemini] 所有产品均已验证，无需重复验证")
            return []

        # 使用动态并发控制
        results = []
        pending_indices = list(range(len(products)))
        active_tasks = {}  # task -> index

        while pending_indices or active_tasks:
            # 启动新任务，直到达到当前并发限制
            while pending_indices and len(active_tasks) < self._current_concurrent:
                idx = pending_indices.pop(0)
                product = products[idx]
                self.logger.info(f"[Gemini] 进度: {idx + 1}/{len(products)} - {product.asin} (并发: {len(active_tasks) + 1}/{self._current_concurrent})")
                task = asyncio.create_task(self.validate_product_async(product, keyword, custom_categories))
                active_tasks[task] = idx

            if not active_tasks:
                break

            # 等待任意一个任务完成
            done, _ = await asyncio.wait(active_tasks.keys(), return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                idx = active_tasks.pop(task)
                try:
                    result = task.result()
                    # 只保存成功的结果（非None）
                    if result is not None:
                        results.append((idx, result))
                        # 将新验证的ASIN添加到缓存
                        self.validated_asins.add(products[idx].asin)
                    else:
                        self.logger.warning(f"[Gemini] 产品 {products[idx].asin} 验证失败，不入库")
                except Exception as e:
                    self.logger.error(f"[Gemini] 验证产品 {products[idx].asin} 时发生异常: {e}")

        # 按原始顺序排序结果
        results.sort(key=lambda x: x[0])
        valid_results = [r[1] for r in results]

        # 统计结果
        failed_count = len(products) - len(valid_results)
        relevant_count = sum(1 for r in valid_results if r.is_relevant)
        correct_count = sum(1 for r in valid_results if r.category_is_correct)

        self.logger.info(f"[Gemini] 验证完成: 成功 {len(valid_results)}/{len(products)}, 失败 {failed_count}, "
                        f"相关产品 {relevant_count}/{len(valid_results)}, "
                        f"分类正确 {correct_count}/{len(valid_results)}")

        return valid_results

    def validate_batch(
        self,
        products: List[Product],
        keyword: str,
        custom_categories: Optional[List[str]] = None,
        skip_validated: bool = True,
        use_async: bool = True
    ) -> List[CategoryValidation]:
        """
        批量验证产品分类

        Args:
            products: 产品列表
            keyword: 搜索关键词
            custom_categories: 自定义分类列表
            skip_validated: 是否跳过已验证的产品（默认True）
            use_async: 是否使用异步并发（默认True）

        Returns:
            CategoryValidation对象列表
        """
        if use_async:
            # 使用异步并发版本
            return asyncio.run(self.validate_batch_async(products, keyword, custom_categories, skip_validated))

        # 使用原有的同步顺序版本
        self.logger.info(f"[Gemini] 开始批量验证 {len(products)} 个产品")

        # 过滤已验证的产品
        if skip_validated and self.db_manager:
            products_to_validate = []
            skipped_count = 0

            for product in products:
                if product.asin in self.validated_asins:
                    skipped_count += 1
                    self.logger.debug(f"[Gemini] 跳过已验证的产品: {product.asin}")
                else:
                    products_to_validate.append(product)

            if skipped_count > 0:
                self.logger.info(f"[Gemini] 跳过 {skipped_count} 个已验证的产品，剩余 {len(products_to_validate)} 个待验证")

            products = products_to_validate

        if not products:
            self.logger.info("[Gemini] 所有产品均已验证，无需重复验证")
            return []

        results = []
        failed_count = 0
        for i, product in enumerate(products, 1):
            self.logger.info(f"[Gemini] 进度: {i}/{len(products)}")
            result = self.validate_product(product, keyword, custom_categories)

            # 只保存成功的结果（非None）
            if result is not None:
                results.append(result)
                # 将新验证的ASIN添加到缓存
                self.validated_asins.add(product.asin)
            else:
                failed_count += 1
                self.logger.warning(f"[Gemini] 产品 {product.asin} 验证失败，不入库")

        # 统计结果
        relevant_count = sum(1 for r in results if r.is_relevant)
        correct_count = sum(1 for r in results if r.category_is_correct)

        self.logger.info(f"[Gemini] 验证完成: 成功 {len(results)}/{len(products)}, 失败 {failed_count}, "
                        f"相关产品 {relevant_count}/{len(results)}, "
                        f"分类正确 {correct_count}/{len(results)}")

        return results

    def save_results_to_csv(
        self,
        results: List[CategoryValidation],
        products: List[Product],
        keyword: str,
        filename: Optional[str] = None
    ) -> Path:
        """
        将验证结果保存到CSV文件

        Args:
            results: 验证结果列表
            products: 产品列表
            keyword: 搜索关键词
            filename: 自定义文件名（可选）

        Returns:
            CSV文件路径
        """
        if not results:
            self.logger.warning("[Gemini] 没有验证结果可保存")
            return None

        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_{keyword}_{timestamp}.csv"

        csv_path = self.csv_output_dir / filename

        # 创建产品ASIN到产品对象的映射
        product_map = {p.asin: p for p in products}

        # 写入CSV
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # 写入表头
                writer.writerow([
                    'ASIN',
                    '产品名称',
                    '品牌',
                    '当前分类',
                    '价格',
                    '是否相关',
                    '分类是否正确',
                    '建议分类',
                    '验证原因',
                    '验证时间'
                ])

                # 写入数据
                for result in results:
                    product = product_map.get(result.asin)
                    if product:
                        writer.writerow([
                            result.asin,
                            product.name,
                            product.brand or '',
                            product.category or '',
                            product.price or '',
                            '是' if result.is_relevant else '否',
                            '是' if result.category_is_correct else '否',
                            result.suggested_category or '',
                            result.validation_reason or '',
                            result.validated_at.strftime("%Y-%m-%d %H:%M:%S") if result.validated_at else ''
                        ])

            self.logger.info(f"[Gemini] 验证结果已保存到CSV: {csv_path}")
            return csv_path

        except Exception as e:
            self.logger.error(f"[Gemini] 保存CSV失败: {e}")
            return None

    def validate_and_save(
        self,
        products: List[Product],
        keyword: str,
        custom_categories: Optional[List[str]] = None,
        skip_validated: bool = True,
        save_to_db: bool = True,
        save_to_csv: bool = True
    ) -> tuple[List[CategoryValidation], Optional[Path]]:
        """
        验证产品并保存结果到数据库和CSV

        Args:
            products: 产品列表
            keyword: 搜索关键词
            custom_categories: 自定义分类列表
            skip_validated: 是否跳过已验证的产品
            save_to_db: 是否保存到数据库
            save_to_csv: 是否保存到CSV

        Returns:
            (验证结果列表, CSV文件路径)
        """
        # 批量验证
        results = self.validate_batch(products, keyword, custom_categories, skip_validated)

        if not results:
            self.logger.info("[Gemini] 没有新的验证结果")
            return results, None

        # 保存到数据库
        if save_to_db and self.db_manager:
            try:
                self.db_manager.save_category_validations(results)
                self.logger.info(f"[Gemini] 已保存 {len(results)} 条验证结果到数据库")
            except Exception as e:
                self.logger.error(f"[Gemini] 保存到数据库失败: {e}")

        # 保存到CSV
        csv_path = None
        if save_to_csv:
            csv_path = self.save_results_to_csv(results, products, keyword)

        return results, csv_path

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
            self.logger.error(f"[Gemini] 解析响应失败: {e}")
            validation_reason = f"解析错误: {str(e)}"

        return CategoryValidation(
            asin=asin,
            is_relevant=is_relevant,
            category_is_correct=category_is_correct,
            suggested_category=suggested_category,
            validation_reason=validation_reason,
            validated_at=datetime.now()
        )

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
