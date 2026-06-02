from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import UUID4, Field


class BaseResponse(BaseModel):
    status: str = Field(description="操作状态")
    message: str = Field(default="", description="消息")


class PaginationQuery(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")


class PaginationResponse(BaseModel):
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")


class ErrorResponse(BaseModel):
    status: str = Field(default="error", description="操作状态")
    message: str = Field(description="错误消息")
    detail: Optional[str] = Field(default=None, description="错误详情")
