# 快速开始：OCR 测试

## 🚀 5分钟快速测试

### 步骤 1: 安装测试依赖

```bash
pip install pytest requests
```

### 步骤 2: 确认服务已启动

确保 FastAPI 服务运行在 `http://localhost:8001`

### 步骤 3: 运行 TCP7 测试

#### 方式一：双击运行（Windows）
```
双击运行：tests\run_test.bat
```

#### 方式二：命令行运行
```bash
python tests\run_ocr_test.py --config TCP7
```

#### 方式三：使用 pytest
```bash
pytest tests\integration\test_ocr_integration.py -v -s
```

## 📊 测试输出示例

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

✅ 原始图片已生成
✅ 可视化图片已生成

============================================================
✅ 测试通过!
============================================================
```

## 🎯 测试其他车位

```bash
# 测试 TCP3
python tests\run_ocr_test.py --config TCP3

# 测试所有配置的车位
pytest tests\integration\test_ocr_integration.py -v -s
```

## 📝 添加新的测试车位

编辑 `tests\test_config.py`，添加新配置：

```python
NEW_CONFIG = {
    "name": "NEW_TCPP",
    "ip": "192.168.3.XX",
    "park_no": "NEW_TCPP",
    "height": 0,
    "classId": 1,
    "file_path": "",
    "description": "新车位测试"
}

TEST_CONFIGS["NEW_TCPP"] = NEW_CONFIG
```

然后运行：

```bash
python tests\run_ocr_test.py --config NEW_TCPP
```

## ⚠️ 常见问题

### 1. 无法连接到服务器

**解决方案**:
```bash
# 检查服务是否启动
curl http://localhost:8001/docs

# 如果没有启动，运行
python app\startup.py
```

### 2. 测试超时

**解决方案**:
编辑 `tests\test_config.py`，增加超时时间：
```python
SERVER_CONFIG = {
    "timeout": 120,  # 从 60 改为 120 秒
}
```

### 3. 相机连接失败

**解决方案**:
- 检查相机 IP 是否正确
- 确认相机在线
- 检查网络连接

## 📚 更多信息

详细文档请查看：
- [测试文档](tests/README.md)
- [测试报告模板](tests/TEST_REPORT_TEMPLATE.md)

## 🎉 下一步

1. 运行单元测试：`pytest tests\unit\test_func_calc.py -v`
2. 查看测试覆盖率：`pytest --cov=app tests\`
3. 生成测试报告：`pytest --html=report.html tests\`
