from pydantic import UUID4, Field
from typing import Optional
from datetime import datetime


class WarningResponse:
    id: UUID4 = Field(description="预警ID")
    device_id: UUID4 = Field(description="设备ID")
    device_name: str = Field(description="设备名称")
    device_scene_name: str = Field(description="设备所属场景名称")
    strategy_id: UUID4 = Field(description="策略ID")
    strategy_name: str = Field(description="策略名称")
    happen_time: datetime = Field(description="发生时间")
    image_address: str = Field(description="图片地址")


class WarningQuery:
    device_name: Optional[str] = Field(default="", description="设备名称（模糊查询）")
    scene_name: Optional[str] = Field(default="", description="场景名称（模糊查询）")
    strategy_name: Optional[str] = Field(default="", description="策略名称（模糊查询）")
    start_time: Optional[str] = Field(default="", description="开始时间")
    end_time: Optional[str] = Field(default="", description="结束时间")


class WarningChartData:
    strategy_name: str = Field(description="策略名称")
    data: dict = Field(description="预警数据字典，key为日期，value为预警数量")


class WarningChartQuery:
    unit: Optional[str] = Field(default="year", description="时间单位：year|month|week")
