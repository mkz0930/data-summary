"""
关键词分析器模块
分析关键词扩展机会、长尾关键词等
"""

import json
from typing import List, Dict, Any, Optional

from src.database.models import SellerSpiritData
from src.utils.logger import get_logger


class KeywordAnalyzer:
    """关键词分析器"""

    def __init__(self):
        """初始化关键词分析器"""
        self.logger = get_logger()

    def analyze(
        self,
        sellerspirit_data: Optional[SellerSpiritData] = None,
        main_keyword: str = ""
    ) -> Dict[str, Any]:
        """
        综合关键词分析

        Args:
            sellerspirit_data: 卖家精灵数据
            main_keyword: 主关键词

        Returns:
            关键词分析结果
        """
        self.logger.info(f"开始关键词分析: {main_keyword}")

        if not sellerspirit_data:
            self.logger.warning("缺少卖家精灵数据，无法进行关键词分析")
            return {
                'main_keyword': main_keyword,
                'monthly_searches': 0,
                'extensions': [],
                'long_tail_opportunities': [],
                'total_extensions': 0
            }

        # 解析关键词扩展数据
        extensions = self._parse_keyword_extensions(sellerspirit_data)

        # 识别长尾关键词机会
        long_tail = self._identify_long_tail_opportunities(extensions)

        # 关键词分类
        categorized = self._categorize_keywords(extensions)

        result = {
            'main_keyword': main_keyword,
            'monthly_searches': sellerspirit_data.monthly_searches,
            'extensions': extensions,
            'long_tail_opportunities': long_tail,
            'categorized_keywords': categorized,
            'total_extensions': len(extensions)
        }

        self.logger.info(f"关键词分析完成，发现 {len(extensions)} 个扩展关键词")
        return result

    def _parse_keyword_extensions(
        self,
        sellerspirit_data: SellerSpiritData
    ) -> List[Dict[str, Any]]:
        """
        解析关键词扩展数据

        Args:
            sellerspirit_data: 卖家精灵数据

        Returns:
            关键词扩展列表
        """
        if not sellerspirit_data.keyword_extensions:
            return []

        try:
            # 假设keyword_extensions是JSON格式的字符串
            extensions_data = json.loads(sellerspirit_data.keyword_extensions)

            # 如果是列表格式
            if isinstance(extensions_data, list):
                return extensions_data

            # 如果是字典格式
            elif isinstance(extensions_data, dict):
                return [extensions_data]

            else:
                self.logger.warning(f"未知的关键词扩展数据格式: {type(extensions_data)}")
                return []

        except json.JSONDecodeError as e:
            self.logger.error(f"解析关键词扩展数据失败: {e}")
            return []

    def _identify_long_tail_opportunities(
        self,
        extensions: List[Dict[str, Any]],
        min_searches: int = 1000,
        max_products: int = 50
    ) -> List[Dict[str, Any]]:
        """
        识别长尾关键词机会

        定义：搜索量 > min_searches 且 竞品数 < max_products

        Args:
            extensions: 关键词扩展列表
            min_searches: 最小搜索量
            max_products: 最大竞品数

        Returns:
            长尾关键词机会列表
        """
        opportunities = []

        for ext in extensions:
            searches = ext.get('searches', 0) or ext.get('monthly_searches', 0)
            products = ext.get('products', 0) or ext.get('asin_count', 0)

            if searches >= min_searches and products <= max_products:
                # 计算机会指数
                opportunity_index = searches / products if products > 0 else searches

                opportunities.append({
                    'keyword': ext.get('keyword', ''),
                    'searches': searches,
                    'products': products,
                    'opportunity_index': round(opportunity_index, 2)
                })

        # 按机会指数排序
        opportunities.sort(key=lambda x: x['opportunity_index'], reverse=True)

        return opportunities

    def _categorize_keywords(
        self,
        extensions: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        关键词分类

        Args:
            extensions: 关键词扩展列表

        Returns:
            分类后的关键词字典
        """
        categorized = {
            'high_volume': [],      # 高搜索量 (>10000)
            'medium_volume': [],    # 中搜索量 (1000-10000)
            'low_volume': [],       # 低搜索量 (<1000)
            'low_competition': [],  # 低竞争 (<50产品)
            'high_competition': []  # 高竞争 (>200产品)
        }

        for ext in extensions:
            searches = ext.get('searches', 0) or ext.get('monthly_searches', 0)
            products = ext.get('products', 0) or ext.get('asin_count', 0)
            keyword = ext.get('keyword', '')

            item = {
                'keyword': keyword,
                'searches': searches,
                'products': products
            }

            # 按搜索量分类
            if searches > 10000:
                categorized['high_volume'].append(item)
            elif searches > 1000:
                categorized['medium_volume'].append(item)
            else:
                categorized['low_volume'].append(item)

            # 按竞争度分类
            if products < 50:
                categorized['low_competition'].append(item)
            elif products > 200:
                categorized['high_competition'].append(item)

        return categorized

    def get_recommended_keywords(
        self,
        analysis_result: Dict[str, Any],
        limit: int = 10
    ) -> List[str]:
        """
        获取推荐关键词列表

        Args:
            analysis_result: 关键词分析结果
            limit: 返回数量限制

        Returns:
            推荐关键词列表
        """
        # 优先推荐长尾机会关键词
        long_tail = analysis_result.get('long_tail_opportunities', [])

        recommended = [kw['keyword'] for kw in long_tail[:limit]]

        # 如果长尾关键词不足，补充中等搜索量的关键词
        if len(recommended) < limit:
            categorized = analysis_result.get('categorized_keywords', {})
            medium_volume = categorized.get('medium_volume', [])

            for kw in medium_volume:
                if kw['keyword'] not in recommended:
                    recommended.append(kw['keyword'])
                    if len(recommended) >= limit:
                        break

        return recommended

    def get_keyword_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成关键词分析摘要

        Args:
            analysis_result: 关键词分析结果

        Returns:
            摘要文本
        """
        main_keyword = analysis_result.get('main_keyword', '')
        monthly_searches = analysis_result.get('monthly_searches', 0)
        total_extensions = analysis_result.get('total_extensions', 0)
        long_tail = analysis_result.get('long_tail_opportunities', [])
        categorized = analysis_result.get('categorized_keywords', {})

        summary = f"""
关键词分析摘要
{'=' * 50}

主关键词: {main_keyword}
月搜索量: {monthly_searches}
扩展关键词数: {total_extensions}

长尾关键词机会: {len(long_tail)} 个
"""

        if long_tail:
            summary += "\nTop 5 长尾机会:\n"
            for i, kw in enumerate(long_tail[:5], 1):
                summary += f"{i}. {kw['keyword']} (搜索量: {kw['searches']}, 竞品: {kw['products']}, 机会指数: {kw['opportunity_index']})\n"

        summary += f"""
关键词分类:
- 高搜索量 (>10000): {len(categorized.get('high_volume', []))} 个
- 中搜索量 (1000-10000): {len(categorized.get('medium_volume', []))} 个
- 低搜索量 (<1000): {len(categorized.get('low_volume', []))} 个
- 低竞争 (<50产品): {len(categorized.get('low_competition', []))} 个
- 高竞争 (>200产品): {len(categorized.get('high_competition', []))} 个
"""

        return summary
