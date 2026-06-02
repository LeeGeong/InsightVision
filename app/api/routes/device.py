import uuid
from fastapi import APIRouter, HTTPException
from pydantic import UUID4
from app.api.deps import SessionDep
from app.models.device import Device, ResponsesDevice, UpdateDevice, CreatDevice, device_to_response
from app.models.scene import Scene
from sqlmodel import select
import datetime

router = APIRouter()


@router.get("/read", response_model=list[ResponsesDevice])
async def read_device(session: SessionDep, device_name: str = "", scene_name: str = ""):
    """
    Get All Devices.
    """
    statement = select(Device).join(Scene)
    if device_name:
        statement = statement.where(Device.name.like(f"%{device_name}%"))
    if scene_name:
        statement = statement.where(Scene.name.like(f"%{scene_name}%"))
    result = session.exec(statement)
    if not result:
        raise HTTPException(status_code=404, detail="Devices not found")
    else:
        result_list = [device_to_response(r) for r in result]
        # for r in result:
        #     res = ResponsesDevice(
        #         id=r.id,
        #         name=r.name,
        #         ip=r.ip,
        #         account=r.account,
        #         password=r.password,
        #         scene_id=r.scene_id,
        #         scene_name=r.parent_scene.name
        #     )
        #     result_list.append(res)
    return result_list


@router.post("/create", response_model=list[ResponsesDevice])
async def create_device(session: SessionDep, current_device: CreatDevice):
    """
    Create new Devices.
    """

    # current_device.id = uuid.uuid4()
    # a = current_device.model_dump(by_alias=True)
    # a["scene_id"] = a.pop("senceId")
    # result = Device.model_validate(a)

    result = Device.model_validate(current_device,
                                update={"update_time": datetime.datetime.now().replace(microsecond=0),
                                        "id":uuid.uuid4()})
    session.add(result)
    session.commit()
    session.refresh(result)
    result_list = [device_to_response(result)]
    return result_list


@router.post("/update", response_model=list[ResponsesDevice])
async def update_device(session: SessionDep, current_device: UpdateDevice):
    """
    Update new Devices.
    """
    result = session.get(Device, current_device.id)
    if not result:
        # 如果找不到对应的场景，抛出HTTP 404错误
        raise HTTPException(status_code=404, detail="Scene not found")
    # 更新场景的name字段
    result.name = current_device.name
    result.ip = current_device.ip
    result.password = current_device.password
    result.account = current_device.account
    result.scene_id = current_device.scene_id
    session.commit()
    session.refresh(result)
    result_list = [device_to_response(result)]
    return result_list



@router.delete("/delete")
async def delete_device(session: SessionDep, id: UUID4):
    """
    Delete Devices by ID.
    """
    result = session.get(Device, id)
    if not result:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(result)
    session.commit()
    return "success"
