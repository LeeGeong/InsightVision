import numpy as np
from typing import List, Dict, Tuple, Optional
import Levenshtein
from difflib import SequenceMatcher
import re
from collections import defaultdict


class SprayCodeMatcher:
    """喷码匹配器 - 从OCR结果中找到最匹配的喷码"""

    def __init__(self, spray_codes: List[Dict[str, str]]):
        """
        初始化匹配器

        Args:
            spray_codes: 喷码列表
        """
        self.spray_codes = [item['mat_no'] for item in spray_codes]
        self.code_patterns = self._analyze_patterns()

    def _analyze_patterns(self) -> Dict:
        """分析喷码模式"""
        patterns = {
            'lengths': defaultdict(list),
            'prefixes': defaultdict(list),
            'char_positions': defaultdict(lambda: defaultdict(int))
        }

        for code in self.spray_codes:
            # 长度分组
            patterns['lengths'][len(code)].append(code)

            # 前缀分组
            if len(code) >= 2:
                patterns['prefixes'][code[:2]].append(code)

            # 字符位置频率
            for i, char in enumerate(code):
                patterns['char_positions'][i][char] += 1

        return patterns

    def find_best_match(self, ocr_text: str, top_k: int = 3) -> List[Tuple[str, float, Dict]]:
        """
        找到最匹配的喷码

        Args:
            ocr_text: OCR识别的文本
            top_k: 返回前k个最佳匹配

        Returns:
            [(喷码, 置信度, 详细信息), ...]
        """
        candidates = []

        # 预处理OCR文本
        ocr_text = self._preprocess_ocr_text(ocr_text)

        for code in self.spray_codes:
            # 计算多种相似度
            scores = {
                'levenshtein': self._levenshtein_similarity(ocr_text, code),
                'sequence': self._sequence_similarity(ocr_text, code),
                'position': self._position_similarity(ocr_text, code),
                'pattern': self._pattern_similarity(ocr_text, code),
                'char_confusion': self._char_confusion_similarity(ocr_text, code)
            }

            # 加权综合评分
            weights = {
                'levenshtein': 0.25,
                'sequence': 0.20,
                'position': 0.20,
                'pattern': 0.15,
                'char_confusion': 0.20
            }

            final_score = sum(scores[k] * weights[k] for k in scores)

            candidates.append((code, final_score, scores))

        # 排序并返回前k个
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def _preprocess_ocr_text(self, text: str) -> str:
        """预处理OCR文本"""
        # 移除空格和特殊字符
        text = re.sub(r'[^A-Za-z0-9]', '', text)
        # 转换为大写
        text = text.upper()
        return text

    def _levenshtein_similarity(self, text1: str, text2: str) -> float:
        """编辑距离相似度"""
        distance = Levenshtein.distance(text1, text2)
        max_len = max(len(text1), len(text2))
        return 1 - (distance / max_len) if max_len > 0 else 0

    def _sequence_similarity(self, text1: str, text2: str) -> float:
        """序列相似度"""
        return SequenceMatcher(None, text1, text2).ratio()

    def _position_similarity(self, ocr_text: str, code: str) -> float:
        """位置相似度 - 考虑字符在正确位置的比例"""
        if len(ocr_text) != len(code):
            # 长度不同时，尝试对齐
            return self._aligned_position_similarity(ocr_text, code)

        matches = sum(1 for i in range(len(code)) if i < len(ocr_text) and ocr_text[i] == code[i])
        return matches / len(code)

    def _aligned_position_similarity(self, ocr_text: str, code: str) -> float:
        """对齐后的位置相似度"""
        # 动态规划对齐
        m, n = len(ocr_text), len(code)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ocr_text[i - 1] == code[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n] / n if n > 0 else 0

    def _pattern_similarity(self, ocr_text: str, code: str) -> float:
        """模式相似度 - 基于喷码的模式特征"""
        score = 0.0

        # 长度相似度
        len_diff = abs(len(ocr_text) - len(code))
        len_score = 1 / (1 + len_diff * 0.2)
        score += len_score * 0.3

        # 前缀相似度
        if len(ocr_text) >= 2 and len(code) >= 2:
            prefix_match = 1.0 if ocr_text[:2] == code[:2] else 0.5 if ocr_text[0] == code[0] else 0
            score += prefix_match * 0.4

        # 字符类型模式（数字/字母分布）
        ocr_pattern = self._get_char_pattern(ocr_text)
        code_pattern = self._get_char_pattern(code)
        pattern_match = self._compare_patterns(ocr_pattern, code_pattern)
        score += pattern_match * 0.3

        return score

    def _get_char_pattern(self, text: str) -> str:
        """获取字符模式（D=数字，L=字母）"""
        pattern = ''
        for char in text:
            if char.isdigit():
                pattern += 'D'
            elif char.isalpha():
                pattern += 'L'
            else:
                pattern += '?'
        return pattern

    def _compare_patterns(self, pattern1: str, pattern2: str) -> float:
        """比较两个模式的相似度"""
        if not pattern1 or not pattern2:
            return 0
        return SequenceMatcher(None, pattern1, pattern2).ratio()

    def _char_confusion_similarity(self, ocr_text: str, code: str) -> float:
        """字符混淆相似度 - 考虑OCR常见的混淆"""
        # OCR常见混淆对
        confusion_pairs = {
            '0': ['O', 'Q', 'D'],
            'O': ['0', 'Q', 'D'],
            '1': ['I', 'L', '|', 'l'],
            'I': ['1', 'L', '|', 'l'],
            'L': ['1', 'I', '|', 'l'],
            '5': ['S'],
            'S': ['5'],
            '6': ['G', 'b'],
            'G': ['6', 'C'],
            '8': ['B'],
            'B': ['8', '3'],
            '2': ['Z'],
            'Z': ['2'],
            '3': ['B', 'E'],
            'E': ['3', 'F'],
            '4': ['A'],
            'A': ['4'],
            '7': ['T', 'L'],
            'T': ['7'],
            '9': ['g', 'q'],
            'C': ['G', '(', '['],
        }

        # 创建混淆文本的变体
        max_similarity = self._levenshtein_similarity(ocr_text, code)

        # 尝试替换可能混淆的字符
        for i, char in enumerate(ocr_text):
            if char in confusion_pairs:
                for replacement in confusion_pairs[char]:
                    variant = ocr_text[:i] + replacement + ocr_text[i + 1:]
                    similarity = self._levenshtein_similarity(variant, code)
                    max_similarity = max(max_similarity, similarity)

        return max_similarity

    def batch_match(self, ocr_results: List[str]) -> List[List[Tuple[str, float, Dict]]]:
        """批量匹配多个OCR结果"""
        results = []
        for ocr_text in ocr_results:
            matches = self.find_best_match(ocr_text)
            results.append(matches)
        return results

    def get_match_report(self, ocr_text: str) -> str:
        """生成详细的匹配报告"""
        matches = self.find_best_match(ocr_text, top_k=5)

        report = f"OCR识别文本: {ocr_text}\n"
        report += "=" * 50 + "\n"

        for i, (code, score, details) in enumerate(matches, 1):
            report += f"\n匹配 {i}: {code} (总分: {score:.3f})\n"
            report += "详细评分:\n"
            for metric, value in details.items():
                report += f"  - {metric}: {value:.3f}\n"

        return report


