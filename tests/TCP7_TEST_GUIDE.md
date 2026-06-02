# TCP7 OCR 测试快速指南

## 📋 测试说明

本测试用于验证宝钢钢板库 TCP7 车位的 OCR 喷码识别功能。

## 🎯 测试内容

### 测试接口
- **接口路径**: `POST /api/bao_steel/barcode_ocr_test`
- **接口功能**: 喷码识别

### 测试参数

#### 请求体 (JSON)
```json
{
    "ip": "192.168.3.65",
    "mat_infos": [
        {
            "mat_no": "6310242200",
            "mat_length": 10378.0,
            "mat_width": 3581.0,
            "mat_thick": 21.5,
            "mat_weight": 6240.0
        }
    ]
}
```

**字段说明**:
- `ip`: 相机 IP 地址
- `mat_infos`: 物料信息列表（用于验证 OCR 结果）
  - `mat_no`: 物料编号（批号）
  - `mat_length`: 长度
  - `mat_width`: 宽度
  - `mat_thick`: 厚度
  - `mat_weight`: 重量

#### 查询参数
- `request_mode`: 0=自动，1=人工
- `height`: 高度参数（默认2300）

### 预期返回

```json
{
    "status": "success",
    "results": [
        {
            "Ocr_Manufactor": "厂家",
            "Ocr_BatchNo": "批号",
            "Ocr_Length": 1000,
            "Ocr_Width": 2000,
            "Ocr_Height": 10,
            "Ocr_Weight": 150.5,
            "Ocr_Code": "编号",
            "Priority": 0,
            "box": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
            "status": "success",
            "message": "第 1 个喷码识别成功",
            "image_base64_detail": "..."
        }
    ],
    "image_base64_overview": "...",
    "time_usage": {
        "total": "10.5s",
        "camera_setup": 0.15,
        "mat_info_check": 0.05,
        "camera_shooting": 2.31,
        "ocr_processing": 5.89,
        ...
    }
}
```

## 🚀 运行测试

### 方式一：使用测试脚本（推荐）

```bash
python tests\run_ocr_test.py --config TCP7
```

### 方式二：使用 pytest

```bash
pytest tests\integration\test_ocr_integration.py::TestOCRIntegration::test_ocr_barcode_tcp7 -v -s
```

### 方式三：双击运行（Windows）

```
双击运行：tests\run_test.bat
```

## ⚠️ 注意事项

### 1. 生产环境测试
- ✅ 测试会调用真实的相机
- ✅ 测试会保存图片文件
- ✅ 测试会写入数据库
- ⚠️ 请确保测试不会影响生产业务

### 2. 测试前检查
- ✅ 确认服务已启动（http://localhost:8001）
- ✅ 确认相机在线（192.168.3.65）
- ✅ 确认网络连接正常
- ✅ 确认数据库连接正常

### 3. 测试时间
- 预计耗时：10-30秒
- 超时设置：120秒

## 📊 测试输出

测试会输出以下信息：

1. **测试配置**
   - 车位编号
   - 相机IP
   - 请求模式
   - 高度参数

2. **测试结果**
   - 状态（success/error）
   - 请求耗时
   - 详细耗时统计

3. **识别结果**
   - 喷码数量
   - 每个喷码的详细信息
   - 批号、厂家、重量等
   - 检测框坐标

4. **图片验证**
   - 概览图片
   - 详情图片

## 🔧 故障排查

### 问题1：无法连接到服务器

**解决方案**:
```bash
# 检查服务状态
curl http://localhost:8001/docs

# 启动服务
python app\startup.py
```

### 问题2：相机连接失败

**解决方案**:
- 检查相机IP是否正确
- 确认相机在线
- 检查网络连接
- 检查相机账号密码

### 问题3：测试超时

**解决方案**:
编辑 `tests\test_config.py`，增加超时时间：
```python
SERVER_CONFIG = {
    "timeout": 180,  # 增加到180秒
}
```

### 问题4：OCR识别失败

**解决方案**:
- 检查日志文件：`logs/app.log`
- 确认模型文件存在
- 确认相机拍摄清晰
- 检查光线条件

## 📝 测试报告

测试完成后，请填写测试报告：
- 使用模板：`tests/TEST_REPORT_TEMPLATE.md`
- 记录测试结果
- 记录问题和解决方案

## 📞 联系方式

如有问题，请联系开发团队。
