# Hostinger Deployment Guide for Khulaasaa & hooks85

This guide provides step-by-step instructions for deploying Khulaasaa on **Hostinger**.

---

## 1. Hosting Plan Requirement

> [!IMPORTANT]
> **Use Hostinger VPS (KVM 1 or KVM 2, Ubuntu 22.04 / 24.04 64-bit).**  
> Do **NOT** use Hostinger Shared Web Hosting. FastAPI and Uvicorn require an **ASGI** asynchronous application server with long-running background scraping daemons. Shared hosting kills long-running processes after 60 seconds and lacks Docker/ASGI support.

---

## 2. Fast 1-Click Setup on Hostinger VPS

### Step 1: Connect to your Hostinger VPS via SSH
From your local terminal (PowerShell, Terminal, or PuTTY):
```bash
ssh root@YOUR_HOSTINGER_SERVER_IP
```

### Step 2: Install Docker & Docker Compose (if not already installed)
If you chose the "Ubuntu with Docker" template in Hostinger hPanel, Docker is already installed. Otherwise:
```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose-plugin git curl
systemctl enable --now docker
```

### Step 3: Clone or Upload the Codebase
```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/khulaasaa-1.git khulaasaa
cd /opt/khulaasaa
```

### Step 4: Configure Production Environment (`.env`)
Create your production `.env` file:
```bash
cp .env.example .env
nano .env
```
Ensure you change these key variables:
```ini
# Production Admin Credentials (Change from default 'changeme')
EDITOR_USERNAME=admin
EDITOR_PASSWORD=YourStrongPasswordHere2026!

# Domain URL
APP_URL=https://yourdomain.com

# Database (Leave default for SQLite on VPS, or paste Supabase URL)
KHULAASAA_DB_PATH=/app/data/khulaasaa.db
# DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres

# Telegram Alert Bot (Optional)
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_BOT_USERNAME=khulaasaa_bot
```
Press `Ctrl+O` then `Enter` to save, and `Ctrl+X` to exit nano.

### Step 5: Build and Start the Docker Container
```bash
docker compose up -d --build
```
Check container status:
```bash
docker compose ps
docker compose logs -f web
```
The application is now running on port `8300`!

---

## 3. Connect Your Domain & Free SSL (HTTPS)

You have two easy options to connect your domain with HTTPS:

### Option A: Cloudflare Proxy (Fastest & Easiest)
1. In Hostinger / your domain registrar, set your domain's Nameservers to **Cloudflare**.
2. In Cloudflare DNS settings:
   * Add an **A Record**: `khulaasaa.tech` &rarr; `YOUR_HOSTINGER_SERVER_IP` (Proxy status: **Orange Cloud ON**).
   * Add an **A Record**: `app.hooks85.com` &rarr; `YOUR_HOSTINGER_SERVER_IP` (Proxy status: **Orange Cloud ON**).
3. Install Nginx on VPS to route incoming domains to their respective Docker containers:
```bash
apt install -y nginx
cat << 'EOF' > /etc/nginx/sites-available/multi-apps
# 1. Khulaasaa Public Platform
server {
    listen 80;
    server_name khulaasaa.tech www.khulaasaa.tech khulaasaa.mv;

    location / {
        proxy_pass http://127.0.0.1:8300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# 2. hooks85 Platform (Account, POS, Sales, Gateway & Payment Gateway)
server {
    listen 80;
    server_name app.hooks85.com hooks85.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# 3. hooks85 Admin Console
server {
    listen 80;
    server_name admin.hooks85.com;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
ln -s /etc/nginx/sites-available/multi-apps /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl reload nginx
```

### Option B: Direct Let's Encrypt Certbot SSL (All Domains)
If not using Cloudflare:
```bash
apt install -y nginx certbot python3-certbot-nginx
certbot --nginx -d khulaasaa.tech -d app.hooks85.com -d admin.hooks85.com
```

---

## 4. Pre-Deployment Readiness Checklist

| Item | Status | Verification / Action |
| :--- | :--- | :--- |
| **ASGI Engine** | ✅ Ready | Uvicorn running on FastAPI with background workers. |
| **Docker & Compose** | ✅ Ready | Dockerfile and `docker-compose.yml` with healthchecks (`/healthz`). |
| **Ads & Billing Quotas** | ✅ Ready | Impression limit (1,000 views) and time-based (1 month) limits working. |
| **Database** | ✅ Ready | Local persistent volume (`./data`) or cloud Supabase PostgreSQL adapter. |
| **Admin Security** | ⚠️ Notice | Change `EDITOR_PASSWORD` in `.env` before public launch. |
| **Static & Logos** | ✅ Ready | All agency, SOE, and hooks85 assets bundled inside `/static`. |
| **Scrapers 24/7** | ✅ Ready | Gazette, SOE procurement portals, and news scrapers run independently. |

---

## 5. Maintenance Commands Cheat Sheet

* **Update code after git push**:
  ```bash
  cd /opt/khulaasaa
  git pull origin main
  docker compose up -d --build
  ```
* **View live server logs**:
  ```bash
  docker compose logs -f web
  ```
* **Backup SQLite database**:
  ```bash
  cp /opt/khulaasaa/data/khulaasaa.db /opt/khulaasaa/data/khulaasaa.db.backup_$(date +%F)
  ```