# 高级匹配器 - 使用机器学习特征
class AdvancedSprayCodeMatcher(SprayCodeMatcher):
    """高级喷码匹配器 - 包含更多智能特征"""

    def __init__(self, spray_codes: List[Dict[str, str]]):
        super().__init__(spray_codes)
        self.ocr_error_stats = self._build_error_statistics()

    def _build_error_statistics(self) -> Dict:
        """构建OCR错误统计（实际应用中应该从历史数据学习）"""
        return {
            'char_frequency': self._calculate_char_frequency(),
            'position_importance': self._calculate_position_importance()
        }

    def _calculate_char_frequency(self) -> Dict[str, float]:
        """计算字符频率"""
        char_count = defaultdict(int)
        total_chars = 0

        for code in self.spray_codes:
            for char in code:
                char_count[char] += 1
                total_chars += 1

        return {char: count / total_chars for char, count in char_count.items()}

    def _calculate_position_importance(self) -> List[float]:
        """计算位置重要性（某些位置的字符更稳定）"""
        max_len = max(len(code) for code in self.spray_codes)
        position_variance = []

        for pos in range(max_len):
            chars_at_pos = []
            for code in self.spray_codes:
                if pos < len(code):
                    chars_at_pos.append(code[pos])

            # 计算该位置的字符多样性
            unique_chars = len(set(chars_at_pos))
            total_chars = len(chars_at_pos)
            variance = unique_chars / total_chars if total_chars > 0 else 1
            position_variance.append(1 - variance)  # 越稳定权重越高

        return position_variance

    def smart_match(self, ocr_text: str, context: Optional[Dict] = None) -> Tuple[str, float, Dict]:
        """
        智能匹配 - 考虑上下文信息

        Args:
            ocr_text: OCR文本
            context: 上下文信息（如：图像质量、位置、历史记录等）

        Returns:
            (最佳匹配喷码, 置信度, 详细信息)
        """
        # 基础匹配
        base_matches = self.find_best_match(ocr_text, top_k=5)

        if context:
            # 根据上下文调整评分
            adjusted_matches = []

            for code, score, details in base_matches:
                adjusted_score = score

                # 如果有历史记录，提高常见喷码的权重
                if 'history' in context and code in context['history']:
                    frequency = context['history'][code]
                    adjusted_score *= (1 + frequency * 0.1)

                # 如果图像质量差，更依赖模式匹配
                if 'image_quality' in context and context['image_quality'] < 0.5:
                    pattern_score = details['pattern']
                    adjusted_score = score * 0.7 + pattern_score * 0.3

                adjusted_matches.append((code, adjusted_score, details))

            adjusted_matches.sort(key=lambda x: x[1], reverse=True)
            return adjusted_matches[0]
        else:
            return base_matches[0]


