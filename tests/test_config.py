"""
OCR 测试配置文件

用于配置不同车位的测试参数
"""
from typing import Dict, Any, List

# TCP7 测试配置
TCP7_CONFIG: Dict[str, Any] = {
    "name": "TCP7",
    "ip": "192.168.3.65",
    "park_no": "TCP7",
    "file_path": "",  # 点云文件路径，如果有的话
    "request_mode": 0,  # 0=自动，1=人工
    "default_height": 2300,  # 默认高度（如果无法获取高度）
    "mat_infos": [  # 物料信息（用于验证）
        {
            "mat_no": "6406229200",
            "mat_length": 10378.0,
            "mat_width": 3581.0,
            "mat_thick": 21.5,
            "mat_weight": 6240.0
        }
    ],
    "description": "宝钢钢板库 TCP7 车位 OCR 测试"
}

# TCP3 测试配置
TCP3_CONFIG: Dict[str, Any] = {
    "name": "TCP3",
    "ip": "192.168.3.61",
    "park_no": "TCP3",
    "file_path": "",
    "request_mode": 0,
    "default_height": 2300,
    "mat_infos": [
        {
            "mat_no": "6406229200",
            "mat_length": 10378.0,
            "mat_width": 3581.0,
            "mat_thick": 21.5,
            "mat_weight": 6240.0
        }
    ],
    "description": "宝钢钢板库 TCP3 车位 OCR 测试"
}

# 所有测试配置
TEST_CONFIGS = {
    "TCP7": TCP7_CONFIG,
    "TCP3": TCP3_CONFIG,
}

# 测试服务器配置
SERVER_CONFIG = {
    "base_url": "http://localhost:8001",
    "api_prefix": "/api/bao_steel",
    "timeout": 120,  # 请求超时时间（秒），增加到120秒因为OCR处理较慢
}
