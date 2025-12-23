# CascadingTrust Deployment Guide

This directory contains systemd service files for deploying CascadingTrust in production.

## Quick Setup

### 1. Install Dependencies

```bash
# Backend
cd /home/admin/CascadingTrust/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd /home/admin/CascadingTrust/frontend
npm install
npm run build
```

### 2. Configure Environment

**Backend** (`/home/admin/CascadingTrust/backend/.env`):
```bash
# Generate a secure JWT secret
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

# Create .env file
cat > /home/admin/CascadingTrust/backend/.env << EOF
JWT_SECRET_KEY=$JWT_SECRET_KEY
PRODUCTION=true
ALLOWED_DOMAINS=cascadingtrust.net,www.cascadingtrust.net
BASE_URL=https://cascadingtrust.net
JWT_EXPIRATION_DAYS=7
EOF

# Secure the file
chmod 600 /home/admin/CascadingTrust/backend/.env
```

**Frontend** (`/home/admin/CascadingTrust/frontend/.env.local`):
```bash
cat > /home/admin/CascadingTrust/frontend/.env.local << EOF
NEXT_PUBLIC_API_SERVER_URL=https://cascadingtrust.net/api
EOF
```

### 3. Install Systemd Services

```bash
# Copy service files
sudo cp deploy/cascadingtrust-api.service /etc/systemd/system/
sudo cp deploy/cascadingtrust-frontend.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable cascadingtrust-api
sudo systemctl enable cascadingtrust-frontend

# Start services
sudo systemctl start cascadingtrust-api
sudo systemctl start cascadingtrust-frontend
```

### 4. Configure Nginx

Copy the nginx configuration:
```bash
sudo cp nginx.conf /etc/nginx/sites-available/cascadingtrust
sudo ln -sf /etc/nginx/sites-available/cascadingtrust /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Setup SSL with Certbot

```bash
# Install certbot if needed
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot

# Get SSL certificate (this modifies nginx.conf automatically)
sudo certbot --nginx -d cascadingtrust.net -d www.cascadingtrust.net
```

### 6. Post-Certbot Security Hardening

After Certbot runs successfully, add security headers to the HTTPS server block:

```bash
# Edit the nginx config
sudo nano /etc/nginx/sites-available/cascadingtrust

# Add these lines inside the HTTPS server block (listen 443 ssl):
#   add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
#   add_header X-Frame-Options "SAMEORIGIN" always;
#   add_header X-Content-Type-Options "nosniff" always;
#   add_header X-XSS-Protection "1; mode=block" always;
#   add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# See deploy/nginx-post-certbot.conf for full reference

# Enable rate limiting (optional but recommended)
sudo cp deploy/rate-limiting.conf /etc/nginx/conf.d/
# Then uncomment the limit_req lines in nginx config

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

## Management Commands

```bash
# Check service status
sudo systemctl status cascadingtrust-api
sudo systemctl status cascadingtrust-frontend

# View logs
sudo journalctl -u cascadingtrust-api -f
sudo journalctl -u cascadingtrust-frontend -f

# Restart services
sudo systemctl restart cascadingtrust-api
sudo systemctl restart cascadingtrust-frontend

# Stop services
sudo systemctl stop cascadingtrust-api
sudo systemctl stop cascadingtrust-frontend
```

## Updating

```bash
# Pull latest code
cd /home/admin/CascadingTrust
git pull

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Update frontend
cd ../frontend
npm install
npm run build

# Restart services
sudo systemctl restart cascadingtrust-api
sudo systemctl restart cascadingtrust-frontend
```

## Troubleshooting

### API won't start
- Check JWT_SECRET_KEY is set: `grep JWT_SECRET_KEY backend/.env`
- Check logs: `sudo journalctl -u cascadingtrust-api -n 50`

### Frontend won't start
- Ensure build completed: `cd frontend && npm run build`
- Check logs: `sudo journalctl -u cascadingtrust-frontend -n 50`

### 502 Bad Gateway
- Check if services are running: `sudo systemctl status cascadingtrust-*`
- Check nginx config: `sudo nginx -t`

