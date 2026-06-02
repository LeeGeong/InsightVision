from app.api.deps import SessionDep
from fastapi import APIRouter, HTTPException
from app.models.system import SystemConfiguration, SystemInfo, CreateUpdateSystemConfiguration
from sqlmodel import select
import psutil



router = APIRouter()


@router.get("/info", response_model=list[SystemInfo])
async def read_system_info(session: SessionDep):
    """
    获取系统当前信息
    Args:
    Returns:
    """
    # 获取CPU状态
    cpu_percent: str = psutil.cpu_percent(1)  # 1秒间隔获取CPU使用率
    # print(f"CPU状态: {cpu_percent}%")

    # 获取内存占用
    memory_usage = psutil.virtual_memory()
    total_memory = memory_usage.total / 1024 ** 2  # 转换为MB
    used_memory: str = memory_usage.used / 1024 ** 2
    memory_percent = used_memory / total_memory
    # print(f"内存占用: 总共{total_memory:.2f} MB, 已使用{used_memory:.2f} MB, 剩余{total_memory - used_memory:.2f} MB")

    # 获取硬盘容量
    disk_usage = psutil.disk_usage('/')  # 根目录的硬盘使用情况
    total_disk = disk_usage.total / 1024 ** 3  # 转换为GB
    used_disk: str = disk_usage.used / 1024 ** 3
    disk_percent = used_disk / total_disk
    # print(f"硬盘容量: 总共{total_disk:.2f} GB, 已使用{used_disk:.2f} GB, 剩余{total_disk - used_disk:.2f} GB")
    response = SystemInfo(cpu_usage=str(cpu_percent), memory_usage=str(memory_percent), disk_usage=str(disk_percent))
    response_list = [response]
    return response_list


@router.get("/configuration", response_model=list[SystemConfiguration])
async def read_system_configuration(session: SessionDep):
    """
    Get configuration.
    """
    statement = select(SystemConfiguration)
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="configuration not found")
    result_list = [result]
    return result_list


@router.post("/configuration", response_model=list[SystemConfiguration])
async def create_update_system_configuration(session: SessionDep, current_device: CreateUpdateSystemConfiguration):
    """
    Create or update configuration.
    """
    result = session.exec(select(SystemConfiguration)).first()
    if result:
        result.mqtt_address = current_device.mqtt_address
        result.mqtt_port = current_device.mqtt_port
        result.mqtt_topic = current_device.mqtt_topic
        result.image_delete_period = current_device.image_delete_period
    else:
        result = SystemConfiguration.model_validate(current_device)
        session.add(result)
    session.commit()
    session.refresh(result)
    result_list = [result]
    return result_list
