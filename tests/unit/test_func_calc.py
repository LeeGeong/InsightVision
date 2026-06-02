"""
func_calc 单元测试

测试 OCR 结果过滤和去重功能
"""
import pytest
from app.core.func_calc import remove_duplicates, filtering_algorithm


class TestRemoveDuplicates:
    """测试 remove_duplicates 函数"""

    def test_remove_duplicates_basic(self):
        """测试基本的去重功能"""
        data = {
            "results": [
                {"Ocr_BatchNo": "001", "box": "A", "status": "success"},
                {"Ocr_BatchNo": "001", "box": "B", "status": "success"},
                {"Ocr_BatchNo": "002", "box": "C", "status": "success"}
            ]
        }
        result = remove_duplicates(data)
        
        assert len(result["results"]) == 2
        assert result["results"][0]["Ocr_BatchNo"] == "001"
        assert result["results"][0]["box"] == "A"  # 保留第一个

    def test_remove_duplicates_empty_results(self):
        """测试空结果列表"""
        data = {"results": []}
        result = remove_duplicates(data)
        
        assert result == data

    def test_remove_duplicates_no_batch_no(self):
        """测试缺少 Ocr_BatchNo 字段"""
        data = {
            "results": [
                {"box": "A", "status": "success"},
                {"box": "B", "status": "error"}
            ]
        }
        result = remove_duplicates(data)
        
        # 缺少 Ocr_BatchNo，应该返回原数据
        assert result == data

    def test_remove_duplicates_invalid_input(self):
        """测试无效输入"""
        # 不是字典
        result = remove_duplicates("invalid")
        assert result == "invalid"
        
        # None
        result = remove_duplicates(None)
        assert result is None


class TestFilteringAlgorithm:
    """测试 filtering_algorithm 函数"""

    def test_filter_single_success(self):
        """测试只有一个 success 记录的情况"""
        data = {
            "results": [
                {"Ocr_BatchNo": "001", "status": "success", "Priority": 1},
                {"Ocr_BatchNo": "002", "status": "error", "Priority": 2}
            ]
        }
        result = filtering_algorithm(data)
        
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "success"
        assert result["results"][0]["Ocr_BatchNo"] == "001"

    def test_filter_multiple_success_with_duplicates(self):
        """测试多个 success 且有重复的情况"""
        data = {
            "results": [
                {"Ocr_BatchNo": "001", "status": "success", "Priority": 3},
                {"Ocr_BatchNo": "001", "status": "success", "Priority": 1},
                {"Ocr_BatchNo": "002", "status": "success", "Priority": 2}
            ]
        }
        result = filtering_algorithm(data)
        
        # 应该保留重复的 001，且选择 Priority 最小的
        assert len(result["results"]) == 1
        assert result["results"][0]["Ocr_BatchNo"] == "001"
        assert result["results"][0]["Priority"] == 1

    def test_filter_no_success(self):
        """测试没有 success 记录的情况"""
        data = {
            "results": [
                {"Ocr_BatchNo": "001", "status": "error"},
                {"Ocr_BatchNo": "002", "status": "error"}
            ]
        }
        result = filtering_algorithm(data)
        
        # 没有 success，应该返回原数据
        assert result == data

    def test_filter_single_record(self):
        """测试只有一条记录的情况"""
        data = {
            "results": [
                {"Ocr_BatchNo": "001", "status": "success"}
            ]
        }
        result = filtering_algorithm(data)
        
        # 只有一条记录，直接返回
        assert result == data

    def test_filter_empty_results(self):
        """测试空结果"""
        data = {"results": []}
        result = filtering_algorithm(data)
        
        assert result == data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
