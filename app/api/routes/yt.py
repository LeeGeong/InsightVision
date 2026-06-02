from fastapi import APIRouter, HTTPException, Request
from app.models.yt import EquipmentCode
from app.api.deps import SessionDep
from app.api.routes.artificial_intelligence import get_device_info
import random
import json
import base64
import cv2
router = APIRouter()
from app.core.deploy.python import infer_qr
detector_qr, FLAGS = infer_qr.init_detector_qr()


@router.post("/hookIdentify")
async def hook_identify(session: SessionDep, request: Request, eqCode:EquipmentCode):
    """
    {
        "eqCode": "ECraneA01" // 设备名称
    }
    响应：
    {
        "ok": 0, // 拍照、识别是否成功，枚举，
        "isHookSuccess": true, // 是否挂钩成功
        "imgLeft": "string", // 左侧照片，base64编码的字符串
        "imgRight": "string", // 右侧照片，base64编码的字符串
    }
    """
    # 获取请求体内容
    request_body = await request.json()
    # 打印请求体内容
    print("Received POST request body:")
    print(json.dumps(request_body, indent=4))
    res = {
        "ok": random.choice([0,1]),
        "isHookSuccess": random.choice([True,False]),
        "imgLeft": "string",
        "imgRight": "string",
    }
    img_list = ["static/20240717/images/playback_192.168.0.64_08_20240716151040574.jpeg"]
    with open(img_list[0], "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode('utf-8')
        res['imgLeft'] = encoded_string
        res['imgRight'] = encoded_string
    return res


@router.post("/unhookIdentify")
async def unhook_identify(session: SessionDep, request: Request, eqCode:EquipmentCode):
    """
    {
     "eqCode": "ECraneA01" // 设备名称
    }
    响应：
    {
     "ok": 0, // 拍照是否成功，枚举，
     "imgLeft": "string", // 左侧照片，base64编码的字符串
     "imgRight": "string", // 右侧照片，base64编码的字符串
    }
    """
    # 获取请求体内容
    request_body = await request.json()
    # 打印请求体内容
    print("Received POST request body:")
    print(json.dumps(request_body, indent=4))
    img_list = ["static/20240717/images/playback_192.168.0.64_08_20240716151040574.jpeg"]
    res = {
        "ok": random.choice([0,1]),
        "imgLeft": "string",
        "imgRight": "string",
    }
    with open(img_list[0], "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode('utf-8')
        res['imgLeft'] = encoded_string
        res['imgRight'] = encoded_string
    return res


@router.post("/packCodeIdentify")
async def packcode_identify(session: SessionDep, request: Request, eqCode:EquipmentCode):
    """
    {
     "eqCode": "E80T01" // 设备名称
    }
    响应：
    {
     "ok": 0, // 识别是否成功，枚举，
     "packCode": "0001", // 渣包编号，字符串
    }
    """
    # 获取请求体内容
    request_body = await request.json()
    # 打印请求体内容
    print("Received POST request body:")
    print(json.dumps(request_body, indent=4))
    res = {
        "ok": random.choice([0,1]),
        "packCode": "0000",
    }

    eqCode = request_body["eqCode"]
    account, password, ip = get_device_info(session, device_name=eqCode)
    rtsp = "rtsp://%s:%s@%s:554/Streaming/Channels/101" % (account, password, ip)
    cap = cv2.VideoCapture(rtsp)
    if not cap.isOpened():
        print("无法打开相机")
        res["ok"] = 0
        return res
    # 获取一帧图像
    ret, frame = cap.read()
    # 关闭摄像头
    cap.release()
    if ret:
        img_list = [frame[:, :, ::-1]]
        cv2.imwrite("static/qrcode.jpg", frame)
    else:
        print("无法捕获图像。")
        res["ok"] = 0
        return res
    img_list = ["F:/20240801-DHHI-InsightCore/app/static/123.jpg"]
    try:
        img, text, bbox = infer_qr.predict_image(detector_qr, img_list, FLAGS.batch_size)
    except Exception as e:
        print(e)
        res["ok"] = 0
        return res

    res["packCode"] = text
    return res

