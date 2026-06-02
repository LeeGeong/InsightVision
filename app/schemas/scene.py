from pydantic import UUID4, Field
from typing import Optional
from datetime import datetime


class SceneBase:
    name: str = Field(default="测试区域", description="场景名称")


class SceneCreate(SceneBase):
    pass


class SceneUpdate:
    id: UUID4 = Field(description="场景ID")
    name: str = Field(default="测试区域", description="场景名称")


class SceneResponse:
    id: UUID4 = Field(description="场景ID")
    name: str = Field(description="场景名称")
    create_time: Optional[datetime] = Field(default=None, description="创建时间")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")


class SceneQuery:
    name: Optional[str] = Field(default="", description="场景名称（模糊查询）")
