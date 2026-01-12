@echo off
REM Daily Digest Agent - Windows一键部署脚本
REM 使用方法: deploy.bat

setlocal enabledelayedexpansion

echo [INFO] 开始部署 Daily Digest Agent...
echo.

REM 检查Docker是否安装
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker 未安装，请先安装 Docker Desktop
    exit /b 1
)

where docker-compose >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose 未安装，请先安装 Docker Compose
    exit /b 1
)

echo [INFO] 系统依赖检查通过
echo.

REM 检查.env文件
if not exist .env (
    echo [WARN] .env 文件不存在，从 .env.example 创建...
    if exist .env.example (
        copy .env.example .env >nul
        echo [WARN] 请编辑 .env 文件，填入必需的配置（特别是 SECRET_KEY 和 LLM API密钥）
        echo [WARN] 编辑完成后，请重新运行此脚本
        exit /b 1
    ) else (
        echo [ERROR] .env.example 文件不存在，无法创建 .env 文件
        exit /b 1
    )
)

echo [INFO] 检查必需配置...
REM 这里可以添加更多的配置检查

echo [INFO] 配置检查完成
echo.

echo [INFO] 构建Docker镜像...
docker-compose build
if %errorlevel% neq 0 (
    echo [ERROR] 镜像构建失败
    exit /b 1
)

echo [INFO] 镜像构建完成
echo.

echo [INFO] 启动服务...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] 服务启动失败
    exit /b 1
)

echo [INFO] 服务启动完成
echo.

timeout /t 5 /nobreak >nul

echo [INFO] =========================================
echo [INFO] 部署完成！
echo [INFO] =========================================
echo.
echo [INFO] 服务访问地址:
echo [INFO]   前端: http://localhost:16666
echo [INFO]   后端API: http://localhost:6666
echo [INFO]   API文档: http://localhost:6666/docs
echo.
echo [INFO] 常用命令:
echo [INFO]   查看日志: docker-compose logs -f
echo [INFO]   停止服务: docker-compose down
echo [INFO]   重启服务: docker-compose restart
echo [INFO]   查看状态: docker-compose ps
echo.

pause
