from pydantic import Field


class SystemInfo:
    cpu_usage: str = Field(description="CPU使用率")
    memory_usage: str = Field(description="内存使用情况")
    disk_usage: str = Field(description="磁盘使用情况")


class SystemConfigurationBase:
    mqtt_address: str = Field(description="MQTT服务器地址")
    mqtt_port: str = Field(description="MQTT服务器端口")
    mqtt_topic: str = Field(description="MQTT主题")
    image_delete_period: int = Field(description="图片删除周期（天）")


class SystemConfigurationCreate(SystemConfigurationBase):
    pass


class SystemConfigurationUpdate(SystemConfigurationBase):
    pass


class SystemConfigurationResponse(SystemConfigurationBase):
    pass
