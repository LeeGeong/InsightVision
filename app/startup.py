import sys
import os

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))
import uvicorn as uvicorn
from fastapi import Depends, FastAPI, HTTPException, applications
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.main import api_router
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

# 测试Git
app = FastAPI(title="智能视觉平台接口文档", docs_url=None, redoc_url=None)

app.include_router(api_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/cache", StaticFiles(directory="cache"), name="cache")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="./cache/swagger-ui-bundle.js",
        swagger_css_url="./cache/swagger-ui.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="./cache/redoc.standalone.js",
    )


if __name__ == '__main__':
    print("可调用CPU数量：", os.cpu_count())
    uvicorn.run(app="startup:app", host="0.0.0.0", port=8001, workers=1, reload=False)
