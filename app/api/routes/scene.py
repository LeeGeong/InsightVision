import uuid
from pydantic import UUID4
from app.api.deps import SessionDep
from fastapi import APIRouter, HTTPException
from app.models.scene import Scene, GetScene, UpdateScene, CreatScene
from sqlmodel import select
import datetime

router = APIRouter()
details = "scene not found"

@router.get("/read", response_model=list[GetScene])
async def read_scene(session: SessionDep, name: str = ""):
    """
    Get Scene by ID
    """
    statement = select(Scene).where(Scene.name.like(f"%{name}%"))
    result = session.exec(statement)
    result_list = []
    # result 一直有值，没法判断查询为空
    if not result:
        raise HTTPException(status_code=404, detail=details)
    else:
        for r in result:
            result_list.append(GetScene(id=r.id, name=r.name))
    return result_list


@router.post("/create", response_model=list[Scene])
async def create_scene(session: SessionDep, current_scene: CreatScene):
    """
    Create Scene
    """
    result = Scene.model_validate(current_scene,
                                update={"update_time": datetime.datetime.now().replace(microsecond=0),
                                        "id":uuid.uuid4()})
    session.add(result)
    session.commit()
    session.refresh(result)
    result_list = [result]
    return result_list

@router.post("/update", response_model=list[Scene])
async def update_scene(session: SessionDep, current_scene: UpdateScene):
    """
    Update Scene
    """
    # item = session.query(Scene).filter(Scene.id == current_scene.id).first()
    result = session.get(Scene, current_scene.id)
    if not result:
        # 如果找不到对应的场景，抛出HTTP 404错误
        raise HTTPException(status_code=404, detail=details)
    # 更新场景的name字段
    result.name = current_scene.name
    result.update_time = datetime.datetime.now().replace(microsecond=0)
    # scene = session.get(Scene, current_scene.id)
    # item = Scene.model_validate(scene, update={"name": current_scene.name,
    #                                            "update_time": datetime.datetime.now().replace(microsecond=0)})

    session.commit()
    session.refresh(result)
    result_list = [result]
    return result_list

@router.delete("/delete")
async def delete_scene(session: SessionDep, id: UUID4):
    """
    Delete Scene by Id
    """
    result = session.get(Scene, id)
    if not result:
        raise HTTPException(status_code=404, detail=details)
    session.delete(result)
    session.commit()
    return "success"
