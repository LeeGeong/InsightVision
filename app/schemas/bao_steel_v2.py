"""
宝钢接口请求/响应模型 V2

定义所有 API 请求和响应的 Pydantic 模型

开发者: JJH
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==================== 物料信息 ====================

class MatInfo(BaseModel):
    """物料信息"""
    mat_no: str = Field(..., description="喷码编号")
    mat_length: float = Field(default=0, description="长度")
    mat_width: float = Field(default=0, description="宽度")
    mat_height: float = Field(default=0, description="高度")
    mat_weight: float = Field(default=0, description="重量")
    mat_manufactor: str = Field(default="", description="厂家")


# ==================== OCR 识别请求 ====================

class BarcodeOcrRequest(BaseModel):
    """
    喷码识别请求
    
    用于宝钢钢板库喷码识别接口
    """
    park_no: str = Field(..., description="车位号，如 TCP7")
    mat_infos: List[MatInfo] = Field(default_factory=list, description="物料信息列表")
    file_path: str = Field(default="", description="点云文件路径（可选）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "park_no": "TCP7",
                "mat_infos": [
                    {
                        "mat_no": "6406229200",
                        "mat_length": 10000,
                        "mat_width": 2000,
                        "mat_height": 20,
                        "mat_weight": 3.14,
                        "mat_manufactor": "宝钢"
                    }
                ],
                "file_path": "Z:\\ScanData\\TCP7_20260413.ply"
            }
        }


# ==================== OCR 识别结果 ====================

class OcrResult(BaseModel):
    """单个喷码识别结果"""
    Ocr_Manufactor: str = Field(default="", description="OCR 钢板厂家")
    Ocr_BatchNo: str = Field(default="", description="OCR 钢板批号（喷码）")
    Ocr_Length: float = Field(default=0, description="OCR 钢板长度")
    Ocr_Width: float = Field(default=0, description="OCR 钢板宽度")
    Ocr_Height: float = Field(default=0, description="OCR 钢板高度")
    Ocr_Weight: float = Field(default=0, description="OCR 钢板重量")
    Ocr_Code: str = Field(default="", description="OCR 钢板编号")
    Priority: int = Field(default=0, description="优先级")
    box: List[List[int]] = Field(default_factory=list, description="检测框坐标")
    status: str = Field(default="success", description="状态: success/error")
    message: str = Field(default="", description="消息")
    image_base64_detail: str = Field(default="", description="图片 Base64 编码")


class BarcodeOcrResponse(BaseModel):
    """
    喷码识别响应
    """
    status: str = Field(default="success", description="整体状态")
    message: str = Field(default="", description="整体消息")
    results: List[OcrResult] = Field(default_factory=list, description="识别结果列表")
    time_usage: float = Field(default=0, description="总耗时（秒）")
    time_stats: Dict[str, float] = Field(default_factory=dict, description="耗时统计")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "",
                "results": [
                    {
                        "Ocr_Manufactor": "",
                        "Ocr_BatchNo": "6406229200",
                        "Ocr_Length": 10000,
                        "Ocr_Width": 2000,
                        "Ocr_Height": 20,
                        "Ocr_Weight": 3.14,
                        "Ocr_Code": "",
                        "Priority": 0,
                        "box": [[1560, 31606], [1622, 31606], [1621, 31691], [1559, 31691]],
                        "status": "success",
                        "message": "喷码验证成功",
                        "image_base64_detail": "base64..."
                    }
                ],
                "time_usage": 17.89,
                "time_stats": {
                    "camera_setup": 0.0,
                    "camera_shooting": 4.83,
                    "ocr_processing": 13.11
                }
            }
        }


# ==================== 钢板识别请求 ====================

class SteelPlateRequest(BaseModel):
    """
    钢板识别请求参数
    
    用于宝钢钢板库钢板识别接口
    """
    ip: str = Field(default="192.168.1.64", description="相机 IP 地址")
    file_path: str = Field(default="", description="点云文件路径")
    park_no: str = Field(default="", description="车位号")
    height: int = Field(default=0, description="高度（可选，会自动计算）")
    classId: int = Field(default=1, description="类别 ID")
    task_id: str = Field(default="", description="任务 ID")


# ==================== 钢板识别结果 ====================

class SteelPlateResult(BaseModel):
    """钢板识别结果"""
    center_1: List[float] = Field(default_factory=list, description="图像识别中心点")
    center_2: List[float] = Field(default_factory=list, description="点云识别中心点")
    box: List[List[float]] = Field(default_factory=list, description="画框三维坐标")
    box_native: List[List[float]] = Field(default_factory=list, description="画框二维坐标")
    safe_region: Dict[str, Any] = Field(default_factory=dict, description="安全区域")
    angle1: float = Field(default=0, description="上边缘角度")
    angle2: float = Field(default=0, description="下边缘角度")
    width_height: List[int] = Field(default_factory=list, description="图像宽高")


class SteelPlateResponse(BaseModel):
    """
    钢板识别响应
    """
    status: str = Field(default="success", description="状态")
    message: str = Field(default="", description="消息")
    height: float = Field(default=0, description="计算高度")
    result: SteelPlateResult = Field(default_factory=SteelPlateResult, description="识别结果")
    image_native_base64: str = Field(default="", description="原始图片 Base64")
    image_visualize_base64: str = Field(default="", description="可视化图片 Base64")
    time_usage: float = Field(default=0, description="总耗时（秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "",
                "height": 2300,
                "result": {
                    "center_1": [960, 540],
                    "center_2": [960, 540, 2300],
                    "box": [[0, 0, 0], [100, 0, 0], [100, 100, 0], [0, 100, 0]],
                    "box_native": [[100, 200], [300, 200], [300, 400], [100, 400]],
                    "safe_region": {},
                    "angle1": 0.5,
                    "angle2": -0.3,
                    "width_height": [3840, 2160]
                },
                "image_native_base64": "base64...",
                "image_visualize_base64": "base64...",
                "time_usage": 5.23
            }
        }


# ==================== 车高识别 ====================

class CarHeightRequest(BaseModel):
    """车高识别请求"""
    park_no: str = Field(..., description="车位号")
    file_path: str = Field(..., description="点云文件路径")


class CarHeightResponse(BaseModel):
    """车高识别响应"""
    status: str = Field(default="success", description="状态")
    height: float = Field(default=0, description="高度")
    message: str = Field(default="", description="消息")


# ==================== 通用响应 ====================

class ErrorResponse(BaseModel):
    """错误响应"""
    status: str = Field(default="error", description="状态")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(default=None, description="详细信息")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(default="ok", description="状态")
    version: str = Field(default="1.0.0", description="版本")
    timestamp: str = Field(default="", description="时间戳")


if __name__ == "__main__":
    print("宝钢接口请求/响应模型")
    print("=" * 50)
    
    # 测试请求模型
    request = BarcodeOcrRequest(
        park_no="TCP7",
        mat_infos=[
            MatInfo(mat_no="6406229200", mat_length=10000, mat_width=2000)
        ]
    )
    print(f"请求模型: {request.model_dump_json(indent=2)}")
    
    # 测试响应模型
    response = BarcodeOcrResponse(
        status="success",
        results=[
            OcrResult(Ocr_BatchNo="6406229200", status="success", message="喷码验证成功")
        ],
        time_usage=17.89
    )
    print(f"响应模型: {response.model_dump_json(indent=2)}")
