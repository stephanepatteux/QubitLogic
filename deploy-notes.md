# Deployment Notes — QuantumStack on Ubuntu VPS + Nginx

## 1. Build the site

```bash
hugo --minify
```

Output lands in `public/`. Copy this to your VPS.

## 2. Transfer to VPS

```bash
rsync -avz --delete public/ user@YOUR_VPS_IP:/var/www/quantumstack/
```

## 3. Nginx site config

Create `/etc/nginx/sites-available/quantumstack`:

```nginx
server {
    listen 80;
    server_name quantumstack.com www.quantumstack.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name quantumstack.com www.quantumstack.com;

    root /var/www/quantumstack;
    index index.html;

    ssl_certificate     /etc/letsencrypt/live/quantumstack.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/quantumstack.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options         "SAMEORIGIN"   always;
    add_header X-Content-Type-Options  "nosniff"      always;
    add_header Referrer-Policy         "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy      "interest-cohort=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Aggressive static caching
    location ~* \.(css|js|woff2?|ttf|eot|svg|png|jpg|webp|ico)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # HTML — no cache (Hugo hashes assets anyway)
    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript
               image/svg+xml;
    gzip_min_length 1024;
    gzip_comp_level 6;

    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    error_page 404 /404.html;
}
```

Enable and reload:

```bash
ln -s /etc/nginx/sites-available/quantumstack /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## 4. TLS via Certbot

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d quantumstack.com -d www.quantumstack.com
```

## 5. Auto-renew

Certbot adds a systemd timer automatically. Verify:

```bash
systemctl list-timers | grep certbot
```

## 6. Performance checklist

- [ ] PageSpeed Insights score ≥ 95 on mobile before launch
- [ ] `curl -I https://quantumstack.com` shows `content-encoding: gzip`
- [ ] Lighthouse: CLS < 0.1, LCP < 1.5 s, TBT < 200 ms

## 7. Hugo version pinning

Current build uses Hugo Extended **v0.162.1**. Lock this in CI:

```yaml
# .github/workflows/deploy.yml  (example)
- uses: peaceiris/actions-hugo@v3
  with:
    hugo-version: '0.162.1'
    extended: true
```
