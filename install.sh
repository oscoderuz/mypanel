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

echo -e "${GREEN}[1/7]${NC} Обновление системы..."
apt-get update -qq
apt-get upgrade -y -qq

echo -e "${GREEN}[2/7]${NC} Установка системных зависимостей..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    supervisor

# Install Docker
echo -e "${GREEN}[3/7]${NC} Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "Docker уже установлен"
fi

# Create panel user
echo -e "${GREEN}[4/7]${NC} Создание пользователя панели..."
if ! id "$PANEL_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$PANEL_DIR" "$PANEL_USER"
fi
usermod -aG docker "$PANEL_USER"

# Create panel directory
echo -e "${GREEN}[5/7]${NC} Установка MyPanel..."
mkdir -p "$PANEL_DIR"
mkdir -p "$PANEL_DIR/data"
mkdir -p "$PANEL_DIR/logs"

# Copy panel files (assuming running from source directory)
if [ -f "app.py" ]; then
    cp -r . "$PANEL_DIR/"
else
    echo -e "${YELLOW}Файлы панели не найдены в текущей директории${NC}"
    echo "Убедитесь, что вы запускаете скрипт из директории с исходным кодом"
fi

# Create virtual environment
echo -e "${GREEN}[6/7]${NC} Настройка Python окружения..."
cd "$PANEL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# Set permissions
chown -R "$PANEL_USER:$PANEL_USER" "$PANEL_DIR"
chmod -R 755 "$PANEL_DIR"

# Create systemd service
echo -e "${GREEN}[7/7]${NC} Создание systemd сервиса..."
cat > /etc/systemd/system/mypanel.service << EOF
[Unit]
Description=MyPanel Server Management Panel
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=$PANEL_USER
Group=$PANEL_USER
WorkingDirectory=$PANEL_DIR
Environment="PATH=$PANEL_DIR/venv/bin"
Environment="MYPANEL_ENV=production"
ExecStart=$PANEL_DIR/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create Nginx config for panel
cat > /etc/nginx/sites-available/mypanel << EOF
# MyPanel Nginx Configuration
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

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
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/mypanel /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Reload services
systemctl daemon-reload
nginx -t && systemctl restart nginx
systemctl enable mypanel
systemctl start mypanel

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
echo -e "Полезные команды:"
echo -e "  ${YELLOW}systemctl status mypanel${NC}  - статус панели"
echo -e "  ${YELLOW}systemctl restart mypanel${NC} - перезапуск панели"
echo -e "  ${YELLOW}journalctl -u mypanel -f${NC}  - логи панели"
echo ""
echo -e "${GREEN}Спасибо за использование MyPanel!${NC}"
