"""
宝钢接口路由 V2（简化版示例）

展示如何使用新的服务层和 schemas 重构路由

开发者: JJH

使用说明:
    1. 此文件为示例文件，展示重构后的代码风格
    2. 原有 bao_steel.py 保持不变，可逐步迁移
    3. 在 main.py 中添加: from .routes.bao_steel_v2 import router as bao_steel_v2_router
    4. 注册路由: api_router.include_router(bao_steel_v2_router, prefix="/bao_steel_v2", tags=["宝钢接口V2"])
"""
import base64
import time
from typing import Dict, Any

import cv2
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import SessionDep
from app.log import logger
from app.core.config.settings_v2 import settings
from app.core.services.camera_service import (
    CameraService, 
    PerspectiveService,
    get_camera_service,
    get_perspective_service
)
from app.core.services.ocr_service import (
    OCRService, 
    YoloDetectionService,
    get_ocr_service
)
from app.schemas.bao_steel_v2 import (
    BarcodeOcrRequest,
    BarcodeOcrResponse,
    OcrResult,
    SteelPlateRequest,
    SteelPlateResponse,
    SteelPlateResult,
    CarHeightResponse,
    ErrorResponse
)


router = APIRouter()


# ==================== 依赖注入 ====================

def get_camera_svc(session: SessionDep) -> CameraService:
    return get_camera_service(session)


def get_perspective_svc() -> PerspectiveService:
    return get_perspective_service()


def get_ocr_svc() -> OCRService:
    return get_ocr_service()


# ==================== 喷码识别接口 ====================

@router.post(
    "/barcode_ocr",
    response_model=BarcodeOcrResponse,
    responses={
        200: {"description": "识别成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"}
    },
    summary="喷码识别",
    description="对指定车位的钢板进行喷码 OCR 识别"
)
async def barcode_ocr(
    session: SessionDep,
    request_data: BarcodeOcrRequest,
    request_mode: int = Query(default=0, description="请求模式: 0=自动, 1=人工"),
    height: int = Query(default=2300, description="高度"),
    task_id: str = Query(default="", description="任务ID")
):
    """
    喷码识别接口（简化版）
    
    流程:
        1. 获取相机图像
        2. 执行 YOLO 检测
        3. 对每个检测框执行 OCR
        4. 验证并返回结果
    
    Args:
        session: 数据库会话
        request_data: 请求体
        request_mode: 请求模式
        height: 高度
        task_id: 任务ID
    
    Returns:
        BarcodeOcrResponse: 识别结果
    """
    start_time = time.time()
    
    logger.info(f"接口请求: POST /barcode_ocr_v2, 参数: request_mode={request_mode}, height={height}, task_id={task_id}")
    logger.info(f"请求 body: {request_data.model_dump()}")
    
    # 初始化响应
    response = BarcodeOcrResponse(
        status="success",
        message="",
        results=[],
        time_stats={}
    )
    
    try:
        # 1. 初始化服务
        camera_service = get_camera_svc(session)
        perspective_service = get_perspective_svc()
        ocr_service = get_ocr_svc()
        
        # 2. 准备物料信息
        if request_data.mat_infos:
            mat_infos_df = pd.DataFrame([m.model_dump() for m in request_data.mat_infos])
        else:
            mat_infos_df = pd.DataFrame()
        
        # 3. 获取相机 IP（根据 park_no 查询）
        ip = _get_ip_by_park_no(request_data.park_no)
        
        # 4. 获取图像
        stage_start = time.time()
        status, msg, camera_img = camera_service.capture_from_ip(ip)
        response.time_stats["camera_shooting"] = time.time() - stage_start
        
        if not status:
            response.status = "error"
            response.message = msg
            return response
        
        # 5. 透视变换
        stage_start = time.time()
        perspective_img, width, height_p = perspective_service.apply_perspective_warp(camera_img, ip)
        response.time_stats["perspective_warp"] = time.time() - stage_start
        
        # 6. YOLO 检测
        stage_start = time.time()
        detections = YoloDetectionService.detect(perspective_img)
        response.time_stats["yolo_detection"] = time.time() - stage_start
        
        logger.info(f"检测到 {len(detections)} 个喷码")
        
        if not detections:
            response.status = "success"
            response.message = "未检测到喷码"
            return response
        
        # 7. 按距离中心排序
        image_center_x = perspective_img.shape[1] / 2
        image_center_y = perspective_img.shape[0] / 2
        detections.sort(
            key=lambda x: ((x["center"][0] - image_center_x) ** 2 + (x["center"][1] - image_center_y) ** 2) ** 0.5
        )
        
        # 8. 处理每个检测框
        for i, detection in enumerate(detections):
            logger.info(f"处理第 {i + 1} 个喷码 (置信度: {detection['confidence']:.2f})")
            
            # 创建结果
            result = OcrResult(
                box=detection.get("box_points", []),
                status="success",
                message=f"第 {i + 1} 个喷码处理中",
                Priority=i
            )
            
            try:
                # 移动相机到喷码位置
                zoom_level = camera_service.calculate_zoom_level(detection, height)
                camera_service.move_to_position(
                    ip, 
                    detection["center"][0],
                    detection["center"][1],
                    height,
                    zoom_level
                )
                time.sleep(6)  # 等待相机稳定
                
                # 获取放大后的图像
                rtsp = camera_service.get_rtsp_url(ip)
                status, msg, detail_img = camera_service.capture_image(rtsp)
                
                if status:
                    # OCR 识别
                    stage_start = time.time()
                    ocr_results = ocr_service.process_image(detail_img)
                    response.time_stats["ocr_processing"] = response.time_stats.get("ocr_processing", 0) + (time.time() - stage_start)
                    
                    # 编码图片用于 Ollama
                    _, img_encoded = cv2.imencode('.jpg', detail_img)
                    img_bytes = img_encoded.tobytes()
                    
                    # 验证结果
                    if not mat_infos_df.empty:
                        _, result_dict = ocr_service.verify_batch(ocr_results, mat_infos_df, img_bytes)
                        result.Ocr_BatchNo = result_dict.get("Ocr_BatchNo", "")
                        result.status = result_dict.get("status", "error")
                        result.message = result_dict.get("message", "")
                    
                    # 编码图片
                    result.image_base64_detail = base64.b64encode(img_bytes).decode("utf-8")
                
            except Exception as e:
                logger.error(f"处理喷码异常: {str(e)}")
                result.status = "error"
                result.message = f"处理异常: {str(e)}"
            
            response.results.append(result)
        
        # 9. 应用过滤算法
        response_dict = response.model_dump()
        from app.core.func_calc import filtering_algorithm
        response_dict = filtering_algorithm(response_dict)
        response = BarcodeOcrResponse(**response_dict)
        
    except Exception as e:
        logger.error(f"喷码识别异常: {str(e)}")
        response.status = "error"
        response.message = str(e)
    
    finally:
        response.time_usage = round(time.time() - start_time, 3)
    
    return response


