#!/bin/bash
#
# MyPanel Installation Script
# ============================
# Installs MyPanel on Ubuntu Server 20.04+
#
# Usage: sudo bash install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PANEL_DIR="/opt/mypanel"
PANEL_USER="mypanel"
PANEL_PORT=8888
DOMAIN=""

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║   ███╗   ███╗██╗   ██╗██████╗  █████╗ ███╗   ██╗███████╗██╗  ║"
echo "║   ████╗ ████║╚██╗ ██╔╝██╔══██╗██╔══██╗████╗  ██║██╔════╝██║  ║"
echo "║   ██╔████╔██║ ╚████╔╝ ██████╔╝███████║██╔██╗ ██║█████╗  ██║  ║"
echo "║   ██║╚██╔╝██║  ╚██╔╝  ██╔═══╝ ██╔══██║██║╚██╗██║██╔══╝  ██║  ║"
echo "║   ██║ ╚═╝ ██║   ██║   ██║     ██║  ██║██║ ╚████║███████╗███████╗"
echo "║   ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝"
echo "║                                                              ║"
echo "║              Server Management Panel Installer               ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Пожалуйста, запустите скрипт с правами root (sudo)${NC}"
    exit 1
fi

# Check OS
if [ ! -f /etc/os-release ]; then
    echo -e "${RED}Не удалось определить ОС${NC}"
    exit 1
fi

source /etc/os-release
if [ "$ID" != "ubuntu" ] && [ "$ID" != "debian" ]; then
    echo -e "${YELLOW}Предупреждение: Скрипт тестировался только на Ubuntu/Debian${NC}"
fi

echo -e "${GREEN}[1/8]${NC} Обновление системы..."
apt-get update -qq
apt-get upgrade -y -qq

echo -e "${GREEN}[2/8]${NC} Установка системных зависимостей..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    supervisor \
    ufw \
    htop \
    net-tools \
    unzip \
    tar

# Verify nginx installation
echo -e "${GREEN}[2.1/8]${NC} Проверка Nginx..."
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Nginx не найден, повторная установка...${NC}"
    apt-get install -y nginx
fi

# Start and enable nginx
systemctl enable nginx
systemctl start nginx || true

# Verify supervisor installation
echo -e "${GREEN}[2.2/8]${NC} Проверка Supervisor..."
if ! command -v supervisorctl &> /dev/null; then
    echo -e "${YELLOW}Supervisor не найден, повторная установка...${NC}"
    apt-get install -y supervisor
fi

# Start and enable supervisor
systemctl enable supervisor
systemctl start supervisor || true

# Install Docker
echo -e "${GREEN}[3/8]${NC} Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "Docker уже установлен"
fi

# Create panel user
echo -e "${GREEN}[4/8]${NC} Создание пользователя панели..."
if ! id "$PANEL_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$PANEL_DIR" "$PANEL_USER"
fi
usermod -aG docker "$PANEL_USER"

# Create panel directory
echo -e "${GREEN}[5/8]${NC} Установка MyPanel..."
mkdir -p "$PANEL_DIR"
mkdir -p "$PANEL_DIR/data"
mkdir -p "$PANEL_DIR/logs"

# Copy panel files (assuming running from source directory)
if [ -f "app.py" ]; then
    CURRENT_DIR=$(pwd -P)
    TARGET_DIR=$(realpath "$PANEL_DIR" 2>/dev/null || echo "$PANEL_DIR")
    
    if [ "$CURRENT_DIR" = "$TARGET_DIR" ]; then
        echo "Файлы уже находятся в целевой директории"
    else
        cp -r . "$PANEL_DIR/"
    fi
else
    echo -e "${YELLOW}Файлы панели не найдены в текущей директории${NC}"
    echo "Убедитесь, что вы запускаете скрипт из директории с исходным кодом"
fi

# Create virtual environment
echo -e "${GREEN}[6/8]${NC} Настройка Python окружения..."
cd "$PANEL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# Set permissions
chown -R "$PANEL_USER:$PANEL_USER" "$PANEL_DIR"
chmod -R 755 "$PANEL_DIR"

# Create supervisor config for MyPanel
echo -e "${GREEN}[7/8]${NC} Настройка Supervisor..."
cat > /etc/supervisor/conf.d/mypanel.conf << EOF
[program:mypanel]
command=$PANEL_DIR/venv/bin/python app.py
directory=$PANEL_DIR
user=$PANEL_USER
autostart=true
autorestart=true
startsecs=5
startretries=3
redirect_stderr=true
stdout_logfile=/var/log/mypanel.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=MYPANEL_ENV="production",PATH="$PANEL_DIR/venv/bin"
EOF

# Reload supervisor
supervisorctl reread
supervisorctl update

# Create Nginx config for panel
echo -e "${GREEN}[8/8]${NC} Настройка Nginx..."
cat > /etc/nginx/sites-available/mypanel << EOF
# MyPanel Nginx Configuration
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:$PANEL_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_buffering off;
    }

    # WebSocket support for terminal
    location /socket.io {
        proxy_pass http://127.0.0.1:$PANEL_PORT/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/mypanel /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test and reload nginx
nginx -t && systemctl reload nginx

# Start MyPanel via supervisor
supervisorctl start mypanel || true

# Configure firewall
echo "Настройка файрвола..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable || true

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  УСТАНОВКА ЗАВЕРШЕНА!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Панель доступна по адресу: ${BLUE}http://$SERVER_IP${NC}"
echo ""
echo -e "При первом входе создайте администратора."
echo ""
echo -e "Установленные сервисы:"
echo -e "  ${GREEN}✓${NC} Nginx"
echo -e "  ${GREEN}✓${NC} Docker"
echo -e "  ${GREEN}✓${NC} Supervisor"
echo -e "  ${GREEN}✓${NC} Certbot (SSL)"
echo ""
echo -e "Полезные команды:"
echo -e "  ${YELLOW}supervisorctl status mypanel${NC}  - статус панели"
echo -e "  ${YELLOW}supervisorctl restart mypanel${NC} - перезапуск панели"
echo -e "  ${YELLOW}tail -f /var/log/mypanel.log${NC}  - логи панели"
echo -e "  ${YELLOW}systemctl status nginx${NC}        - статус Nginx"
echo -e "  ${YELLOW}systemctl status docker${NC}       - статус Docker"
echo ""
echo -e "${GREEN}Спасибо за использование MyPanel!${NC}"
