from fastapi import APIRouter

from .routes import device, scene, strategy, warning, system, bao_steel

api_router = APIRouter(prefix="/api")
api_router.include_router(device.router, prefix="/device", tags=["Device"])
api_router.include_router(scene.router, prefix="/scene", tags=["Scene"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["Strategy"])
api_router.include_router(warning.router, prefix="/warning", tags=["Warning"])
api_router.include_router(system.router, prefix="/system", tags=["System"])
# api_router.include_router(artificial_intelligence.router, prefix="/intelligence", tags=["金重接口"])
# api_router.include_router(yt.router, tags=["云铜接口"])
api_router.include_router(bao_steel.router, prefix="/bao_steel",tags=["宝钢接口"])
# api_router.include_router(bao_steel1.router, prefix="/bao_steel1",tags=["宝钢接口(新)"])