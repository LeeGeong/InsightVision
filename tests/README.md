# 测试文档

## 目录结构

```
tests/
├── __init__.py              # Tests 包
├── conftest.py              # Pytest 配置
├── test_config.py           # 测试配置
├── run_ocr_test.py          # OCR 测试运行脚本
├── unit/                    # 单元测试
│   └── __init__.py
├── integration/             # 集成测试
│   ├── __init__.py
│   └── test_ocr_integration.py
└── README.md               # 本文档
```

## 环境准备

### 1. 安装测试依赖

```bash
pip install pytest requests
```

### 2. 确认服务已启动

确保 FastAPI 服务已启动在 `http://localhost:8001`

```bash
# 启动服务
python app/startup.py
```

## 运行测试

### 方式一：使用测试脚本（推荐）

```bash
# 测试 TCP7 车位（默认）
python tests/run_ocr_test.py

# 测试指定车位
python tests/run_ocr_test.py --config TCP7
python tests/run_ocr_test.py --config TCP3

# 静默模式
python tests/run_ocr_test.py --quiet
```

### 方式二：使用 pytest 命令

```bash
# 运行所有 OCR 测试
pytest tests/integration/test_ocr_integration.py -v -s

# 运行特定车位的测试
pytest tests/integration/test_ocr_integration.py::TestOCRIntegration::test_ocr_steel_plate_tcp7 -v -s

# 运行并生成覆盖率报告
pytest tests/integration/test_ocr_integration.py --cov=app --cov-report=html
```

### 方式三：在 Python 代码中运行

```python
from tests.run_ocr_test import run_test

# 运行 TCP7 测试
run_test("TCP7")

# 运行 TCP3 测试
run_test("TCP3")
```

## 测试配置

### 修改测试配置

编辑 `tests/test_config.py` 文件：

```python
# 添加新的测试配置
NEW_CONFIG = {
    "name": "NEW_TCPP",
    "ip": "192.168.3.XX",
    "park_no": "NEW_TCPP",
    "height": 0,
    "classId": 1,
    "file_path": "",
    "description": "新车位测试"
}

# 添加到配置字典
TEST_CONFIGS["NEW_TCPP"] = NEW_CONFIG
```

### 配置服务器地址

如果服务器不在本地，修改 `tests/test_config.py`：

```python
SERVER_CONFIG = {
    "base_url": "http://your-server-ip:8001",
    "api_prefix": "/api/bao_steel",
    "timeout": 60,
}
```

## 测试输出说明

### 成功示例

```
============================================================
开始测试: TCP7
描述: 宝钢钢板库 TCP7 车位 OCR 测试
IP: 192.168.3.65
车位号: TCP7
============================================================

============================================================
测试结果:
============================================================
状态: success
消息: N/A
请求耗时: 5.23秒

耗时统计:
  - total: 5.23s
  - camera_setup: 0.15
  - camera_shooting: 2.31
  - ocr_processing: 1.89

识别结果:
  - 中心点1: [1234, 567, 0]
  - 中心点2: [1234, 567, 0]
  - 宽高: [200, 150]
  - 上边缘角度: 1.5°
  - 下边缘角度: -0.8°

安全区域:
  - X范围: [100.00, 200.00]
  - Y范围: [50.00, 150.00]

✅ 原始图片已生成 (Base64 长度: 123456)
✅ 可视化图片已生成 (Base64 长度: 234567)

============================================================
✅ 测试通过!
============================================================
```

### 失败示例

```
============================================================
❌ 测试失败，退出码: 1
============================================================
```

## 常见问题

### 1. 无法连接到服务器

**错误信息**: `无法连接到服务器，请确认服务已启动`

**解决方案**:
- 确认服务已启动: `python app/startup.py`
- 检查端口是否正确: 默认 8001
- 检查防火墙设置

### 2. 请求超时

**错误信息**: `请求超时（超过 60 秒）`

**解决方案**:
- 增加 `test_config.py` 中的 `timeout` 值
- 检查网络连接
- 检查服务器性能

### 3. 测试失败

**错误信息**: `OCR 处理失败: ...`

**解决方案**:
- 检查日志文件: `logs/app.log`
- 确认相机 IP 是否正确
- 确认相机是否在线
- 检查数据库配置

## 扩展测试

### 添加单元测试

在 `tests/unit/` 目录下创建测试文件：

```python
# tests/unit/test_func_calc.py
import pytest
from app.core.func_calc import remove_duplicates

def test_remove_duplicates():
    data = {
        "results": [
            {"Ocr_BatchNo": "001", "status": "success"},
            {"Ocr_BatchNo": "001", "status": "success"}
        ]
    }
    result = remove_duplicates(data)
    assert len(result["results"]) == 1
```

### 添加新的集成测试

在 `tests/integration/` 目录下创建测试文件：

```python
# tests/integration/test_camera_integration.py
import pytest
import requests

def test_camera_connection():
    """测试相机连接"""
    response = requests.get("http://192.168.3.65:80")
    assert response.status_code == 200
```

## 最佳实践

1. **测试前准备**
   - 确保服务已启动
   - 确保相机在线
   - 检查网络连接

2. **测试执行**
   - 先运行健康检查测试
   - 再运行具体功能测试
   - 记录测试结果

3. **测试后验证**
   - 检查日志文件
   - 验证输出图片
   - 确认数据库记录

4. **持续集成**
   - 定期运行测试
   - 监控测试结果
   - 及时修复失败用例

## 联系方式

如有问题，请联系开发团队。
