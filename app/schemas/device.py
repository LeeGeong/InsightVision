from pydantic import UUID4, Field
from typing import Optional
from datetime import datetime


class DeviceBase:
    name: str = Field(default="测试设备", description="设备名称")
    ip: str = Field(default="192.168.1.64", description="设备IP地址")
    account: str = Field(default="admin", description="设备账号")
    password: str = Field(default="dhhi123456", description="设备密码")
    scene_id: UUID4 = Field(description="所属场景ID")


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate:
    id: Optional[UUID4] = None
    name: str = Field(default="测试设备", description="设备名称")
    ip: str = Field(default="192.168.1.64", description="设备IP地址")
    password: str = Field(default="dhhi123456", description="设备密码")
    account: str = Field(default="admin", description="设备账号")
    scene_id: UUID4 = Field(description="所属场景ID")


class DeviceResponse:
    id: UUID4 = Field(description="设备ID")
    name: str = Field(description="设备名称")
    ip: str = Field(description="设备IP地址")
    account: str = Field(description="设备账号")
    password: str = Field(description="设备密码")
    scene_id: UUID4 = Field(description="所属场景ID")
    scene_name: str = Field(description="所属场景名称")
    create_time: Optional[datetime] = Field(default=None, description="创建时间")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")


class DeviceQuery:
    device_name: Optional[str] = Field(default="", description="设备名称（模糊查询）")
    scene_name: Optional[str] = Field(default="", description="场景名称（模糊查询）")
