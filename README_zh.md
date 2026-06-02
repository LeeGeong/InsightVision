<div align="center">

![InsightVision Logo](https://img.shields.io/badge/InsightVision-智能视觉平台-009688?style=for-the-badge&logo=vision&logoColor=white)

# InsightVision - 工业智能视觉平台

*基于深度学习的工业场景智能视觉识别系统*

[![Python Version](https://img.shields.io/badge/Python-3.9+-4B8BBE?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.2-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![YOLO](https://img.shields.io/badge/YOLO-v11-FF6B6B?style=flat-square&logo=robot&logoColor=white)](https://github.com/ultralytics/ultralytics)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7.3-2C3E50?style=flat-square)](https://github.com/PaddlePaddle/PaddleOCR)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)]()

---

[English](README.md) | 简体中文

</div>

## 📖 项目简介

**InsightVision** 是一款面向工业场景的智能视觉识别平台，专注于钢板识别、车牌 OCR、安全区域检测等核心功能。系统采用先进的深度学习算法，结合工业级相机管理能力，为钢铁、物流等行业提供高精度、高实时性的视觉解决方案。

### 🎯 核心功能

| 功能模块 | 技术栈 | 应用场景 |
|---------|--------|---------|
| **钢板识别** | YOLOv11 + 透视变换 | 钢铁仓库钢板位置检测 |
| **OCR 识别** | PaddleOCR + YOLO | 车牌、钢板编号识别 |
| **安全区域检测** | 点云处理 + 3D建模 | 作业区域安全监控 |
| **相机管理** | ONVIF 协议 | 工业相机统一管控 |
| **智能分析** | LLM (Ollama) | 复杂场景语义理解 |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI REST API                        │
├─────────────────────────────────────────────────────────────┤
│  API Routes Layer                                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ Device  │ │ Scene   │ │Strategy │ │ Warning │ │ System │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Core Services Layer                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│  │ 视觉检测服务  │ │  OCR识别服务  │ │   相机管理服务        │  │
│  └──────────────┘ └──────────────┘ └──────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Models Layer                                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ YOLOv11 │ │PaddleOCR │ │ 3D Point │ │ ONVIF   │ │ SQLite │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
InsightVision/
├── app/
│   ├── api/                    # API 路由层
│   │   ├── routes/             # 业务路由
│   │   │   ├── bao_steel.py    # 宝钢钢板识别接口
│   │   │   ├── device.py       # 设备管理接口
│   │   │   ├── scene.py       # 场景管理接口
│   │   │   ├── strategy.py    # 策略配置接口
│   │   │   └── warning.py     # 告警管理接口
│   │   └── main.py            # 路由汇总
│   │
│   ├── core/                   # 核心业务逻辑
│   │   ├── config/             # 系统配置
│   │   ├── deploy/             # 模型部署
│   │   │   └── python/         # Python 检测模型
│   │   ├── services/           # 业务服务
│   │   │   ├── bao_steel_services.py
│   │   │   ├── camera_service.py
│   │   │   └── ocr_service.py
│   │   └── func_calc.py        # 函数计算工具
│   │
│   ├── models/                 # 数据模型
│   │   ├── device.py          # 设备模型
│   │   ├── scene.py           # 场景模型
│   │   ├── strategy.py        # 策略模型
│   │   └── warning.py         # 告警模型
│   │
│   ├── schemas/                # Pydantic schemas
│   ├── utils/                  # 工具函数
│   │   ├── scan/              # 扫描识别模块
│   │   └── wsdl/              # ONVIF 协议文件
│   │
│   ├── static/                 # 静态资源
│   │   ├── uploads/           # 上传文件
│   │   ├── ocr_results/       # OCR 结果
│   │   └── steel_output/      # 钢板识别输出
│   │
│   ├── logs/                   # 日志目录
│   ├── cache/                  # 缓存目录
│   │
│   ├── startup.py             # 应用入口
│   ├── requirements.txt       # 依赖清单
│   └── config.json            # 配置文件
│
├── tests/                      # 测试代码
│   ├── integration/           # 集成测试
│   ├── unit/                 # 单元测试
│   ├── test_config.py        # 测试配置
│   └── run_ocr_test.py       # OCR 测试脚本
│
├── docs/                       # 开发文档
│
└── README.md                  # 项目文档
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- CUDA 11.8+ (GPU 加速)
- 8GB+ RAM

### 安装依赖

```bash
cd app
pip install -r requirements.txt
```

### 启动服务

```bash
cd app
python startup.py
```

服务启动后访问：
- API 文档: http://localhost:8001/docs
- ReDoc 文档: http://localhost:8001/redoc

### 运行测试

```bash
# 使用测试脚本
python tests/run_ocr_test.py --config TCP7

# 使用 pytest
pytest tests/integration/test_ocr_integration.py -v
```

## 📡 API 接口

### 钢板识别

```
GET /api/bao_steel/steel_plate
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ip | string | 是 | 相机 IP 地址 |
| park_no | string | 是 | 车位编号 |
| height | int | 否 | 高度阈值 |
| classId | int | 否 | 目标类别 ID |

**响应示例：**

```json
{
  "status": "success",
  "result": {
    "center_1": [1234, 567, 0],
    "center_2": [1234, 567, 0],
    "box": [[0, 0], [200, 0], [200, 150], [0, 150]],
    "width_height": [200, 150],
    "safe_region": {
      "SafetyMaxX": 1500.0,
      "SafetyMinX": 1000.0,
      "SafetyMaxY": 800.0,
      "SafetyMinY": 500.0
    },
    "angle1": 1.5,
    "angle2": -0.8
  },
  "image_native_base64": "...",
  "image_visualize_base64": "..."
}
```

## 🔧 技术栈

### 核心框架

<div align="center">

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.110.2 |
| OCR 引擎 | PaddleOCR | 2.7.3 |
| 目标检测 | YOLOv11 | ultralytics |
| 深度学习 | PaddlePaddle | 2.6.1 |
| 点云处理 | Open3D | 0.18.0 |
| 图像处理 | OpenCV | 4.6.0.66 |

</div>

### 辅助工具

- **数据库**: SQLite + SQLModel
- **相机协议**: ONVIF
- **AI 推理**: Ollama (本地 LLM)
- **日志**: Loguru
- **数据可视化**: Plotly

## 📊 应用场景

### 1. 钢铁仓库 - 钢板识别

![Steel Detection](https://via.placeholder.com/800x400?text=Steel+Plate+Detection)

- 钢板位置与姿态检测
- 钢板尺寸自动测量
- 堆叠状态识别

### 2. 物流园区 - 车牌 OCR

- 车辆进出自动登记
- 车牌号自动识别
- 车辆类型分类

### 3. 安全生产 - 安全区域监控

- 作业区域入侵检测
- 人员安全防护监控
- 异常行为预警

## 🛠️ 开发指南

### 添加新的检测模型

1. 将模型文件放入 `models/` 目录
2. 在 `app/core/deploy/python/` 创建推理脚本
3. 在服务层调用模型进行推理

```python
from app.core.deploy.python.test_infer_steel import init_detector_steel

detector, flags = init_detector_steel()
result = detector.predict(image)
```

### 添加新的 API 路由

1. 在 `app/api/routes/` 创建路由文件
2. 定义 Router 并添加业务逻辑
3. 在 `app/api/main.py` 注册路由

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/your_endpoint")
async def your_function():
    return {"message": "Hello"}
```

## 📝 接口文档

更多接口文档请参考：

- [快速开始指南](tests/QUICKSTART.md)
- [测试文档](tests/README.md)
- [API 测试样例](docs/接口测试样例.txt)

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👥 联系我们

如有问题或建议，请提交 Issue 或联系项目维护者。

---

<div align="center">

**InsightVision** - 让工业视觉更智能

*Built with ❤️ for Industrial Vision*

</div>
