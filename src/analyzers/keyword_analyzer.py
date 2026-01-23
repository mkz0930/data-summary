"""
关键词分析器模块
分析关键词扩展机会、长尾关键词等
继承 BaseAnalyzer 基类
"""

import json
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict

from src.database.models import SellerSpiritData, Product
from src.analyzers.base_analyzer import BaseAnalyzer


class KeywordAnalyzer(BaseAnalyzer):
    """
    关键词分析器

    继承 BaseAnalyzer，提供关键词扩展、长尾关键词识别等功能。
    """

    def __init__(self):
        """初始化关键词分析器"""
        super().__init__(name="KeywordAnalyzer")

    def analyze(
        self,
        products: List[Product] = None,
        sellerspirit_data: Optional[SellerSpiritData] = None,
        main_keyword: str = ""
    ) -> Dict[str, Any]:
        """
        综合关键词分析

        Args:
            products: 产品列表（可选，用于兼容基类接口）
            sellerspirit_data: 卖家精灵数据
            main_keyword: 主关键词

        Returns:
            关键词分析结果
        """
        self.log_info(f"开始关键词分析: {main_keyword}")

        if not sellerspirit_data:
            self.log_warning("缺少卖家精灵数据，无法进行关键词分析")
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

        # 关键词竞争力评分
        scored_keywords = self._score_keywords(extensions)

        # 关键词机会矩阵
        opportunity_matrix = self._create_opportunity_matrix(extensions)

        # 关键词难度评估
        difficulty_analysis = self._analyze_keyword_difficulty(extensions)

        # 关键词聚类分析
        keyword_clusters = self._cluster_keywords(extensions)

        # 品牌 vs 通用关键词分析
        brand_analysis = self._analyze_brand_keywords(extensions, main_keyword)

        # 关键词组合建议
        combination_suggestions = self._suggest_keyword_combinations(extensions)

        result = {
            'main_keyword': main_keyword,
            'monthly_searches': sellerspirit_data.monthly_searches,
            'extensions': extensions,
            'long_tail_opportunities': long_tail,
            'categorized_keywords': categorized,
            'scored_keywords': scored_keywords,
            'opportunity_matrix': opportunity_matrix,
            'difficulty_analysis': difficulty_analysis,
            'keyword_clusters': keyword_clusters,
            'brand_analysis': brand_analysis,
            'combination_suggestions': combination_suggestions,
            'total_extensions': len(extensions)
        }

        self.log_info(f"关键词分析完成，发现 {len(extensions)} 个扩展关键词")
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
                # 检查列表元素类型
                if extensions_data and isinstance(extensions_data[0], str):
                    # 如果是字符串列表（商品标题），转换为字典格式
                    self.log_info("检测到字符串格式的关键词扩展，转换为字典格式")
                    return [{'keyword': title, 'searches': 0, 'products': 0} for title in extensions_data]
                elif extensions_data and isinstance(extensions_data[0], dict):
                    # 如果已经是字典列表，直接返回
                    return extensions_data
                else:
                    self.log_warning(f"未知的列表元素类型: {type(extensions_data[0]) if extensions_data else 'empty'}")
                    return []

            # 如果是字典格式
            elif isinstance(extensions_data, dict):
                return [extensions_data]

            else:
                self.log_warning(f"未知的关键词扩展数据格式: {type(extensions_data)}")
                return []

        except json.JSONDecodeError as e:
            self.log_error(f"解析关键词扩展数据失败: {e}")
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

    def _score_keywords(
        self,
        extensions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        对关键词进行竞争力评分

        评分维度：
        1. 搜索量（40分）
        2. 竞争度（30分）- 竞争越低分数越高
        3. 机会指数（30分）

        Args:
            extensions: 关键词扩展列表

        Returns:
            评分后的关键词列表
        """
        scored = []

        for ext in extensions:
            searches = ext.get('searches', 0) or ext.get('monthly_searches', 0)
            products = ext.get('products', 0) or ext.get('asin_count', 0)
            keyword = ext.get('keyword', '')

            # 搜索量评分（40分）
            if searches >= 10000:
                search_score = 40
            elif searches >= 5000:
                search_score = 35
            elif searches >= 1000:
                search_score = 30
            elif searches >= 500:
                search_score = 20
            else:
                search_score = 10

            # 竞争度评分（30分）- 竞争越低分数越高
            if products < 20:
                competition_score = 30
            elif products < 50:
                competition_score = 25
            elif products < 100:
                competition_score = 20
            elif products < 200:
                competition_score = 15
            else:
                competition_score = 10

            # 机会指数评分（30分）
            opportunity_index = searches / products if products > 0 else searches
            if opportunity_index >= 200:
                opportunity_score = 30
            elif opportunity_index >= 100:
                opportunity_score = 25
            elif opportunity_index >= 50:
                opportunity_score = 20
            elif opportunity_index >= 20:
                opportunity_score = 15
            else:
                opportunity_score = 10

            # 总分
            total_score = search_score + competition_score + opportunity_score

            # 评级
            if total_score >= 85:
                grade = 'A+'
            elif total_score >= 75:
                grade = 'A'
            elif total_score >= 65:
                grade = 'B+'
            elif total_score >= 55:
                grade = 'B'
            elif total_score >= 45:
                grade = 'C'
            else:
                grade = 'D'

            scored.append({
                'keyword': keyword,
                'searches': searches,
                'products': products,
                'opportunity_index': round(opportunity_index, 2),
                'total_score': total_score,
                'grade': grade,
                'score_breakdown': {
                    'search_score': search_score,
                    'competition_score': competition_score,
                    'opportunity_score': opportunity_score
                }
            })

        # 按总分排序
        scored.sort(key=lambda x: x['total_score'], reverse=True)

        return scored

    def _create_opportunity_matrix(
        self,
        extensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        创建关键词机会矩阵（搜索量 vs 竞争度）

        矩阵分为9个象限：
        - 高搜索量 + 低竞争 = 黄金机会
        - 高搜索量 + 中竞争 = 潜力机会
        - 高搜索量 + 高竞争 = 红海市场
        - 中搜索量 + 低竞争 = 蓝海机会
        - 中搜索量 + 中竞争 = 平衡市场
        - 中搜索量 + 高竞争 = 竞争激烈
        - 低搜索量 + 低竞争 = 小众市场
        - 低搜索量 + 中竞争 = 边缘市场
        - 低搜索量 + 高竞争 = 避免进入

        Args:
            extensions: 关键词扩展列表

        Returns:
            机会矩阵
        """
        matrix = {
            'golden_opportunity': [],      # 黄金机会
            'potential_opportunity': [],   # 潜力机会
            'red_ocean': [],               # 红海市场
            'blue_ocean': [],              # 蓝海机会
            'balanced_market': [],         # 平衡市场
            'high_competition': [],        # 竞争激烈
            'niche_market': [],            # 小众市场
            'edge_market': [],             # 边缘市场
            'avoid': []                    # 避免进入
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

            # 搜索量分类
            if searches >= 5000:
                search_level = 'high'
            elif searches >= 1000:
                search_level = 'medium'
            else:
                search_level = 'low'

            # 竞争度分类
            if products < 50:
                competition_level = 'low'
            elif products < 150:
                competition_level = 'medium'
            else:
                competition_level = 'high'

            # 分配到矩阵
            if search_level == 'high' and competition_level == 'low':
                matrix['golden_opportunity'].append(item)
            elif search_level == 'high' and competition_level == 'medium':
                matrix['potential_opportunity'].append(item)
            elif search_level == 'high' and competition_level == 'high':
                matrix['red_ocean'].append(item)
            elif search_level == 'medium' and competition_level == 'low':
                matrix['blue_ocean'].append(item)
            elif search_level == 'medium' and competition_level == 'medium':
                matrix['balanced_market'].append(item)
            elif search_level == 'medium' and competition_level == 'high':
                matrix['high_competition'].append(item)
            elif search_level == 'low' and competition_level == 'low':
                matrix['niche_market'].append(item)
            elif search_level == 'low' and competition_level == 'medium':
                matrix['edge_market'].append(item)
            else:
                matrix['avoid'].append(item)

        return matrix

    def _analyze_keyword_difficulty(
        self,
        extensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析关键词难度

        难度评估基于：
        1. 竞品数量
        2. 搜索量与竞品比例
        3. 关键词长度（长尾词通常更容易）

        Args:
            extensions: 关键词扩展列表

        Returns:
            难度分析结果
        """
        difficulty_levels = {
            'very_easy': [],    # 非常容易
            'easy': [],         # 容易
            'medium': [],       # 中等
            'hard': [],         # 困难
            'very_hard': []     # 非常困难
        }

        for ext in extensions:
            searches = ext.get('searches', 0) or ext.get('monthly_searches', 0)
            products = ext.get('products', 0) or ext.get('asin_count', 0)
            keyword = ext.get('keyword', '')

            # 计算难度分数（0-100，越高越难）
            difficulty_score = 0

            # 竞品数量因素（50分）
            if products > 200:
                difficulty_score += 50
            elif products > 100:
                difficulty_score += 40
            elif products > 50:
                difficulty_score += 30
            elif products > 20:
                difficulty_score += 20
            else:
                difficulty_score += 10

            # 搜索量与竞品比例因素（30分）
            ratio = searches / products if products > 0 else searches
            if ratio < 20:
                difficulty_score += 30
            elif ratio < 50:
                difficulty_score += 20
            elif ratio < 100:
                difficulty_score += 10
            else:
                difficulty_score += 5

            # 关键词长度因素（20分）- 长尾词更容易
            word_count = len(keyword.split())
            if word_count <= 2:
                difficulty_score += 20
            elif word_count <= 3:
                difficulty_score += 15
            elif word_count <= 4:
                difficulty_score += 10
            else:
                difficulty_score += 5

            # 分类
            item = {
                'keyword': keyword,
                'searches': searches,
                'products': products,
                'difficulty_score': difficulty_score
            }

            if difficulty_score >= 80:
                difficulty_levels['very_hard'].append(item)
            elif difficulty_score >= 60:
                difficulty_levels['hard'].append(item)
            elif difficulty_score >= 40:
                difficulty_levels['medium'].append(item)
            elif difficulty_score >= 20:
                difficulty_levels['easy'].append(item)
            else:
                difficulty_levels['very_easy'].append(item)

        return difficulty_levels

    def _cluster_keywords(
        self,
        extensions: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        关键词聚类分析

        基于关键词中的共同词汇进行聚类

        Args:
            extensions: 关键词扩展列表

        Returns:
            关键词聚类结果
        """
        # 提取所有关键词
        keywords = [ext.get('keyword', '') for ext in extensions if ext.get('keyword')]

        # 统计词频
        word_freq = defaultdict(int)
        for keyword in keywords:
            words = keyword.lower().split()
            for word in words:
                # 过滤停用词和短词
                if len(word) > 2 and word not in ['the', 'and', 'for', 'with']:
                    word_freq[word] += 1

        # 找出高频词（出现次数 >= 3）
        common_words = {word: freq for word, freq in word_freq.items() if freq >= 3}

        # 按高频词聚类
        clusters = {}
        for word, freq in sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:10]:
            cluster_keywords = [kw for kw in keywords if word in kw.lower()]
            if cluster_keywords:
                clusters[word] = cluster_keywords

        return clusters

    def _analyze_brand_keywords(
        self,
        extensions: List[Dict[str, Any]],
        main_keyword: str
    ) -> Dict[str, Any]:
        """
        分析品牌关键词 vs 通用关键词

        Args:
            extensions: 关键词扩展列表
            main_keyword: 主关键词

        Returns:
            品牌关键词分析结果
        """
        brand_keywords = []
        generic_keywords = []

        # 常见品牌词模式
        brand_patterns = [
            r'\b[A-Z][a-z]+\b',  # 首字母大写的词
            r'\b[A-Z]{2,}\b',    # 全大写的词
        ]

        for ext in extensions:
            keyword = ext.get('keyword', '')
            searches = ext.get('searches', 0) or ext.get('monthly_searches', 0)
            products = ext.get('products', 0) or ext.get('asin_count', 0)

            item = {
                'keyword': keyword,
                'searches': searches,
                'products': products
            }

            # 检查是否包含品牌词
            is_brand = False
            for pattern in brand_patterns:
                if re.search(pattern, keyword):
                    is_brand = True
                    break

            if is_brand:
                brand_keywords.append(item)
            else:
                generic_keywords.append(item)

        # 统计
        total_brand_searches = sum(kw['searches'] for kw in brand_keywords)
        total_generic_searches = sum(kw['searches'] for kw in generic_keywords)
        total_searches = total_brand_searches + total_generic_searches

        return {
            'brand_keywords': brand_keywords,
            'generic_keywords': generic_keywords,
            'brand_count': len(brand_keywords),
            'generic_count': len(generic_keywords),
            'brand_search_share': round(total_brand_searches / total_searches * 100, 2) if total_searches > 0 else 0,
            'generic_search_share': round(total_generic_searches / total_searches * 100, 2) if total_searches > 0 else 0
        }

    def _suggest_keyword_combinations(
        self,
        extensions: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        建议关键词组合

        基于高搜索量和低竞争的关键词，建议可能的组合

        Args:
            extensions: 关键词扩展列表
            limit: 返回数量限制

        Returns:
            关键词组合建议列表
        """
        suggestions = []

        # 找出高潜力关键词（搜索量 > 1000 且 竞品 < 100）
        high_potential = []
        for ext in extensions:
            searches = ext.get('searches', 0) or ext.get('monthly_searches', 0)
            products = ext.get('products', 0) or ext.get('asin_count', 0)
            keyword = ext.get('keyword', '')

            if searches > 1000 and products < 100:
                high_potential.append({
                    'keyword': keyword,
                    'searches': searches,
                    'products': products,
                    'words': set(keyword.lower().split())
                })

        # 寻找可组合的关键词
        for i, kw1 in enumerate(high_potential):
            for kw2 in high_potential[i+1:]:
                # 找出共同词汇
                common_words = kw1['words'] & kw2['words']
                unique_words = (kw1['words'] | kw2['words']) - common_words

                if common_words and unique_words:
                    # 建议组合
                    combined_searches = (kw1['searches'] + kw2['searches']) / 2
                    combined_products = (kw1['products'] + kw2['products']) / 2

                    suggestions.append({
                        'keyword1': kw1['keyword'],
                        'keyword2': kw2['keyword'],
                        'common_words': list(common_words),
                        'unique_words': list(unique_words),
                        'estimated_searches': round(combined_searches, 0),
                        'estimated_products': round(combined_products, 0),
                        'opportunity_score': round(combined_searches / combined_products, 2) if combined_products > 0 else 0
                    })

                if len(suggestions) >= limit:
                    break

            if len(suggestions) >= limit:
                break

        # 按机会分数排序
        suggestions.sort(key=lambda x: x['opportunity_score'], reverse=True)

        return suggestions[:limit]

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
        scored = analysis_result.get('scored_keywords', [])
        opportunity_matrix = analysis_result.get('opportunity_matrix', {})
        difficulty = analysis_result.get('difficulty_analysis', {})
        brand_analysis = analysis_result.get('brand_analysis', {})

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

关键词评分:
- A+级关键词: {len([k for k in scored if k.get('grade') == 'A+'])} 个
- A级关键词: {len([k for k in scored if k.get('grade') == 'A'])} 个
- B+级关键词: {len([k for k in scored if k.get('grade') == 'B+'])} 个

机会矩阵:
- 黄金机会: {len(opportunity_matrix.get('golden_opportunity', []))} 个
- 蓝海机会: {len(opportunity_matrix.get('blue_ocean', []))} 个
- 潜力机会: {len(opportunity_matrix.get('potential_opportunity', []))} 个

难度分析:
- 非常容易: {len(difficulty.get('very_easy', []))} 个
- 容易: {len(difficulty.get('easy', []))} 个
- 中等: {len(difficulty.get('medium', []))} 个
- 困难: {len(difficulty.get('hard', []))} 个

品牌关键词分析:
- 品牌关键词: {brand_analysis.get('brand_count', 0)} 个 ({brand_analysis.get('brand_search_share', 0)}% 搜索量)
- 通用关键词: {brand_analysis.get('generic_count', 0)} 个 ({brand_analysis.get('generic_search_share', 0)}% 搜索量)
"""

        return summary
