#!/bin/bash
# =============================================================================
# CascadingTrust Production Setup Script
# =============================================================================
# This script sets up CascadingTrust on a fresh Ubuntu server.
# Run as a user with sudo access (not root).
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "CascadingTrust Production Setup"
echo "=========================================="

# =============================================================================
# System Dependencies
# =============================================================================
echo "[1/8] Installing system dependencies..."
sudo apt-get update
sudo apt-get upgrade -y

sudo apt-get -y install python3-venv python3-pip nginx

# Install Node.js LTS (using NodeSource)
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# =============================================================================
# Clone Repository
# =============================================================================
echo "[2/8] Setting up project..."
cd /home/admin
if [ ! -d "CascadingTrust" ]; then
    git clone https://github.com/wcshamblin/CascadingTrust.git
fi
cd CascadingTrust

# =============================================================================
# Backend Setup
# =============================================================================
echo "[3/8] Setting up backend..."
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Generate JWT secret and create .env file
if [ ! -f ".env" ]; then
    echo "[3/8] Creating backend .env file..."
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    cat > .env << EOF
JWT_SECRET_KEY=$JWT_SECRET
PRODUCTION=true
ALLOWED_DOMAINS=cascadingtrust.net,www.cascadingtrust.net
BASE_URL=https://cascadingtrust.net
JWT_EXPIRATION_DAYS=7
EOF
    chmod 600 .env
    echo "Created .env with generated JWT secret"
else
    echo ".env already exists, skipping..."
fi

# =============================================================================
# Frontend Setup
# =============================================================================
echo "[4/8] Setting up frontend..."
cd ../frontend
npm install

# Create frontend .env.local
if [ ! -f ".env.local" ]; then
    cat > .env.local << EOF
NEXT_PUBLIC_API_SERVER_URL=https://cascadingtrust.net/api
EOF
    echo "Created frontend .env.local"
fi

# Build for production
npm run build

# =============================================================================
# Nginx Configuration
# =============================================================================
echo "[5/8] Configuring nginx..."
cd ..

# Copy rate limiting config
sudo cp deploy/rate-limiting.conf /etc/nginx/conf.d/

# Copy site config
sudo cp nginx.conf /etc/nginx/sites-available/cascadingtrust
sudo ln -sf /etc/nginx/sites-available/cascadingtrust /etc/nginx/sites-enabled/

# Remove default site if exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t

# =============================================================================
# Systemd Services
# =============================================================================
echo "[6/8] Installing systemd services..."
sudo cp deploy/cascadingtrust-api.service /etc/systemd/system/
sudo cp deploy/cascadingtrust-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable cascadingtrust-api
sudo systemctl enable cascadingtrust-frontend

# =============================================================================
# SSL Setup with Certbot
# =============================================================================
echo "[7/8] Setting up SSL..."
if ! command -v certbot &> /dev/null; then
    sudo snap install --classic certbot
    sudo ln -sf /snap/bin/certbot /usr/bin/certbot
fi

# =============================================================================
# Start Services
# =============================================================================
echo "[8/8] Starting services..."
sudo systemctl start cascadingtrust-api
sudo systemctl start cascadingtrust-frontend
sudo systemctl restart nginx

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run: sudo certbot --nginx -d cascadingtrust.net -d www.cascadingtrust.net"
echo "2. Uncomment HSTS header in nginx.conf after confirming HTTPS works"
echo "3. Uncomment rate limiting in nginx.conf"
echo ""
echo "Useful commands:"
echo "  Check API status:      sudo systemctl status cascadingtrust-api"
echo "  Check frontend status: sudo systemctl status cascadingtrust-frontend"
echo "  View API logs:         sudo journalctl -u cascadingtrust-api -f"
echo "  View frontend logs:    sudo journalctl -u cascadingtrust-frontend -f"
echo ""