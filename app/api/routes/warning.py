from pydantic import UUID4
from app.api.deps import SessionDep
from fastapi import APIRouter, HTTPException
from app.models.warning import Warning, WarningResponse, warning_to_response
from app.models.device import Device
from app.models.strategy import Strategy
from app.models.scene import Scene
from sqlmodel import select
import datetime
import pandas as pd

from sqlalchemy import func, cast, Integer, and_

router = APIRouter()
details = "warning not found"


@router.get("/read", response_model=list[WarningResponse])
async def read_warning(session: SessionDep, device_name: str = "", scene_name: str = "", strategy_name: str = "",
                 start_time: str = "", end_time: str = ""):
    """
    Get warning by ID.
    """
    statement = select(Warning).join(Strategy).join(Device).join(Scene)
    base_statement = select(Warning).join(Strategy).join(Device)
    # base_result = session.execute(base_statement).all()
    # print(base_result)
    # warnings = session.exec(statement).all()
    # return warnings
    if device_name:
        statement = statement.where(Device.name.like(f"%{device_name}%"))
    if scene_name:
        statement = statement.where(Scene.name.like(f"%{scene_name}%"))
    if strategy_name:
        statement = statement.where(Strategy.name.like(f"%{strategy_name}%"))
    if start_time:
        statement = statement.where(Warning.happen_time > start_time)
    if end_time:
        statement = statement.where(Warning.happen_time < end_time)
    result = session.exec(statement).all()
    # if not device_name and not scene_name and not strategy_name and not start_time and not end_time:
    #     result = session.exec(base_statement).all()
    # result 一直有值，没法判断查询为空
    if not result:
        return []
        # raise HTTPException(status_code=404, detail=details)
    result_list = [warning_to_response(r) for r in result]
    return result_list
    # 初始化查询
    # query = session.query(Warning).options(
    #     selectinload(Warning.parent_device),  # 加载Device关联
    #     selectinload(Warning.parent_strategy)  # 加载Strategy关联
    # ).join(Warning.parent_device,Warning.parent_device.parent_scene)
    # # 动态添加过滤条件
    # if device_name:
    #     query = query.filter(Warning.parent_device.name.like(f"%{device_name}%"))
    # if scene_name:
    #     query = query.filter(Warning.parent_device.parent_scene.name.like(f"%{scene_name}%"))
    # if strategy_name:
    #     query = query.filter(Warning.parent_strategy.name.like(f"%{strategy_name}%"))
    # try:
    #     # 执行查询并转换结果
    #     result_list = [warning_to_response(warning) for warning in query.all()]
    # except Exception:
    #     raise HTTPException(status_code=404, detail="No warnings found matching the given criteria.")
    # return result_list


@router.delete("/delete")
async def delete_warning(session: SessionDep, id: UUID4):
    """
    Delete warning by ID.
    """
    scene = session.get(Warning, id)
    if not scene:
        raise HTTPException(status_code=404, detail=details)
    session.delete(scene)
    session.commit()
    return "success"


@router.get("/line_chart")
async def line_chart_warning(session: SessionDep, unit: str = "year"):
    """
    获取年月日折线图数据
    unit : year | month | week
    """
    # statement = select(Warning).join(Strategy)
    # results = session.exec(statement).all()

    query = select(
        Warning.id,
        Warning.device_id,
        Warning.strategy_id,
        Warning.happen_time,
        Warning.image_address,
        Strategy.name.label("strategy_name")  # 使用label来明确别名，避免列名冲突
    ).join(Strategy, Warning.strategy_id == Strategy.id)  # 假设策略ID是关联字段

    if unit == "year":
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=365)
    elif unit == "month":
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=30)
    elif unit == "week":
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=7)

    query = query.where(and_(Warning.happen_time >= start_time, Warning.happen_time <= end_time))
    results = session.execute(query).all()

    df_warning = pd.DataFrame(results,
                              columns=['id', 'device_id', 'strategy_id', 'happen_time', 'image_address',
                                       'strategy_name'])
    df_warning['date'] = pd.to_datetime(df_warning['happen_time'])
    df_warning.set_index('date', inplace=True)
    query = select(Strategy.id, Strategy.name, Strategy.key)  # 使用label来明确别名，避免列名冲突
    results = session.execute(query).all()
    df_strategy = pd.DataFrame(results, columns=['id', 'name', 'key'])
    unique_name = df_strategy['name'].unique()
    return_list = []
    for name in unique_name:
        mid_dict = {}
        df_warning_filter = df_warning[df_warning['strategy_name'] == name].copy()
        mid_dict['strategy_name'] = name
        mid_dict['data'] = {}
        cycle_times = 0
        today = datetime.datetime.today()
        if unit == "year":
            while cycle_times <= 7:
                next_month = today - datetime.timedelta(days=30)
                warning_data = df_warning_filter[
                    (df_warning_filter['happen_time'] > next_month) & (df_warning_filter['happen_time'] < today)].shape[
                    0]
                mid_dict['data'][today.strftime("%Y-%m-%d")] = warning_data
                today = next_month
                cycle_times += 1
        elif unit == "month":
            while cycle_times <= 7:
                next_month = today - datetime.timedelta(days=7)
                warning_data = df_warning_filter[
                    (df_warning_filter['happen_time'] > next_month) & (df_warning_filter['happen_time'] < today)].shape[
                    0]
                mid_dict['data'][today.strftime("%Y-%m-%d")] = warning_data
                today = next_month
                cycle_times += 1
        elif unit == "week":
            while cycle_times <= 7:
                next_month = today - datetime.timedelta(days=1)
                warning_data = df_warning_filter[
                    (df_warning_filter['happen_time'] > next_month) & (df_warning_filter['happen_time'] < today)].shape[
                    0]
                mid_dict['data'][today.strftime("%Y-%m-%d")] = warning_data
                today = next_month
                cycle_times += 1
        mid_dict['data'] = {k: mid_dict['data'][k] for k in sorted(mid_dict['data'], reverse=False)}
        return_list.append(mid_dict)

    # weekly_counts = df_warning_filter.resample('W-MON').size().reset_index(name='count')
    # a = [pd.Grouper(freq='W-MON'), 'strategy_name']
    # df_weekly_names = df.groupby(a).first()
    # # df_weekly_names = df.groupby(a).first()['strategy_name'].reset_index()
    # weekly_counts = weekly_counts.merge(df_weekly_names, on=['date', 'strategy_name'], how='left').fillna(0)

    return return_list
