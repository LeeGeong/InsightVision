@echo off
REM OCR 测试快速启动脚本 (Windows)

echo ============================================================
echo OCR 测试快速启动
echo ============================================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 检查 pytest 是否安装
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未检测到 pytest，正在安装...
    pip install pytest requests
)

REM 运行测试
echo [信息] 开始运行 TCP7 OCR 测试...
echo.
python tests\run_ocr_test.py --config TCP7

echo.
echo ============================================================
echo 测试完成
echo ============================================================
pause