# 使用示例
def demo_usage():
    # 您提供的喷码数据
    spray_codes = [
        {'mat_no': '5C31401130'},
        {'mat_no': '5C31401140'},
        {'mat_no': '6113162100'},
        # ... 其他喷码
    ]

    # 创建匹配器
    matcher = AdvancedSprayCodeMatcher(spray_codes)

    # 模拟OCR识别结果（可能有错误）
    ocr_results = [
        "5C3140113O",  # 最后一位0识别成O
        "6II3I62I00",  # 多个1识别成I
        "SC31401140",  # 5识别成S
        "6118137Z00",  # 2识别成Z
    ]

    print("喷码匹配结果：")
    print("=" * 60)

    for ocr_text in ocr_results:
        matches = matcher.find_best_match(ocr_text, top_k=3)

        print(f"\nOCR识别: {ocr_text}")
        for i, (code, score, details) in enumerate(matches, 1):
            print(f"  匹配{i}: {code} (置信度: {score:.3f})")

        # 生成详细报告
        print("\n" + "-" * 60)
        print(matcher.get_match_report(ocr_text))

    # 演示智能匹配功能
    print("\n" + "=" * 60)
    print("智能匹配演示（带上下文信息）：")
    print("=" * 60)

    # 模拟上下文信息
    context = {
        'history': {'5C31401130': 0.8, '5C31401140': 0.5},  # 历史频率
        'image_quality': 0.7  # 图像质量
    }

    test_ocr = "5C3140113O"
    best_match, confidence, details = matcher.smart_match(test_ocr, context)

    print(f"\nOCR识别: {test_ocr}")
    print(f"最佳匹配: {best_match}")
    print(f"置信度: {confidence:.3f}")
    print(f"详细评分: {details}")

    # 演示批量匹配
    print("\n" + "=" * 60)
    print("批量匹配演示：")
    print("=" * 60)

    batch_results = matcher.batch_match(ocr_results)
    for i, matches in enumerate(batch_results):
        print(f"\nOCR结果 {i+1}: {ocr_results[i]}")
        for j, (code, score, _) in enumerate(matches, 1):
            print(f"  {j}. {code} (置信度: {score:.3f})")


if __name__ == "__main__":
    demo_usage()