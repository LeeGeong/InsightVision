"""
OCR 集成测试

测试宝钢钢板库 OCR 识别功能
"""
import pytest
import requests
import time
from typing import Dict, Any
from tests.test_config import TEST_CONFIGS, SERVER_CONFIG


class TestOCRIntegration:
    """OCR 集成测试类"""

    @pytest.fixture
    def server_url(self):
        """获取服务器URL"""
        return f"{SERVER_CONFIG['base_url']}{SERVER_CONFIG['api_prefix']}"

    @pytest.fixture
    def test_config(self, request):
        """获取测试配置"""
        config_name = getattr(request, "param", "TCP7")
        return TEST_CONFIGS.get(config_name)

    def test_server_health(self, server_url):
        """测试服务器是否正常运行"""
        try:
            response = requests.get(f"{SERVER_CONFIG['base_url']}/docs", timeout=5)
            assert response.status_code == 200, "服务器未正常运行"
            print("✅ 服务器运行正常")
        except requests.exceptions.ConnectionError:
            pytest.fail("无法连接到服务器，请确认服务已启动")

    @pytest.mark.parametrize("test_config", ["TCP7"], indirect=True)
    def test_ocr_barcode_tcp7(self, server_url, test_config):
        """测试 TCP7 车位的 OCR 喷码识别"""
        print(f"\n{'='*60}")
        print(f"开始测试: {test_config['name']}")
        print(f"描述: {test_config['description']}")
        print(f"IP: {test_config['ip']}")
        print(f"车位号: {test_config['park_no']}")
        print(f"请求模式: {test_config['request_mode']} (0=自动, 1=人工)")
        print(f"{'='*60}\n")

        # 步骤1：获取高度
        height = test_config.get("default_height", 2300)
        
        # 如果有点云文件，先调用 car_height 接口获取高度
        if test_config.get("file_path"):
            print(f"[INFO] 检测到点云文件，正在获取高度...")
            try:
                height_params = {
                    "park_no": test_config["park_no"],
                    "file_path": test_config["file_path"]
                }
                height_response = requests.get(
                    f"{server_url}/car_height",
                    params=height_params,
                    timeout=30
                )
                
                if height_response.status_code == 200:
                    height_result = height_response.json()
                    if height_result.get("status") == "success":
                        height = height_result.get("height", height)
                        print(f"[OK] 成功获取高度: {height}")
                    else:
                        print(f"[WARN] 获取高度失败: {height_result.get('message', '未知错误')}")
                        print(f"       使用默认高度: {height}")
                else:
                    print(f"[WARN] 高度接口请求失败，状态码: {height_response.status_code}")
                    print(f"       使用默认高度: {height}")
            except Exception as e:
                print(f"[WARN] 获取高度异常: {str(e)}")
                print(f"       使用默认高度: {height}")
        else:
            print(f"[INFO] 未提供点云文件，使用默认高度: {height}")
        
        print(f"\n{'='*60}")
        print(f"准备进行 OCR 测试")
        print(f"使用高度: {height}")
        print(f"{'='*60}\n")

        # 步骤2：构建请求数据
        request_data = {
            "ip": test_config["ip"],
            "mat_infos": test_config.get("mat_infos", [])
        }

        # 构建请求参数
        params = {
            "request_mode": test_config["request_mode"],
            "height": int(height)
        }

        # 步骤3：发送 OCR 请求
        start_time = time.time()
        try:
            response = requests.post(
                f"{server_url}/barcode_ocr",
                json=request_data,
                params=params,
                timeout=SERVER_CONFIG["timeout"]
            )
            elapsed_time = time.time() - start_time

            # 验证响应状态码
            assert response.status_code == 200, f"请求失败，状态码: {response.status_code}"

            # 解析响应数据
            result = response.json()

            # 验证基本结构
            assert "status" in result, "响应缺少 status 字段"
            assert "results" in result, "响应缺少 results 字段"

            # 打印结果
            print(f"\n{'='*60}")
            print(f"测试结果:")
            print(f"{'='*60}")
            print(f"状态: {result.get('status')}")
            print(f"请求耗时: {elapsed_time:.2f}秒")
            
            if "time_usage" in result:
                print(f"\n耗时统计:")
                time_usage = result["time_usage"]
                if isinstance(time_usage, dict):
                    for key, value in time_usage.items():
                        print(f"  - {key}: {value}")

            # 验证并打印结果列表
            if "results" in result and isinstance(result["results"], list):
                print(f"\n识别结果数量: {len(result['results'])}")
                
                for i, res in enumerate(result["results"]):
                    print(f"\n--- 喷码 {i + 1} ---")
                    print(f"  状态: {res.get('status', 'N/A')}")
                    print(f"  消息: {res.get('message', 'N/A')}")
                    print(f"  优先级: {res.get('Priority', 'N/A')}")
                    
                    if res.get('Ocr_BatchNo'):
                        print(f"  批号: {res.get('Ocr_BatchNo')}")
                    if res.get('Ocr_Manufactor'):
                        print(f"  厂家: {res.get('Ocr_Manufactor')}")
                    if res.get('Ocr_Weight'):
                        print(f"  重量: {res.get('Ocr_Weight')}")
                    if res.get('Ocr_Length') and res.get('Ocr_Width'):
                        print(f"  规格: {res.get('Ocr_Length')} x {res.get('Ocr_Width')} x {res.get('Ocr_Height')}")
                    
                    if res.get('box'):
                        print(f"  检测框: {res.get('box')}")

            # 验证图片数据
            if result.get("image_base64_overview"):
                print(f"\n[OK] 概览图片已生成 (Base64 长度: {len(result['image_base64_overview'])})")
            
            # 检查详情图片
            if "results" in result:
                for i, res in enumerate(result["results"]):
                    if res.get("image_base64_detail"):
                        print(f"[OK] 喷码 {i + 1} 详情图片已生成 (Base64 长度: {len(res['image_base64_detail'])})")

            # 验证状态
            assert result["status"] in ["success", "error"], f"未知状态: {result['status']}"
            
            print(f"\n{'='*60}")
            print(f"[OK] 测试完成!")
            print(f"{'='*60}\n")

        except requests.exceptions.Timeout:
            pytest.fail(f"请求超时（超过 {SERVER_CONFIG['timeout']} 秒）")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"请求异常: {str(e)}")
        except Exception as e:
            pytest.fail(f"测试异常: {str(e)}")

    @pytest.mark.parametrize("test_config", ["TCP3"], indirect=True)
    def test_ocr_barcode_tcp3(self, server_url, test_config):
        """测试 TCP3 车位的 OCR 喷码识别"""
        # 与 TCP7 测试逻辑相同
        self.test_ocr_barcode_tcp7(server_url, test_config)


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])
