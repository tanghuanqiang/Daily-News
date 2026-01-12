#!/bin/bash

# Daily Digest Agent - 一键部署脚本
# 使用方法: ./deploy.sh

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

# 主函数
main() {
    print_info "开始部署 Daily Digest Agent..."
    echo ""

    # 检查必需的命令
    print_info "检查系统依赖..."
    check_command docker
    check_command docker-compose
    print_info "✓ 系统依赖检查通过"
    echo ""

    # 检查.env文件
    if [ ! -f .env ]; then
        print_warn ".env 文件不存在，从 env.example 创建..."
        if [ -f env.example ]; then
            cp env.example .env
            print_warn "请编辑 .env 文件，填入必需的配置（特别是 SECRET_KEY 和 LLM API密钥）"
            print_warn "编辑完成后，请重新运行此脚本"
            exit 1
        else
            print_error "env.example 文件不存在，无法创建 .env 文件"
            exit 1
        fi
    fi

    # 检查必需的配置
    print_info "检查必需配置..."
    source .env
    
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" == "your-strong-random-secret-key-change-this-in-production" ]; then
        print_error "请修改 .env 文件中的 SECRET_KEY 为强随机字符串"
        exit 1
    fi

    if [ -z "$LLM_PROVIDER" ]; then
        print_error "请配置 .env 文件中的 LLM_PROVIDER (dashscope/nvidia/ollama)"
        exit 1
    fi

    case "$LLM_PROVIDER" in
        dashscope)
            if [ -z "$DASHSCOPE_API_KEY" ]; then
                print_error "请配置 .env 文件中的 DASHSCOPE_API_KEY"
                exit 1
            fi
            print_info "✓ 使用 DashScope LLM 服务"
            ;;
        nvidia)
            if [ -z "$NVIDIA_API_KEY" ]; then
                print_error "请配置 .env 文件中的 NVIDIA_API_KEY"
                exit 1
            fi
            print_info "✓ 使用 NVIDIA GLM LLM 服务"
            ;;
        ollama)
            print_warn "⚠ 使用本地 Ollama，请确保 Ollama 服务已运行在 $OLLAMA_BASE_URL"
            ;;
        *)
            print_error "不支持的 LLM_PROVIDER: $LLM_PROVIDER (支持: dashscope/nvidia/ollama)"
            exit 1
            ;;
    esac

    print_info "✓ 配置检查通过"
    echo ""

    # 检查端口占用
    print_info "检查端口占用..."
    BACKEND_PORT=${BACKEND_PORT:-6666}
    FRONTEND_PORT=${FRONTEND_PORT:-16666}
    
    if command -v netstat &> /dev/null; then
        if netstat -tuln | grep -q ":$BACKEND_PORT "; then
            print_warn "端口 $BACKEND_PORT 已被占用，请修改 BACKEND_PORT 或停止占用该端口的服务"
        fi
        if netstat -tuln | grep -q ":$FRONTEND_PORT "; then
            print_warn "端口 $FRONTEND_PORT 已被占用，请修改 FRONTEND_PORT 或停止占用该端口的服务"
        fi
    fi
    print_info "✓ 端口检查完成"
    echo ""

    # 构建镜像
    print_info "构建Docker镜像..."
    docker-compose build
    print_info "✓ 镜像构建完成"
    echo ""

    # 启动服务
    print_info "启动服务..."
    docker-compose up -d
    print_info "✓ 服务启动完成"
    echo ""

    # 等待服务就绪
    print_info "等待服务就绪..."
    sleep 5
    
    # 检查后端健康状态
    if docker-compose ps backend | grep -q "Up"; then
        print_info "✓ 后端服务运行中"
    else
        print_error "后端服务启动失败，请查看日志: docker-compose logs backend"
        exit 1
    fi

    # 检查前端服务
    if docker-compose ps frontend | grep -q "Up"; then
        print_info "✓ 前端服务运行中"
    else
        print_error "前端服务启动失败，请查看日志: docker-compose logs frontend"
        exit 1
    fi

    echo ""
    print_info "========================================="
    print_info "部署完成！"
    print_info "========================================="
    echo ""
    print_info "服务访问地址:"
    print_info "  前端: http://localhost:${FRONTEND_PORT:-80}"
    print_info "  后端API: http://localhost:${BACKEND_PORT:-8000}"
    print_info "  API文档: http://localhost:${BACKEND_PORT:-8000}/docs"
    echo ""
    print_info "常用命令:"
    print_info "  查看日志: docker-compose logs -f"
    print_info "  停止服务: docker-compose down"
    print_info "  重启服务: docker-compose restart"
    print_info "  查看状态: docker-compose ps"
    echo ""
}

# 运行主函数
main
