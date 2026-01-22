"""
模型对比分析器
比较Claude和Gemini两个模型的分类验证结果
"""

from typing import List, Dict, Any, Tuple
from src.database.models import CategoryValidation
from src.utils.logger import get_logger


class ModelComparator:
    """模型对比分析器"""

    def __init__(self):
        """初始化对比分析器"""
        self.logger = get_logger()

    def compare_validations(
        self,
        claude_validations: List[CategoryValidation],
        gemini_validations: List[CategoryValidation]
    ) -> Dict[str, Any]:
        """
        对比两个模型的验证结果

        Args:
            claude_validations: Claude验证结果列表
            gemini_validations: Gemini验证结果列表

        Returns:
            对比分析结果字典
        """
        self.logger.info("开始对比两个模型的验证结果")

        # 构建ASIN到验证结果的映射
        claude_map = {v.asin: v for v in claude_validations}
        gemini_map = {v.asin: v for v in gemini_validations}

        # 找出共同的ASIN
        common_asins = set(claude_map.keys()) & set(gemini_map.keys())
        self.logger.info(f"共同验证的产品数量: {len(common_asins)}")

        # 分析不一致的结果
        relevance_disagreements = []  # 相关性判断不一致
        category_disagreements = []   # 分类判断不一致
        both_disagreements = []       # 两者都不一致

        for asin in common_asins:
            claude_val = claude_map[asin]
            gemini_val = gemini_map[asin]

            relevance_disagree = claude_val.is_relevant != gemini_val.is_relevant
            category_disagree = claude_val.category_is_correct != gemini_val.category_is_correct

            if relevance_disagree and category_disagree:
                both_disagreements.append({
                    'asin': asin,
                    'claude_relevant': claude_val.is_relevant,
                    'gemini_relevant': gemini_val.is_relevant,
                    'claude_category_correct': claude_val.category_is_correct,
                    'gemini_category_correct': gemini_val.category_is_correct,
                    'claude_reason': claude_val.validation_reason,
                    'gemini_reason': gemini_val.validation_reason,
                    'claude_suggested': claude_val.suggested_category,
                    'gemini_suggested': gemini_val.suggested_category
                })
            elif relevance_disagree:
                relevance_disagreements.append({
                    'asin': asin,
                    'claude_relevant': claude_val.is_relevant,
                    'gemini_relevant': gemini_val.is_relevant,
                    'claude_reason': claude_val.validation_reason,
                    'gemini_reason': gemini_val.validation_reason
                })
            elif category_disagree:
                category_disagreements.append({
                    'asin': asin,
                    'claude_category_correct': claude_val.category_is_correct,
                    'gemini_category_correct': gemini_val.category_is_correct,
                    'claude_suggested': claude_val.suggested_category,
                    'gemini_suggested': gemini_val.suggested_category,
                    'claude_reason': claude_val.validation_reason,
                    'gemini_reason': gemini_val.validation_reason
                })

        # 计算一致性指标
        total_compared = len(common_asins)
        relevance_agreements = total_compared - len(relevance_disagreements) - len(both_disagreements)
        category_agreements = total_compared - len(category_disagreements) - len(both_disagreements)

        relevance_agreement_rate = relevance_agreements / total_compared if total_compared > 0 else 0
        category_agreement_rate = category_agreements / total_compared if total_compared > 0 else 0
        overall_agreement_rate = (relevance_agreements + category_agreements) / (2 * total_compared) if total_compared > 0 else 0

        # 统计结果
        result = {
            'total_compared': total_compared,
            'relevance_disagreements': relevance_disagreements,
            'category_disagreements': category_disagreements,
            'both_disagreements': both_disagreements,
            'relevance_disagreement_count': len(relevance_disagreements) + len(both_disagreements),
            'category_disagreement_count': len(category_disagreements) + len(both_disagreements),
            'relevance_agreement_rate': relevance_agreement_rate,
            'category_agreement_rate': category_agreement_rate,
            'overall_agreement_rate': overall_agreement_rate,
            'disagreement_asins': self._get_all_disagreement_asins(
                relevance_disagreements,
                category_disagreements,
                both_disagreements
            )
        }

        self.logger.info(f"相关性一致率: {relevance_agreement_rate:.2%}")
        self.logger.info(f"分类一致率: {category_agreement_rate:.2%}")
        self.logger.info(f"总体一致率: {overall_agreement_rate:.2%}")
        self.logger.info(f"不一致的ASIN数量: {len(result['disagreement_asins'])}")

        return result

    def _get_all_disagreement_asins(
        self,
        relevance_disagreements: List[Dict],
        category_disagreements: List[Dict],
        both_disagreements: List[Dict]
    ) -> List[str]:
        """
        获取所有不一致的ASIN列表

        Args:
            relevance_disagreements: 相关性不一致列表
            category_disagreements: 分类不一致列表
            both_disagreements: 两者都不一致列表

        Returns:
            不一致的ASIN列表
        """
        asins = set()
        for item in relevance_disagreements:
            asins.add(item['asin'])
        for item in category_disagreements:
            asins.add(item['asin'])
        for item in both_disagreements:
            asins.add(item['asin'])
        return sorted(list(asins))

    def get_comparison_summary(self, comparison_result: Dict[str, Any]) -> str:
        """
        生成对比摘要文本

        Args:
            comparison_result: 对比结果字典

        Returns:
            摘要文本
        """
        total = comparison_result['total_compared']
        rel_disagree = comparison_result['relevance_disagreement_count']
        cat_disagree = comparison_result['category_disagreement_count']
        rel_rate = comparison_result['relevance_agreement_rate']
        cat_rate = comparison_result['category_agreement_rate']
        overall_rate = comparison_result['overall_agreement_rate']

        summary = f"""
模型对比分析摘要
{'=' * 60}
共同验证产品数: {total}
相关性判断不一致: {rel_disagree} ({(1-rel_rate)*100:.1f}%)
分类判断不一致: {cat_disagree} ({(1-cat_rate)*100:.1f}%)
相关性一致率: {rel_rate*100:.1f}%
分类一致率: {cat_rate*100:.1f}%
总体一致率: {overall_rate*100:.1f}%
不一致的ASIN数量: {len(comparison_result['disagreement_asins'])}
{'=' * 60}
"""
        return summary

    def export_disagreements_to_csv(
        self,
        comparison_result: Dict[str, Any],
        output_path: str
    ) -> None:
        """
        导出不一致的结果到CSV文件

        Args:
            comparison_result: 对比结果字典
            output_path: 输出文件路径
        """
        import csv

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ASIN',
                '不一致类型',
                'Claude相关性',
                'Gemini相关性',
                'Claude分类正确',
                'Gemini分类正确',
                'Claude建议分类',
                'Gemini建议分类',
                'Claude原因',
                'Gemini原因'
            ])

            # 写入相关性不一致
            for item in comparison_result['relevance_disagreements']:
                writer.writerow([
                    item['asin'],
                    '相关性不一致',
                    '是' if item['claude_relevant'] else '否',
                    '是' if item['gemini_relevant'] else '否',
                    '-',
                    '-',
                    '-',
                    '-',
                    item['claude_reason'],
                    item['gemini_reason']
                ])

            # 写入分类不一致
            for item in comparison_result['category_disagreements']:
                writer.writerow([
                    item['asin'],
                    '分类不一致',
                    '-',
                    '-',
                    '是' if item['claude_category_correct'] else '否',
                    '是' if item['gemini_category_correct'] else '否',
                    item['claude_suggested'] or '-',
                    item['gemini_suggested'] or '-',
                    item['claude_reason'],
                    item['gemini_reason']
                ])

            # 写入两者都不一致
            for item in comparison_result['both_disagreements']:
                writer.writerow([
                    item['asin'],
                    '相关性和分类都不一致',
                    '是' if item['claude_relevant'] else '否',
                    '是' if item['gemini_relevant'] else '否',
                    '是' if item['claude_category_correct'] else '否',
                    '是' if item['gemini_category_correct'] else '否',
                    item['claude_suggested'] or '-',
                    item['gemini_suggested'] or '-',
                    item['claude_reason'],
                    item['gemini_reason']
                ])

        self.logger.info(f"不一致结果已导出到: {output_path}")
