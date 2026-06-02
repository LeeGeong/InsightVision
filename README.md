<div align="center">

![InsightVision Logo](https://img.shields.io/badge/InsightVision-Industrial%20Vision%20Platform-009688?style=for-the-badge&logo=vision&logoColor=white)

# InsightVision - Industrial Intelligent Vision Platform

*Deep Learning-based Intelligent Vision Recognition System for Industrial Scenarios*

[![Python Version](https://img.shields.io/badge/Python-3.9+-4B8BBE?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.2-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![YOLO](https://img.shields.io/badge/YOLO-v11-FF6B6B?style=flat-square&logo=robot&logoColor=white)](https://github.com/ultralytics/ultralytics)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7.3-2C3E50?style=flat-square)](https://github.com/PaddlePaddle/PaddleOCR)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)]()

---

[English](README.md) | [简体中文](README_zh.md)

</div>

## 📖 Introduction

**InsightVision** is an intelligent vision recognition platform designed for industrial scenarios. It focuses on core functionalities such as steel plate recognition, license plate OCR, and safety zone detection. The system utilizes advanced deep learning algorithms combined with industrial-grade camera management capabilities to provide high-precision, real-time vision solutions for steel, logistics, and other industries.

### 🎯 Core Features

| Feature | Technology | Use Case |
|---------|------------|----------|
| **Steel Plate Recognition** | YOLOv11 + Perspective Transform | Steel warehouse plate positioning |
| **OCR Recognition** | PaddleOCR + YOLO | License plates, plate number recognition |
| **Safety Zone Detection** | Point Cloud Processing + 3D Modeling | Workplace safety monitoring |
| **Camera Management** | ONVIF Protocol | Industrial camera unified control |
| **Intelligent Analysis** | LLM (Ollama) | Complex scene semantic understanding |

## 🏗️ System Architecture

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
│  │Vision Service│ │ OCR Service  │ │  Camera Service      │  │
│  └──────────────┘ └──────────────┘ └──────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Models Layer                                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ YOLOv11 │ │PaddleOCR │ │ 3D Point │ │ ONVIF   │ │ SQLite │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
InsightVision/
├── app/
│   ├── api/                    # API Routes Layer
│   │   ├── routes/             # Business Routes
│   │   │   ├── bao_steel.py    # Baosteel Steel Plate Interface
│   │   │   ├── device.py       # Device Management Interface
│   │   │   ├── scene.py       # Scene Management Interface
│   │   │   ├── strategy.py    # Strategy Configuration Interface
│   │   │   └── warning.py     # Warning Management Interface
│   │   └── main.py            # Route Aggregation
│   │
│   ├── core/                   # Core Business Logic
│   │   ├── config/             # System Configuration
│   │   ├── deploy/             # Model Deployment
│   │   │   └── python/         # Python Detection Models
│   │   ├── services/           # Business Services
│   │   │   ├── bao_steel_services.py
│   │   │   ├── camera_service.py
│   │   │   └── ocr_service.py
│   │   └── func_calc.py        # Function Calculation Utilities
│   │
│   ├── models/                 # Data Models
│   │   ├── device.py          # Device Model
│   │   ├── scene.py           # Scene Model
│   │   ├── strategy.py        # Strategy Model
│   │   └── warning.py         # Warning Model
│   │
│   ├── schemas/                # Pydantic Schemas
│   ├── utils/                  # Utility Functions
│   │   ├── scan/              # Scan Recognition Module
│   │   └── wsdl/              # ONVIF Protocol Files
│   │
│   ├── static/                 # Static Resources
│   │   ├── uploads/           # Uploaded Files
│   │   ├── ocr_results/       # OCR Results
│   │   └── steel_output/      # Steel Plate Recognition Output
│   │
│   ├── logs/                   # Log Directory
│   ├── cache/                  # Cache Directory
│   │
│   ├── startup.py             # Application Entry Point
│   ├── requirements.txt       # Dependencies
│   └── config.json            # Configuration File
│
├── tests/                      # Test Code
│   ├── integration/           # Integration Tests
│   ├── unit/                 # Unit Tests
│   ├── test_config.py        # Test Configuration
│   └── run_ocr_test.py       # OCR Test Script
│
├── docs/                       # Development Documentation
│
└── README.md                  # Project Documentation
```

## 🚀 Quick Start

### Requirements

- Python 3.9+
- CUDA 11.8+ (GPU Acceleration)
- 8GB+ RAM

### Install Dependencies

```bash
cd app
pip install -r requirements.txt
```

### Start Service

```bash
cd app
python startup.py
```

After starting, access:
- API Documentation: http://localhost:8001/docs
- ReDoc Documentation: http://localhost:8001/redoc

### Run Tests

```bash
# Using test script
python tests/run_ocr_test.py --config TCP7

# Using pytest
pytest tests/integration/test_ocr_integration.py -v
```

## 📡 API Interface

### Steel Plate Recognition

```
GET /api/bao_steel/steel_plate
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ip | string | Yes | Camera IP Address |
| park_no | string | Yes | Parking Spot Number |
| height | int | No | Height Threshold |
| classId | int | No | Target Class ID |

**Response Example:**

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

## 🔧 Tech Stack

### Core Frameworks

<div align="center">

| Category | Technology | Version |
|----------|------------|---------|
| Web Framework | FastAPI | 0.110.2 |
| OCR Engine | PaddleOCR | 2.7.3 |
| Object Detection | YOLOv11 | ultralytics |
| Deep Learning | PaddlePaddle | 2.6.1 |
| Point Cloud | Open3D | 0.18.0 |
| Image Processing | OpenCV | 4.6.0.66 |

</div>

### Supporting Tools

- **Database**: SQLite + SQLModel
- **Camera Protocol**: ONVIF
- **AI Inference**: Ollama (Local LLM)
- **Logging**: Loguru
- **Data Visualization**: Plotly

## 📊 Application Scenarios

### 1. Steel Warehouse - Steel Plate Recognition

- Steel plate position and posture detection
- Automatic steel plate dimension measurement
- Stacking state recognition

### 2. Logistics Park - License Plate OCR

- Automatic vehicle entry/exit registration
- Automatic license plate number recognition
- Vehicle type classification

### 3. Production Safety - Safety Zone Monitoring

- Work area intrusion detection
- Personnel safety protection monitoring
- Anomalous behavior early warning

## 🛠️ Development Guide

### Adding New Detection Models

1. Place model files in `models/` directory
2. Create inference scripts in `app/core/deploy/python/`
3. Call the model in the service layer

```python
from app.core.deploy.python.test_infer_steel import init_detector_steel

detector, flags = init_detector_steel()
result = detector.predict(image)
```

### Adding New API Routes

1. Create route file in `app/api/routes/`
2. Define Router and add business logic
3. Register route in `app/api/main.py`

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/your_endpoint")
async def your_function():
    return {"message": "Hello"}
```

## 📝 Documentation

For more documentation:

- [Quick Start Guide](tests/QUICKSTART.md)
- [Test Documentation](tests/README.md)
- [API Test Examples](docs/接口测试样例.txt)

## 🤝 Contributing

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Contact

For questions or suggestions, please submit an Issue or contact the project maintainers.

---

<div align="center">

**InsightVision** - Making Industrial Vision Smarter

*Built with ❤️ for Industrial Vision*

</div>
