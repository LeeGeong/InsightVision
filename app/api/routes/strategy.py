from pydantic import UUID4
from app.api.deps import SessionDep
from fastapi import APIRouter, HTTPException
from app.models.strategy import Strategy, CreatStrategy, UpdateStrategy
from app.models.device import Device
from app.models.device_strategy import DeviceStrategy, RequireResponseBinding, enable_disable
from sqlmodel import select
import datetime
import uuid
from sqlalchemy import func


router = APIRouter()
details = "strategy not found"


@router.post("/create", response_model=list[Strategy])
async def create_strategy(session: SessionDep, current_strategy: CreatStrategy):
    """
    Create new Strategy.
    """
    result = Strategy.model_validate(current_strategy,
                                     update={"update_time": datetime.datetime.now().replace(microsecond=0),
                                             "id": uuid.uuid4()})
    if not result:
        raise HTTPException(status_code=404, detail=details)
    session.add(result)
    session.commit()
    session.refresh(result)
    result_list = [result]
    return result_list


@router.post("/update", response_model=list[Strategy])
async def update_strategy(session: SessionDep, current_strategy: UpdateStrategy):
    """
    Update Strategy.
    """
    result = session.get(Strategy, current_strategy.id)
    if not result:
        raise HTTPException(status_code=404, detail=details)
    result.name = current_strategy.name
    result.key = current_strategy.key
    result.update_time = datetime.datetime.now().replace(microsecond=0)
    session.commit()
    session.refresh(result)
    result_list = [result]
    return result_list


@router.get("/read", response_model=list[Strategy])
async def read_strategy(session: SessionDep, name: str = ""):
    """
    Get Strategy by ID.
    """
    statement = select(Strategy)
    if name:
        statement = statement.where(Strategy.name.like(f"%{name}%"))
    result = session.exec(statement).all()
    # result 一直有值，没法判断查询为空
    if not result:
        return []
        # raise HTTPException(status_code=404, detail=details)
    return result


@router.delete("/delete")
async def delete_strategy(session: SessionDep, id: UUID4):
    """
    Delete Strategy by ID.
    """
    result = session.get(Strategy, id)
    if not result:
        # return []
        raise HTTPException(status_code=404, detail=details)
    session.delete(result)
    session.commit()
    return "success"


@router.post("/binding_info")
async def change_binding_info(session: SessionDep, current_binding: RequireResponseBinding):
    """
    设备策略绑定信息修改
    Args:
    Returns:
    """

    statement = select(DeviceStrategy).join(Device).join(Strategy)
    statement = statement.where(DeviceStrategy.strategy_id == current_binding.strategy_id)
    result = session.exec(statement).all()
    if result:
        for r in result:
            session.delete(r)
            session.commit()
    if current_binding.device_id:
        for device_id in current_binding.device_id:
            result = DeviceStrategy(id=uuid.uuid4(), device_id=device_id, strategy_id=current_binding.strategy_id)
            session.add(result)
            session.commit()
            session.refresh(result)
    # statement = select(DeviceStrategy).join(Device).join(Strategy)
    # statement = statement.where(DeviceStrategy.strategy_id == current_binding.strategy_id)
    # if current_binding.device_id:
    #     statement = statement.where(DeviceStrategy.device_id in current_binding.device_id)
    # result = session.exec(statement).all()
    # if not result:
    #     raise HTTPException(status_code=404, detail=details)
    # result.name = current_strategy.name
    # result.key = current_strategy.key
    # result.update_time = datetime.datetime.now().replace(microsecond=0)
    # session.commit()
    # session.refresh(result)
    # result_list = [result]
    return "success"


@router.get("/binding_info", response_model=list[RequireResponseBinding])
async def read_binding_info(session: SessionDep, strategy_id: UUID4):
    """
    通过 strategy_id 获取设备策略绑定信息
    Args:
    Returns:
    """
    statement = select(DeviceStrategy)
    # strategy_id = uuid.UUID(strategy_id)
    # if strategy_id:
    statement = statement.where(DeviceStrategy.strategy_id == strategy_id)
    result = session.exec(statement).all()
    # else:
    #     raise HTTPException(status_code=404, detail=details)
    # result 一直有值，没法判断查询为空
    if not result:
        return []
        # raise HTTPException(status_code=404, detail=details)
    else:
        response = RequireResponseBinding(strategy_id=strategy_id, device_id=[r.device_id for r in result])
    result_list = [response]
    return result_list


@router.get("/enable_disable", response_model=list[enable_disable])
async def read_binding_info(session: SessionDep):
    """
    获取当前策略启用停用状态
    Args:
    Returns:
    """
    statement = select(func.count(Strategy.id.distinct()))
    result = session.execute(statement)
    total_strategy = result.scalar()
    statement = select(func.count(DeviceStrategy.strategy_id.distinct()))
    result = session.execute(statement)
    enable_strategy = result.scalar()

    response = enable_disable(total_strategy=total_strategy, enable_strategy=enable_strategy)
    result_list = [response]
    return result_list
