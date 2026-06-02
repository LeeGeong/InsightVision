from pydantic import Field
from typing import Optional, List, Dict, Any


class SteelPlateRequest:
    ip: str = Field(default="192.168.1.64", description="相机IP地址")
    file_path: str = Field(default="", description="点云数据文件路径")
    park_no: str = Field(default="", description="停车位编号")
    height: int = Field(default=0, description="高度值")
    classId: int = Field(default=1, description="类别ID")


class SteelPlateResult:
    center_1: List[float] = Field(default=[0, 0, 0], description="图像识别中心点坐标")
    center_2: List[float] = Field(default=[0, 0, 0], description="点云识别中心点坐标")
    box: List[List[float]] = Field(default=[[0, 0], [0, 0], [0, 0], [0, 0]], description="画框三维坐标")
    box_native: List[List[float]] = Field(default=[[0, 0], [0, 0], [0, 0], [0, 0]], description="画框二维坐标")
    width_height: List[float] = Field(default=[0, 0], description="宽度和高度")
    perspective_box: List[List[float]] = Field(default=[[0, 0], [0, 0], [0, 0], [0, 0]], description="透视变换框")
    perspective_box_native: List[List[float]] = Field(default=[[0, 0], [0, 0], [0, 0], [0, 0]], description="透视变换框原始坐标")
    safe_region: Dict[str, float] = Field(default={
        "SafetyMaxX": 0.0,
        "SafetyMinX": 0.0,
        "SafetyMaxY": 0.0,
        "SafetyMinY": 0.0
    }, description="安全区域坐标")
    angle1: float = Field(default=0.0, description="上边缘角度")
    angle2: float = Field(default=0.0, description="下边缘角度")


class SteelPlateResponse:
    status: str = Field(description="操作状态")
    message: str = Field(default="", description="消息")
    result: SteelPlateResult = Field(description="识别结果")
    image_native_base64: str = Field(default="", description="原始图片Base64编码")
    image_visualize_base64: str = Field(default="", description="可视化图片Base64编码")
    time_usage: float = Field(default=0.0, description="总耗时")


class CameraImageRequest:
    ip: str = Field(default="192.168.1.64", description="相机IP地址")


class CameraImageResponse:
    status: str = Field(description="操作状态")
    image_base64: str = Field(default="", description="图片Base64编码")


class CarHeightRequest:
    park_no: str = Field(default="", description="停车位编号")
    file_path: str = Field(default="", description="点云数据文件路径")


class CarHeightResponse:
    status: str = Field(description="操作状态")
    height: float = Field(default=0.0, description="高度值")
    message: str = Field(default="", description="消息")


class SafeRegionRequest:
    file_path: str = Field(default="", description="点云数据文件路径")
    points: str = Field(default="[23.2, 90.14, 1.97]", description="点坐标字符串")


class SafeRegionResponse:
    safe_area: Dict[str, float] = Field(description="安全区域坐标")


class TruckAreaRequest:
    file_path: str = Field(default="", description="点云数据文件路径")


class TruckAreaResponse:
    truck_area: Dict[str, Any] = Field(description="卡车区域信息")


class OffsetRequest:
    file_path: str = Field(default="", description="点云数据文件路径")
    equipment_number: str = Field(default="", description="设备编号")
    length: int = Field(default=0, description="长度")
    width: int = Field(default=0, description="宽度")
    lifiting_height: int = Field(default=0, description="起升高度")
    magnet_offset: int = Field(default=0, description="磁铁偏移")


class OffsetResponse:
    offset_info: Dict[str, Any] = Field(description="偏移信息")


class AlignAndCrosserRequest:
    park_no: str = Field(default="", description="停车位编号")
    file_path: str = Field(default="", description="点云数据文件路径")
    frame_type: int = Field(default=0, description="框架类型")
    empty_statu: int = Field(default=0, description="空车状态")


class AlignAndCrosserResponse:
    align_crosser_info: Dict[str, Any] = Field(description="对齐和横梁信息")


class HeightDifferenceRequest:
    file_path: str = Field(default="", description="点云数据文件路径")
    angle_points: str = Field(default="[[29573, 416296], [28957, 418269], [36490, 418240], [37145, 416207]]", description="角度点字符串")


class HeightDifferenceResponse:
    height_difference_info: Dict[str, Any] = Field(description="高度差信息")


class EmptyCarPositionRequest:
    file_path: str = Field(default="", description="点云数据文件路径")
    park_no: str = Field(default="", description="停车位编号")
    car_type: int = Field(default=0, description="车辆类型")


class EmptyCarPositionResponse:
    empty_car_info: Dict[str, Any] = Field(description="空车位置信息")


class BarcodeOcrRequest:
    image_base64: str = Field(description="图片Base64编码")


class BarcodeOcrResponse:
    status: str = Field(description="操作状态")
    barcode: str = Field(default="", description="条码内容")
    message: str = Field(default="", description="消息")
