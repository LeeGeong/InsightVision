from pydantic import UUID4, Field
from typing import Optional
from datetime import datetime


class StrategyBase:
    name: str = Field(default="测试模型", description="策略名称")
    key: str = Field(default="csmx", description="策略键值")


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate:
    id: UUID4 = Field(description="策略ID")
    name: str = Field(description="策略名称")
    key: str = Field(description="策略键值")


class StrategyResponse:
    id: UUID4 = Field(description="策略ID")
    name: str = Field(description="策略名称")
    key: str = Field(description="策略键值")
    create_time: Optional[datetime] = Field(default=None, description="创建时间")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")


class StrategyQuery:
    name: Optional[str] = Field(default="", description="策略名称（模糊查询）")


class DeviceStrategyBinding:
    strategy_id: UUID4 = Field(description="策略ID")
    device_id: Optional[list[UUID4]] = Field(default=None, description="设备ID列表")


class StrategyEnableDisable:
    total_strategy: int = Field(description="总策略数")
    enable_strategy: int = Field(description="已启用策略数")