# ==================== 钢板识别接口 ====================

@router.get(
    "/steel_plate",
    response_model=SteelPlateResponse,
    summary="钢板识别",
    description="对指定车位的钢板进行识别"
)
async def steel_plate(
    session: SessionDep,
    ip: str = Query(default="192.168.1.64", description="相机IP"),
    file_path: str = Query(default="", description="点云文件路径"),
    park_no: str = Query(default="", description="车位号"),
    height: int = Query(default=0, description="高度"),
    classId: int = Query(default=1, description="类别ID"),
    task_id: str = Query(default="", description="任务ID")
):
    """
    钢板识别接口（简化版）
    """
    start_time = time.time()
    
    logger.info(f"接口请求: GET /steel_plate_v2, 参数: ip={ip}, file_path={file_path}, park_no={park_no}, height={height}, classId={classId}, task_id={task_id}")
    
    response = SteelPlateResponse(
        status="success",
        message="",
        height=height,
        result=SteelPlateResult()
    )
    
    try:
        camera_service = get_camera_svc(session)
        perspective_service = get_perspective_svc()
        
        # 获取图像
        status, msg, camera_img = camera_service.capture_from_ip(ip)
        
        if not status:
            response.status = "error"
            response.message = msg
            return response
        
        # 透视变换
        perspective_img, width, height_p = perspective_service.apply_perspective_warp(camera_img, ip)
        
        # TODO: 实现钢板识别逻辑
        
    except Exception as e:
        logger.error(f"钢板识别异常: {str(e)}")
        response.status = "error"
        response.message = str(e)
    
    finally:
        response.time_usage = round(time.time() - start_time, 3)
    
    return response


# ==================== 车高识别接口 ====================

@router.get(
    "/car_height",
    response_model=CarHeightResponse,
    summary="车高识别",
    description="根据点云文件计算车辆高度"
)
async def car_height(
    park_no: str = Query(..., description="车位号"),
    file_path: str = Query(..., description="点云文件路径")
):
    """
    车高识别接口
    """
    logger.info(f"接口请求: GET /car_height_v2, 参数: park_no={park_no}, file_path={file_path}")
    
    try:
        from app.utils.scan import recognize_car_height
        
        height = recognize_car_height(file_path)
        
        return CarHeightResponse(
            status="success",
            height=height,
            message="高度计算成功"
        )
        
    except Exception as e:
        logger.error(f"车高识别异常: {str(e)}")
        return CarHeightResponse(
            status="error",
            height=0,
            message=str(e)
        )


# ==================== 辅助函数 ====================

def _get_ip_by_park_no(park_no: str) -> str:
    """
    根据车位号获取相机 IP
    
    Args:
        park_no: 车位号
    
    Returns:
        str: 相机 IP
    """
    # TODO: 从数据库或配置中查询
    park_ip_mapping = {
        "TCP7": "192.168.3.65",
        "TCP6": "192.168.3.68",
        "TPC6": "192.168.3.68",
        "TPC7": "192.168.3.65",
    }
    
    return park_ip_mapping.get(park_no, "192.168.3.65")


# ==================== 健康检查 ====================

@router.get("/health", summary="健康检查")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "version": settings.app.API_VERSION,
        "debug": settings.app.DEBUG
    }


if __name__ == "__main__":
    print("宝钢接口路由 V2（简化版示例）")
    print("=" * 50)
    print("主要改进:")
    print("  1. 使用 Pydantic 模型定义请求/响应")
    print("  2. 使用服务层封装业务逻辑")
    print("  3. 使用依赖注入管理服务实例")
    print("  4. 统一异常处理和日志记录")
    print()
    print("使用方式:")
    print("  在 main.py 中添加:")
    print("  from .routes.bao_steel_v2 import router as bao_steel_v2_router")
    print("  api_router.include_router(bao_steel_v2_router, prefix='/bao_steel_v2', tags=['宝钢接口V2'])")
