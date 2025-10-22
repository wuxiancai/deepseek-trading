#!/bin/bash

# ============================================
# Binance 自动化交易系统部署脚本
# ============================================

set -e  # 遇到错误立即退出

# 配置参数
PROJECT_NAME="binance-trading-bot"
PROJECT_DIR="/opt/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/var/log/$PROJECT_NAME"
CONFIG_DIR="/etc/$PROJECT_NAME"
USER_NAME="tradingbot"

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

# 检查是否以root权限运行
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要以root权限运行"
        exit 1
    fi
}

# 安装系统依赖
install_system_dependencies() {
    log_info "安装系统依赖包..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        libssl-dev \
        libffi-dev \
        supervisor \
        nginx \
        git \
        curl \
        wget \
        tmux
        
    log_success "系统依赖安装完成"
}

# 创建项目用户
create_user() {
    log_info "创建专用用户: $USER_NAME..."
    
    if id "$USER_NAME" &>/dev/null; then
        log_warning "用户 $USER_NAME 已存在"
    else
        useradd -m -s /bin/bash "$USER_NAME"
        log_success "用户 $USER_NAME 创建成功"
    fi
}

# 创建项目目录结构
create_directories() {
    log_info "创建项目目录结构..."
    
    mkdir -p "$PROJECT_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/scripts"
    mkdir -p "$PROJECT_DIR/backups"
    
    chown -R "$USER_NAME:$USER_NAME" "$PROJECT_DIR"
    chown -R "$USER_NAME:$USER_NAME" "$LOG_DIR"
    
    log_success "目录结构创建完成"
}

# 设置Python虚拟环境
setup_virtualenv() {
    log_info "设置Python虚拟环境..."
    
    sudo -u "$USER_NAME" python3 -m venv "$VENV_DIR"
    
    log_success "虚拟环境创建完成"
}

# 安装Python依赖
install_python_dependencies() {
    log_info "安装Python依赖包..."
    
    # 复制项目文件到部署目录（假设当前目录是项目根目录）
    cp -r . "$PROJECT_DIR/"
    chown -R "$USER_NAME:$USER_NAME" "$PROJECT_DIR"
    
    # 安装依赖
    sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" install --upgrade pip
    sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
    
    log_success "Python依赖安装完成"
}

# 配置Supervisor
setup_supervisor() {
    log_info "配置Supervisor服务..."
    
    cat > "/etc/supervisor/conf.d/$PROJECT_NAME.conf" << EOF
[program:$PROJECT_NAME]
command=$VENV_DIR/bin/python $PROJECT_DIR/run.py --mode both --host 0.0.0.0 --port 8000
directory=$PROJECT_DIR
user=$USER_NAME
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=60
redirect_stderr=true
stdout_logfile=$LOG_DIR/trading-bot.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=10
stderr_logfile=$LOG_DIR/trading-bot-error.log
stderr_logfile_maxbytes=10MB
stderr_logfile_backups=10
environment=PYTHONPATH=\