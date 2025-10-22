#!/bin/bash

# ============================================
# Binance 自动化交易系统开发环境部署脚本
# 简化版部署，适用于开发和测试环境
# ============================================

set -e  # 遇到错误立即退出

# 配置参数
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# 颜色输出函数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python_version() {
    log_info "检查Python版本..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装，请先安装Python3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python版本: $PYTHON_VERSION"
}

# 设置Python虚拟环境
setup_virtualenv() {
    log_info "设置Python虚拟环境..."
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        log_success "虚拟环境创建完成"
    else
        log_warning "虚拟环境已存在，跳过创建"
    fi
}

# 安装Python依赖
install_python_dependencies() {
    log_info "安装Python依赖包..."
    
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
    
    log_success "Python依赖安装完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$PROJECT_DIR/backups"
    
    log_success "目录创建完成"
}

# 创建开发环境启动脚本
create_dev_scripts() {
    log_info "创建开发环境启动脚本..."
    
    # 启动交易机器人
    cat > "$PROJECT_DIR/start-bot.sh" << 'EOF'
#!/bin/bash

# 启动交易机器人
source venv/bin/activate
python run.py --mode bot --log-level info
EOF
    
    # 启动Web服务器
    cat > "$PROJECT_DIR/start-web.sh" << 'EOF'
#!/bin/bash

# 启动Web服务器
source venv/bin/activate
python run.py --mode web --host 0.0.0.0 --port 8001 --log-level info
EOF
    
    # 同时启动两者
    cat > "$PROJECT_DIR/start-both.sh" << 'EOF'
#!/bin/bash

# 同时启动交易机器人和Web服务器
source venv/bin/activate
python run.py --mode both --host 0.0.0.0 --port 8001 --log-level info
EOF
    
    # 停止脚本
    cat > "$PROJECT_DIR/stop-all.sh" << 'EOF'
#!/bin/bash

# 停止所有进程
pkill -f "python run.py"
echo "所有进程已停止"
EOF
    
    chmod +x "$PROJECT_DIR/start-bot.sh"
    chmod +x "$PROJECT_DIR/start-web.sh"
    chmod +x "$PROJECT_DIR/start-both.sh"
    chmod +x "$PROJECT_DIR/stop-all.sh"
    
    log_success "启动脚本创建完成"
}

# 创建环境配置
setup_environment() {
    log_info "设置环境配置..."
    
    # 创建.env文件（如果不存在）
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        cat > "$PROJECT_DIR/.env" << 'EOF'
# Binance API配置
# 请在此处填写您的API密钥
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# 交易配置
TRADING_SYMBOL=BTCUSDT
TRADING_LEVERAGE=10

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/trading-bot.log

# Web服务器配置
WEB_HOST=0.0.0.0
WEB_PORT=8001
EOF
        log_warning "已创建.env文件，请编辑并配置您的API密钥"
    fi
    
    log_success "环境配置完成"
}

# 显示部署完成信息
finish_deployment() {
    log_info "\n=== 开发环境部署完成 ==="
    echo ""
    echo "项目目录: $PROJECT_DIR"
    echo "虚拟环境: $VENV_DIR"
    echo ""
    echo "启动命令:"
    echo "  只启动交易机器人: ./start-bot.sh"
    echo "  只启动Web界面: ./start-web.sh"
    echo "  同时启动两者: ./start-both.sh"
    echo "  停止所有: ./stop-all.sh"
    echo ""
    echo "Web界面: http://localhost:8001"
    echo ""
    echo "下一步操作:"
    echo "  1. 编辑配置文件: config.jsonc"
    echo "  2. 配置Binance API密钥"
    echo "  3. 启动服务: ./start-both.sh"
    echo ""
    
    log_success "开发环境部署完成！可以开始使用了"
}

# 主部署流程
main() {
    log_info "开始部署Binance自动化交易系统开发环境..."
    
    check_python_version
    setup_virtualenv
    install_python_dependencies
    create_directories
    create_dev_scripts
    setup_environment
    finish_deployment
}

# 执行主函数
main "$@"