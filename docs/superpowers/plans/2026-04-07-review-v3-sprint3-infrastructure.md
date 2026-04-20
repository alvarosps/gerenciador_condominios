# Comprehensive Review v3 — Sprint 3: Infrastructure & Deploy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the production infrastructure — parametrize nginx configuration, fix rate limiting, add Docker image publishing to CI, make security checks mandatory, integrate Sentry properly, separate migrations from container startup, expand health checks, validate email config, add PgBouncer connection pooling, switch to structured JSON logging, and add Celery monitoring via Flower.

**Architecture:** 12 tasks covering Docker Compose, Nginx, GitHub Actions CI, Django settings, and Celery. All tasks are independently deployable; see dependency graph for the two exceptions.

**Tech Stack:** Docker Compose, Nginx, GitHub Actions, Django 5.2, Celery, Redis, PostgreSQL 15, PgBouncer, Sentry SDK, python-json-logger

**Dependency Graph:**
```
Task 1 (Nginx domain parametrization) → independent
Task 2 (Nginx rate limiting fix) → depends on Task 1 (edits same nginx files)
Task 3 (CI Docker build & push) → independent
Task 4 (CI security checks mandatory) → independent
Task 5 (CI frontend build with dynamic env) → independent
Task 6 (Sentry integration) → independent
Task 7 (Separate migrations from container start) → independent
Task 8 (Expanded health check) → independent
Task 9 (Email config validation) → independent
Task 10 (PgBouncer connection pooling) → independent
Task 11 (Structured JSON logging) → independent
Task 12 (Celery monitoring — Flower) → independent
```

---

## Task 1: Nginx Domain Parametrization

**Context:** `nginx/conf.d/condominios.conf` has `yourdomain.com` hardcoded on lines 11, 28. SSL certificate paths point to `/etc/nginx/ssl/` which is a static volume mount. There is no Certbot container in `docker-compose.prod.yml` and no mechanism to obtain or renew Let's Encrypt certificates. The `.well-known/acme-challenge/` location block already exists on line 14 of the conf file, but no certbot volume is mounted and no certbot container is defined.

**Files:**
- Modify: `nginx/conf.d/condominios.conf`
- Modify: `docker-compose.prod.yml`
- Create: `nginx/conf.d/condominios.conf.template` (envsubst template)
- Create: `scripts/init-letsencrypt.sh`
- Create: `nginx/entrypoint.sh`

- [ ] **Step 1: Create nginx conf template using envsubst syntax**

Rename `nginx/conf.d/condominios.conf` to `nginx/conf.d/condominios.conf.template` and replace every occurrence of `yourdomain.com` with `${DOMAIN}`:

```nginx
# Upstream Django Application
upstream django_app {
    server web:8008 fail_timeout=10s max_fails=3;
    keepalive 32;
}

# HTTP to HTTPS Redirect
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};

    # ACME Challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN} www.${DOMAIN};

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Logging
    access_log /var/log/nginx/condominios_access.log;
    error_log /var/log/nginx/condominios_error.log;

    # Max upload size
    client_max_body_size 20M;

    # Health Check Endpoint
    location /health/ {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $real_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }

    # Static Files
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Media Files
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Contract Files (Protected - requires authentication)
    location /contracts/ {
        internal;
        alias /app/contracts/;
    }

    # API Endpoints with Rate Limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $real_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Admin Panel with Stricter Rate Limiting
    location /admin/ {
        limit_req zone=login_limit burst=5 nodelay;

        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $real_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # OAuth Callbacks
    location /accounts/ {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $real_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Root and Other Endpoints
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $real_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Note: `$real_ip` is defined by Task 2. If implementing Task 1 alone, keep `$remote_addr` until Task 2 is applied.

- [ ] **Step 2: Create nginx custom entrypoint to run envsubst before nginx starts**

Create `nginx/entrypoint.sh`:

```bash
#!/bin/sh
set -e

# Substitute environment variables in nginx template
envsubst '${DOMAIN}' < /etc/nginx/conf.d/condominios.conf.template \
    > /etc/nginx/conf.d/condominios.conf

# Test configuration before starting
nginx -t

# Hand off to the official nginx entrypoint
exec nginx -g "daemon off;"
```

Make it executable:

```bash
chmod +x nginx/entrypoint.sh
```

- [ ] **Step 3: Add Certbot service and update nginx service in docker-compose.prod.yml**

Add `certbot` service and update `nginx` service volumes and entrypoint:

```yaml
  nginx:
    image: nginx:alpine
    container_name: condominios_nginx_prod
    entrypoint: ["/docker-entrypoint-nginx.sh"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d/condominios.conf.template:/etc/nginx/conf.d/condominios.conf.template:ro
      - ./nginx/entrypoint.sh:/docker-entrypoint-nginx.sh:ro
      - static_volume:/app/static:ro
      - media_volume:/app/media:ro
      - certbot_data:/var/www/certbot:ro
      - letsencrypt_data:/etc/letsencrypt:ro
      - ./nginx/logs:/var/log/nginx
    environment:
      - DOMAIN=${DOMAIN}
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web
    networks:
      - condominios_network_prod
    restart: always
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  certbot:
    image: certbot/certbot:latest
    container_name: condominios_certbot_prod
    volumes:
      - certbot_data:/var/www/certbot
      - letsencrypt_data:/etc/letsencrypt
    entrypoint: /bin/sh -c "trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;"
    networks:
      - condominios_network_prod
    restart: always
```

Add new volumes at the bottom of the volumes section:

```yaml
  certbot_data:
    driver: local
  letsencrypt_data:
    driver: local
```

Add `DOMAIN` to `.env.production` documentation (see Step 5).

- [ ] **Step 4: Create initial Let's Encrypt setup script**

Create `scripts/init-letsencrypt.sh`:

```bash
#!/bin/bash
# Initial Let's Encrypt certificate setup.
# Run this ONCE before starting the production stack.
# Usage: DOMAIN=yourdomain.com EMAIL=admin@yourdomain.com ./scripts/init-letsencrypt.sh

set -e

DOMAIN="${DOMAIN:?DOMAIN env var is required}"
EMAIL="${EMAIL:?EMAIL env var is required}"
STAGING="${STAGING:-0}"  # Set STAGING=1 for testing to avoid rate limits

echo "Setting up Let's Encrypt for ${DOMAIN}..."

# Create required directories
mkdir -p nginx/logs
mkdir -p /var/lib/docker/volumes/condominios_certbot_data/_data
mkdir -p /var/lib/docker/volumes/condominios_letsencrypt_data/_data

# Start nginx in HTTP-only mode to pass the ACME challenge
# Temporarily use a minimal config without SSL
docker compose -f docker-compose.prod.yml up -d nginx

# Wait for nginx to be ready
sleep 5

STAGING_FLAG=""
if [ "$STAGING" = "1" ]; then
    STAGING_FLAG="--staging"
    echo "Using Let's Encrypt STAGING environment (no rate limits)"
fi

# Obtain the certificate
docker compose -f docker-compose.prod.yml run --rm certbot \
    certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    ${STAGING_FLAG} \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}"

echo "Certificate obtained. Restarting nginx with SSL..."
docker compose -f docker-compose.prod.yml restart nginx

echo "Done. Certbot will auto-renew every 12 hours."
```

Make it executable:

```bash
chmod +x scripts/init-letsencrypt.sh
```

- [ ] **Step 5: Document required environment variables**

Add to `.env.production.example` (create if it does not exist):

```
# Domain Configuration (required)
DOMAIN=yourdomain.com
```

- [ ] **Step 6: Verify configuration**

```bash
# Validate the template substitution locally
DOMAIN=example.com envsubst '${DOMAIN}' < nginx/conf.d/condominios.conf.template > /tmp/test.conf
cat /tmp/test.conf | grep server_name
# Expected: server_name example.com www.example.com;

# Validate the resulting nginx config syntax (requires docker)
docker run --rm -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
    -v /tmp/test.conf:/etc/nginx/conf.d/condominios.conf:ro \
    nginx:alpine nginx -t
```

---

## Task 2: Nginx Rate Limiting Fix

**Context:** `nginx/nginx.conf` lines 49-50 define rate limiting zones using `$binary_remote_addr`. When nginx is behind a load balancer or CDN, all traffic appears to come from the same IP (the proxy), so one legitimate user can exhaust the limit for everyone behind the same NAT. The fix is to extract the real client IP from `X-Forwarded-For` and use that for rate limiting.

**Files:**
- Modify: `nginx/nginx.conf`
- Modify: `nginx/conf.d/condominios.conf.template` (or `condominios.conf` if Task 1 is not applied)

**Prerequisite:** Task 1 must be completed first (both files are modified).

- [ ] **Step 1: Add real IP extraction to nginx.conf**

Replace the rate limiting section in `nginx/nginx.conf`:

Before:
```nginx
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
```

After:
```nginx
    # Real IP extraction — trust only the internal Docker network
    # When nginx is the outermost proxy, $remote_addr is always the real client.
    # When a CDN or external load balancer sits in front, set its CIDR here.
    set_real_ip_from 172.16.0.0/12;   # Docker bridge networks
    set_real_ip_from 10.0.0.0/8;      # Private networks (cloud LBs)
    real_ip_header X-Forwarded-For;
    real_ip_recursive on;

    # Use $realip_remote_addr (the extracted real IP) for rate limiting.
    # Falls back to $remote_addr when no trusted proxy header is present.
    map $realip_remote_addr $rate_limit_key {
        default $realip_remote_addr;
        ""      $binary_remote_addr;
    }

    # Rate Limiting
    limit_req_zone $rate_limit_key zone=api_limit:10m rate=10r/s;
    limit_req_zone $rate_limit_key zone=login_limit:10m rate=5r/m;
```

- [ ] **Step 2: Update proxy_set_header directives in condominios.conf.template**

Replace every `proxy_set_header X-Real-IP $remote_addr;` with:

```nginx
        proxy_set_header X-Real-IP $realip_remote_addr;
```

This ensures Django's `REMOTE_ADDR` (via `X-Real-IP`) always reflects the actual client, not the proxy.

- [ ] **Step 3: Add the ngx_http_realip_module availability note**

The `ngx_http_realip_module` is compiled into the official `nginx:alpine` image. No additional installation is needed.

Verify with:

```bash
docker run --rm nginx:alpine nginx -V 2>&1 | grep realip
# Expected: --with-http_realip_module
```

- [ ] **Step 4: Verify configuration syntax**

```bash
# Full config validation after both tasks
DOMAIN=example.com envsubst '${DOMAIN}' < nginx/conf.d/condominios.conf.template > /tmp/test.conf
docker run --rm \
    -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
    -v /tmp/test.conf:/etc/nginx/conf.d/condominios.conf:ro \
    nginx:alpine nginx -t
# Expected: nginx: configuration file /etc/nginx/nginx.conf test is successful
```

---

## Task 3: CI Docker Build & Push

**Context:** `.github/workflows/ci.yml` has `test`, `code-quality`, `frontend-test`, `frontend-build`, and `security` jobs, but no job that builds or publishes a Docker image. There is no automated image available for deployment. The image should be published to GitHub Container Registry (ghcr.io) only on pushes to `master`/`main`, not on pull requests.

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add docker-build job after all quality gates pass**

Append to `.github/workflows/ci.yml` before the `build-status` job:

```yaml
  docker-build:
    name: Docker Build & Push
    runs-on: ubuntu-latest
    needs: [test, code-quality, frontend-test, frontend-build]
    # Only build and push on direct pushes to master/main — not on PRs
    if: github.event_name == 'push' && (github.ref == 'refs/heads/master' || github.ref == 'refs/heads/main')
    permissions:
      contents: read
      packages: write

    steps:
    - uses: actions/checkout@v3

    - name: Log in to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract Docker metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ghcr.io/${{ github.repository }}
        tags: |
          type=raw,value=latest
          type=sha,prefix=,format=short
          type=ref,event=branch

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        build-args: |
          NEXT_PUBLIC_API_URL=${{ secrets.PRODUCTION_API_URL }}
          BUILD_DATE=${{ github.event.head_commit.timestamp }}
          VCS_REF=${{ github.sha }}
```

- [ ] **Step 2: Update build-status job to include docker-build**

The `build-status` job's `needs` list does not include `docker-build` because `docker-build` only runs on push to main, but `build-status` runs on PRs too. The `if: always()` guard on `build-status` means it will still run on PRs without `docker-build`. No change is needed to `build-status`.

- [ ] **Step 3: Document required GitHub secrets**

Add a comment block at the top of `.github/workflows/ci.yml` after the `on:` block:

```yaml
# Required GitHub Secrets:
#   PRODUCTION_API_URL   — e.g. https://api.yourdomain.com/api
#   PRODUCTION_DOMAIN    — e.g. yourdomain.com
# GITHUB_TOKEN is automatically provided by GitHub Actions.
```

- [ ] **Step 4: Verify**

After pushing to master, check:

```bash
# In the repository, confirm the package appears under Packages tab
# Or via gh CLI:
gh api /user/packages?package_type=container
```

---

## Task 4: CI Security Checks Mandatory

**Context:** `.github/workflows/ci.yml` lines 174 and 178 both have `continue-on-error: true` on the Bandit and Safety steps. This means security failures are silently ignored and do not block the pipeline. The `build-status` job does not check the `security` job result either (line 204 checks only `test`, `code-quality`, `frontend-build`, `frontend-test`).

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Remove continue-on-error from Bandit**

Before:
```yaml
    - name: Run Bandit security linter
      run: |
        bandit -r core/ condominios_manager/ -ll -f json -o bandit-report.json
      continue-on-error: true
```

After:
```yaml
    - name: Run Bandit security linter
      run: |
        bandit -r core/ condominios_manager/ \
          --severity-level medium \
          --confidence-level medium \
          -f json -o bandit-report.json
        bandit -r core/ condominios_manager/ \
          --severity-level medium \
          --confidence-level medium
```

Note: `bandit` exits non-zero when issues are found. Running it twice — once to write the JSON artifact and once to print to stdout for the CI log — is intentional because `-f json` suppresses terminal output.

- [ ] **Step 2: Remove continue-on-error from Safety**

Before:
```yaml
    - name: Check for known security vulnerabilities
      run: |
        safety check --json
      continue-on-error: true
```

After:
```yaml
    - name: Check for known security vulnerabilities
      run: |
        safety check --full-report
```

- [ ] **Step 3: Make build-status check the security job**

In the `build-status` job, update `needs` and add the security check:

Before:
```yaml
    needs: [test, code-quality, security, frontend-test, frontend-build]
```

(The `needs` line already includes `security` — it was just not being checked in the shell script body.)

Add the check inside the `Check build status` step:

```bash
        if [ "${{ needs.security.result }}" != "success" ]; then
          echo "::error::Security audit failed!"
          exit 1
        fi
```

Insert this block after the existing `frontend-test` check and before the final `echo "Build completed successfully!"`.

- [ ] **Step 4: Verify no existing Bandit issues block the pipeline**

Run locally before merging:

```bash
bandit -r core/ condominios_manager/ --severity-level medium --confidence-level medium
# If issues appear, fix them rather than suppressing with noqa
```

---

## Task 5: CI Frontend Build with Dynamic Environment

**Context:** `.github/workflows/ci.yml` line 150 hardcodes `NEXT_PUBLIC_API_URL: http://localhost:8008/api` for the `frontend-build` job. This verifies that the build compiles, but the production image built in Task 3 also needs the correct production URL baked in via build args.

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add conditional env to frontend-build job**

The `frontend-build` job verifies compilation on PRs. The production URL is not needed here — localhost is sufficient to confirm the build succeeds. No change is needed to `frontend-build`.

The production `NEXT_PUBLIC_API_URL` is injected at Docker build time via `build-args` in the `docker-build` job (Task 3, Step 1). The `NEXT_PUBLIC_API_URL` secret is already referenced there.

- [ ] **Step 2: Add a build-args section comment to the Dockerfile for documentation**

Verify the `Dockerfile` frontend build stage passes `NEXT_PUBLIC_API_URL` as a build arg. Open `Dockerfile` and confirm a pattern like:

```dockerfile
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
```

If this `ARG`/`ENV` pair is absent in the frontend build stage, add it before the `npm run build` step.

- [ ] **Step 3: Document required secrets at top of ci.yml**

The comment added in Task 3 Step 3 already covers this. Confirm `PRODUCTION_API_URL` is listed.

- [ ] **Step 4: Verify**

```bash
# PR builds continue to use localhost — confirm build-status passes on a test PR
# Production builds use the secret — confirm in the docker-build job logs on master push
```

---

## Task 6: Sentry Integration

**Context:** `condominios_manager/settings_production.py` lines 209-218 initialize Sentry only if `SENTRY_DSN` is non-empty. An empty DSN means production errors are silently swallowed. The frontend has no Sentry integration at all. Sentry should be required in production, not optional.

**Files:**
- Modify: `condominios_manager/settings_production.py`
- Modify: `frontend/` (multiple files — see steps)
- Modify: `requirements.txt`

- [ ] **Step 1: Make SENTRY_DSN required in production settings**

In `condominios_manager/settings_production.py`, replace the optional Sentry block:

Before:
```python
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
        send_default_pii=False,
        environment=config("SENTRY_ENVIRONMENT", default="production"),
        release=config("APP_VERSION", default="1.0.0"),
    )
```

After:
```python
from django.core.exceptions import ImproperlyConfigured

SENTRY_DSN = config("SENTRY_DSN", default="")
if not SENTRY_DSN:
    raise ImproperlyConfigured(
        "SENTRY_DSN is required in production. "
        "Set it in .env.production or as an environment variable."
    )

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration()],
    traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
    profiles_sample_rate=config("SENTRY_PROFILES_SAMPLE_RATE", default=0.1, cast=float),
    send_default_pii=False,
    environment=config("SENTRY_ENVIRONMENT", default="production"),
    release=config("APP_VERSION", default="1.0.0"),
)
```

- [ ] **Step 2: Verify sentry-sdk is in requirements.txt**

```bash
grep "sentry-sdk" requirements.txt
```

If absent, add:

```
sentry-sdk[django]>=2.0.0
```

Also verify `sentry_sdk` appears in `pyproject.toml` under `[project.dependencies]`. Add if missing.

- [ ] **Step 3: Install @sentry/nextjs in the frontend**

```bash
cd frontend && npm install @sentry/nextjs
```

- [ ] **Step 4: Create sentry.client.config.ts**

Create `frontend/sentry.client.config.ts`:

```typescript
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (!dsn) {
  console.warn("NEXT_PUBLIC_SENTRY_DSN is not set — Sentry is disabled");
} else {
  Sentry.init({
    dsn,
    tracesSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    integrations: [
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
  });
}
```

- [ ] **Step 5: Create sentry.server.config.ts**

Create `frontend/sentry.server.config.ts`:

```typescript
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    tracesSampleRate: 0.1,
  });
}
```

- [ ] **Step 6: Create sentry.edge.config.ts**

Create `frontend/sentry.edge.config.ts`:

```typescript
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    tracesSampleRate: 0.1,
  });
}
```

- [ ] **Step 7: Run Sentry Next.js wizard or manually update next.config.ts**

The `@sentry/nextjs` package requires wrapping `next.config.ts` with `withSentryConfig`. Read the existing `frontend/next.config.ts` first, then wrap it:

```typescript
import { withSentryConfig } from "@sentry/nextjs";

// ... existing config object ...

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: true,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
});
```

- [ ] **Step 8: Add NEXT_PUBLIC_SENTRY_DSN to docker-compose.prod.yml web service environment**

```yaml
    environment:
      - DJANGO_SETTINGS_MODULE=condominios_manager.settings_production
      - DB_HOST=postgres
      - REDIS_URL=redis://redis:6379/0
      - NEXT_PUBLIC_SENTRY_DSN=${NEXT_PUBLIC_SENTRY_DSN}
```

- [ ] **Step 9: Verify frontend type-checks pass**

```bash
cd frontend && npm run type-check && npm run lint
```

---

## Task 7: Separate Migrations from Container Start

**Context:** `docker-entrypoint.sh` line 17 runs `python manage.py migrate --noinput` on every container start. When multiple web replicas start simultaneously, they all attempt migrations at the same time, causing PostgreSQL advisory lock contention. The migration step should run exactly once as a separate service that completes before the web replicas start.

**Files:**
- Modify: `docker-entrypoint.sh`
- Modify: `docker-compose.prod.yml`
- Create: `scripts/deploy.sh`

- [ ] **Step 1: Remove migrate from entrypoint**

In `docker-entrypoint.sh`, remove the migrate block:

Before:
```bash
# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput
```

After: delete these three lines entirely.

- [ ] **Step 2: Add a migrate service to docker-compose.prod.yml**

Add before the `web` service definition:

```yaml
  migrate:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: condominios_migrate_prod
    command: python manage.py migrate --noinput
    env_file:
      - .env.production
    environment:
      - DJANGO_SETTINGS_MODULE=condominios_manager.settings_production
      - DB_HOST=postgres
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - condominios_network_prod
    restart: "no"
```

Update the `web` service `depends_on` to wait for the migrate service to complete successfully:

Before:
```yaml
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

After:
```yaml
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
```

Apply the same `migrate` dependency to `celery_worker` and `celery_beat`.

- [ ] **Step 3: Create deploy.sh for ordered deployments**

Create `scripts/deploy.sh`:

```bash
#!/bin/bash
# Production deployment script.
# Runs migrations first as a one-shot service, then brings up all containers.
# Usage: ./scripts/deploy.sh [docker-compose flags]

set -e

COMPOSE="docker compose -f docker-compose.prod.yml"

echo "Pulling latest images..."
${COMPOSE} pull

echo "Running database migrations..."
${COMPOSE} run --rm migrate

echo "Starting services..."
${COMPOSE} up -d web nginx redis celery_worker celery_beat certbot "$@"

echo "Deploy complete."
```

Make it executable:

```bash
chmod +x scripts/deploy.sh
```

- [ ] **Step 4: Verify**

```bash
# Validate compose config
docker compose -f docker-compose.prod.yml config --quiet
# Expected: no errors

# Confirm migrate service has restart: "no"
docker compose -f docker-compose.prod.yml config | grep -A5 "migrate:"
```

---

## Task 8: Expanded Health Check

**Context:** `core/views.py` lines 42-55 implement `health_check` that only verifies DB connectivity. Redis failures (OOM, crash, eviction policy changes) are not detected, and disk exhaustion goes unnoticed until writes start failing. Load balancers and orchestrators depend on this endpoint to route traffic.

**Files:**
- Modify: `core/views.py`

- [ ] **Step 1: Expand health_check function**

Replace the existing `health_check` function:

Before:
```python
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request: Request) -> Response:
    """Health check endpoint for load balancers and monitoring."""
    try:
        connection.ensure_connection()
        db_ok = True
    except OperationalError:
        db_ok = False

    status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(
        {"status": "healthy" if db_ok else "unhealthy", "database": db_ok}, status=status_code
    )
```

After:
```python
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request: Request) -> Response:
    """Health check endpoint for load balancers and monitoring.

    Returns 200 when all critical services (DB, Redis) are available.
    Returns 503 when any critical service is degraded.
    Disk space is reported as a warning but does not affect the status code.
    """
    import shutil

    from django.core.cache import cache

    db_ok = _check_database()
    redis_ok = _check_redis(cache)
    disk_free_mb = _check_disk_space()

    all_ok = db_ok and redis_ok
    http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        {
            "status": "healthy" if all_ok else "unhealthy",
            "database": db_ok,
            "redis": redis_ok,
            "disk_free_mb": disk_free_mb,
        },
        status=http_status,
    )


def _check_database() -> bool:
    try:
        connection.ensure_connection()
        return True
    except OperationalError:
        return False


def _check_redis(cache: object) -> bool:
    try:
        from django.core.cache import BaseCache

        if not isinstance(cache, BaseCache):
            return False
        cache.set("health_check_probe", "ok", timeout=5)
        return cache.get("health_check_probe") == "ok"
    except Exception:
        return False


def _check_disk_space() -> int:
    import shutil

    usage = shutil.disk_usage("/")
    return int(usage.free / (1024 * 1024))
```

- [ ] **Step 2: Add the missing imports at the top of views.py**

Verify that `from django.db import connection, OperationalError` is already present. The `shutil` and `cache` imports are done inline inside the helpers to avoid circular import issues.

- [ ] **Step 3: Add type annotations to the helper functions**

Ensure mypy passes:

```python
def _check_database() -> bool: ...
def _check_redis(cache: object) -> bool: ...
def _check_disk_space() -> int: ...
```

- [ ] **Step 4: Run type check and lint**

```bash
ruff check core/views.py && mypy core/views.py
```

- [ ] **Step 5: Test locally**

```bash
python manage.py runserver &
curl -s http://localhost:8008/health/ | python -m json.tool
# Expected: {"status": "healthy", "database": true, "redis": true, "disk_free_mb": <N>}
```

---

## Task 9: Email Configuration Validation

**Context:** `condominios_manager/settings_production.py` lines 113-120 configure SMTP email. `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` default to empty strings. If the SMTP backend is active but credentials are missing, all email sending silently fails at runtime (password reset, admin error notifications, etc.). The failure only surfaces when an email is actually sent.

**Files:**
- Modify: `condominios_manager/settings_production.py`

- [ ] **Step 1: Add validation block after email settings**

After the email configuration block (after `SERVER_EMAIL = ...`), add:

```python
# Validate email credentials when using SMTP backend.
# If credentials are absent, fall back to console backend and log a warning
# so the application starts but email features are visibly degraded.
_smtp_backend = "django.core.mail.backends.smtp.EmailBackend"
if EMAIL_BACKEND == _smtp_backend and (not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD):
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is not set. "
        "Falling back to console email backend — emails will not be delivered. "
        "Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env.production to enable SMTP."
    )
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

Design rationale: raising `ImproperlyConfigured` here would prevent the application from starting when email is genuinely not needed (some deployments do not send email). A logged warning plus automatic fallback is safer than a hard crash.

- [ ] **Step 2: Verify the warning appears on startup when credentials are missing**

```bash
DJANGO_SETTINGS_MODULE=condominios_manager.settings_production \
  EMAIL_HOST_USER="" \
  EMAIL_HOST_PASSWORD="" \
  SENTRY_DSN=https://fake@sentry.io/1 \
  python -c "import django; django.setup()" 2>&1 | grep "email backend"
# Expected: WARNING ... Falling back to console email backend
```

- [ ] **Step 3: Run type check**

```bash
mypy condominios_manager/settings_production.py
```

---

## Task 10: PgBouncer Connection Pooling

**Context:** `condominios_manager/settings_production.py` line 103 sets `CONN_MAX_AGE=600`. With 4 gunicorn workers (default), this creates up to 4 persistent connections per web container. With Celery concurrency=2, that is 6 more. Under load with multiple replicas, connection counts easily exceed PostgreSQL's default `max_connections=100`. PgBouncer in transaction-pooling mode multiplexes many application connections onto few server connections.

**Files:**
- Modify: `docker-compose.prod.yml`
- Modify: `condominios_manager/settings_production.py`
- Create: `pgbouncer/pgbouncer.ini`
- Create: `pgbouncer/userlist.txt.template`

- [ ] **Step 1: Create pgbouncer configuration**

Create `pgbouncer/pgbouncer.ini`:

```ini
[databases]
; Route all connections to the PostgreSQL service on the internal network.
; DB_NAME, DB_USER are substituted at container start via envsubst.
* = host=postgres port=5432 dbname=${DB_NAME}

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

; Transaction pooling: connection is returned to pool after each transaction.
; This is the only mode that provides real multiplexing.
pool_mode = transaction

; Maximum total connections PgBouncer will open to PostgreSQL.
; PostgreSQL max_connections should be set higher than this (e.g. 30).
server_pool_size = 20
max_client_conn = 100
default_pool_size = 20

; Connection limits
reserve_pool_size = 5
reserve_pool_timeout = 3

; Logging
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1

; Health check query
server_check_query = SELECT 1
server_check_delay = 30

; Keep connections alive
server_idle_timeout = 600
client_idle_timeout = 0
```

- [ ] **Step 2: Create userlist template**

Create `pgbouncer/userlist.txt.template`:

```
"${DB_USER}" "${DB_PASSWORD}"
```

This file is generated at container start from environment variables. It must NOT be committed with real credentials.

Add `pgbouncer/userlist.txt` to `.gitignore`.

- [ ] **Step 3: Create PgBouncer entrypoint script**

Create `pgbouncer/entrypoint.sh`:

```bash
#!/bin/sh
set -e

# Generate userlist.txt from environment variables
envsubst '${DB_USER} ${DB_PASSWORD}' \
    < /etc/pgbouncer/userlist.txt.template \
    > /etc/pgbouncer/userlist.txt

# Generate pgbouncer.ini from environment variables
envsubst '${DB_NAME}' \
    < /etc/pgbouncer/pgbouncer.ini.template \
    > /etc/pgbouncer/pgbouncer.ini

exec pgbouncer /etc/pgbouncer/pgbouncer.ini
```

Rename `pgbouncer/pgbouncer.ini` to `pgbouncer/pgbouncer.ini.template` and make `entrypoint.sh` executable.

- [ ] **Step 4: Add PgBouncer to docker-compose.prod.yml**

Add before the `web` service:

```yaml
  pgbouncer:
    image: edoburu/pgbouncer:latest
    container_name: condominios_pgbouncer_prod
    env_file:
      - .env.production
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - POOL_MODE=transaction
      - MAX_CLIENT_CONN=100
      - DEFAULT_POOL_SIZE=20
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - condominios_network_prod
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -h localhost -p 5432 -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 3
```

Note: `edoburu/pgbouncer` accepts configuration via environment variables directly, so the `ini` template approach above is optional — use whichever matches the chosen image. The env-var approach is simpler with `edoburu/pgbouncer`.

- [ ] **Step 5: Point Django at PgBouncer instead of PostgreSQL**

In `condominios_manager/settings_production.py`, update the database host:

Before:
```python
DATABASES["default"]["CONN_MAX_AGE"] = 600
```

After:
```python
# PgBouncer handles connection pooling — Django must not maintain persistent connections
# (CONN_MAX_AGE=0) because transaction-mode pooling returns the connection to the pool
# after each transaction, which is incompatible with Django's persistent connection model.
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["HOST"] = config("PGBOUNCER_HOST", default="pgbouncer")
DATABASES["default"]["PORT"] = config("PGBOUNCER_PORT", default=5432, cast=int)
```

Add to `docker-compose.prod.yml` web/celery service environment:

```yaml
      - PGBOUNCER_HOST=pgbouncer
      - PGBOUNCER_PORT=5432
```

Update `depends_on` for `web`, `celery_worker`, and `celery_beat` to wait for `pgbouncer`:

```yaml
      pgbouncer:
        condition: service_healthy
```

- [ ] **Step 6: Verify**

```bash
docker compose -f docker-compose.prod.yml config --quiet
# Confirm pgbouncer service appears and depends_on is correct

# After stack is running:
docker exec condominios_pgbouncer_prod psql -p 5432 -U ${DB_USER} pgbouncer -c "SHOW POOLS;"
```

---

## Task 11: Structured JSON Logging

**Context:** `condominios_manager/settings_production.py` lines 132-203 configure logging with `RotatingFileHandler` writing to `/app/logs/production.log` and `/app/logs/errors.log`. Docker captures stdout/stderr natively via its log driver; writing to local files inside the container duplicates this and complicates log aggregation. The `pythonjsonlogger` formatter is defined (line 143) but the `json` formatter is never assigned to any handler.

**Files:**
- Modify: `condominios_manager/settings_production.py`
- Modify: `requirements.txt` (if `python-json-logger` is absent)
- Modify: `pyproject.toml` (same)

- [ ] **Step 1: Verify python-json-logger is in requirements**

```bash
grep "python-json-logger" requirements.txt
```

If absent, add `python-json-logger>=2.0.7` to `requirements.txt` and to `pyproject.toml` under `[project.dependencies]`.

- [ ] **Step 2: Replace the LOGGING config with JSON-to-stdout**

Replace the entire `LOGGING` dict in `condominios_manager/settings_production.py`:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        },
        "stderr": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "json",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        },
    },
    "root": {
        "handlers": ["stdout"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["stdout", "stderr"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["stderr", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["stderr", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "core": {
            "handlers": ["stdout", "stderr"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

Rationale: Docker captures stdout and stderr. The log driver (json-file, fluentd, CloudWatch, etc.) handles persistence and rotation. Writing files inside the container is redundant and requires volume mounts just for logs.

- [ ] **Step 3: Remove the logs volume mount from docker-compose.prod.yml**

Remove `./logs:/app/logs` from the `web`, `celery_worker`, and `celery_beat` volume mounts. The `/app/logs` directory no longer exists in production.

- [ ] **Step 4: Run type check**

```bash
ruff check condominios_manager/settings_production.py
mypy condominios_manager/settings_production.py
```

- [ ] **Step 5: Verify JSON output locally**

```bash
DJANGO_SETTINGS_MODULE=condominios_manager.settings_production \
  SENTRY_DSN=https://fake@sentry.io/1 \
  python -c "
import django, logging
django.setup()
logging.getLogger('core').info('test message', extra={'user_id': 42})
" 2>&1
# Expected: JSON line with asctime, name, levelname, message, user_id
```

---

## Task 12: Celery Monitoring (Flower)

**Context:** `docker-compose.prod.yml` defines `celery_worker` and `celery_beat` but there is no visibility into task queues, worker status, or task failures. `condominios_manager/celery.py` has no result backend configured, so task state is not persisted. Without monitoring, failed tasks are invisible until a user reports a missing side effect.

**Files:**
- Modify: `docker-compose.prod.yml`
- Modify: `condominios_manager/celery.py`
- Modify: `condominios_manager/settings_production.py`
- Modify: `requirements.txt` and `pyproject.toml`

- [ ] **Step 1: Add Celery result backend to settings**

In `condominios_manager/settings_production.py`, add after the cache configuration:

```python
# ============================================================
# CELERY CONFIGURATION
# ============================================================

CELERY_BROKER_URL = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_RESULT_EXPIRES = 60 * 60 * 24  # 24 hours
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_TASK_TRACK_STARTED = True

# Retry policy for all tasks unless overridden per-task
CELERY_TASK_ANNOTATIONS = {
    "*": {
        "max_retries": 3,
        "default_retry_delay": 60,  # seconds, exponential backoff applied per-task
    }
}

# Dead letter: tasks that exhaust retries are routed to the dead_letter queue
CELERY_TASK_ROUTES = {
    "*": {"queue": "default"},
}
```

- [ ] **Step 2: Update celery.py to pick up Django settings**

`condominios_manager/celery.py` already calls `app.config_from_object("django.conf:settings", namespace="CELERY")`. No change needed for broker/result backend — they will be picked up automatically once `CELERY_RESULT_BACKEND` is set in settings.

- [ ] **Step 3: Add Flower to requirements**

Add to `requirements.txt`:

```
flower>=2.0.0
```

Add to `pyproject.toml` under `[project.dependencies]`:

```
"flower>=2.0.0",
```

- [ ] **Step 4: Add Flower service to docker-compose.prod.yml**

Add after `celery_beat`:

```yaml
  flower:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: condominios_flower_prod
    command: >
      celery -A condominios_manager flower
        --port=5555
        --basic_auth=${FLOWER_USER}:${FLOWER_PASSWORD}
        --url_prefix=flower
    env_file:
      - .env.production
    environment:
      - DJANGO_SETTINGS_MODULE=condominios_manager.settings_production
      - CELERY_BROKER_URL=${REDIS_URL}
      - CELERY_RESULT_BACKEND=redis://${REDIS_HOST}:6379/1
    depends_on:
      redis:
        condition: service_healthy
      celery_worker:
        condition: service_started
    networks:
      - condominios_network_prod
    restart: always
    ports:
      - "5555:5555"
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:5555/flower/healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 3
```

- [ ] **Step 5: Expose Flower through nginx behind authentication**

Add a location block to `nginx/conf.d/condominios.conf.template` inside the HTTPS server block:

```nginx
    # Flower Celery monitoring (basic auth provided by Flower itself)
    location /flower/ {
        proxy_pass http://flower:5555/flower/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $realip_remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Restrict Flower to admin IPs only — add your office/VPN CIDR here
        # allow 203.0.113.0/24;
        # deny all;
    }
```

Remove the direct port exposure (`ports: - "5555:5555"`) from the Flower service in production once nginx routing is confirmed. Keep it only for local development access.

- [ ] **Step 6: Document required environment variables**

Add to `.env.production.example`:

```
# Flower Celery Monitoring
FLOWER_USER=admin
FLOWER_PASSWORD=changeme-use-strong-password
REDIS_HOST=redis
```

- [ ] **Step 7: Verify**

```bash
docker compose -f docker-compose.prod.yml config --quiet
# Confirm flower service appears

# After stack is running:
curl -u admin:changeme http://localhost:5555/flower/api/workers
# Expected: JSON with worker info
```

---

## Verification Checklist

After implementing all 12 tasks, verify the following:

### Nginx
- [ ] `DOMAIN=example.com envsubst '${DOMAIN}' < nginx/conf.d/condominios.conf.template > /tmp/test.conf && grep server_name /tmp/test.conf` shows no literal `yourdomain.com`
- [ ] `docker run --rm -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro -v /tmp/test.conf:/etc/nginx/conf.d/condominios.conf:ro nginx:alpine nginx -t` exits 0
- [ ] `docker run --rm nginx:alpine nginx -V 2>&1 | grep realip` shows `--with-http_realip_module`
- [ ] `scripts/init-letsencrypt.sh` exists and is executable

### CI Pipeline
- [ ] `.github/workflows/ci.yml` has no `continue-on-error: true` in the security job
- [ ] `docker-build` job exists and runs only on push to master/main
- [ ] `build-status` job checks `needs.security.result`
- [ ] Required secrets are documented in a comment at the top of ci.yml

### Django
- [ ] `condominios_manager/settings_production.py` raises `ImproperlyConfigured` when `SENTRY_DSN` is empty
- [ ] Email fallback warning appears when `EMAIL_HOST_USER` is empty and SMTP backend is configured
- [ ] `CONN_MAX_AGE=0` is set (PgBouncer handles pooling)
- [ ] `LOGGING` config uses only stdout/stderr handlers with JSON formatter
- [ ] `CELERY_RESULT_BACKEND` is configured

### Health Check
- [ ] `GET /health/` returns `{"status": "healthy", "database": true, "redis": true, "disk_free_mb": N}`
- [ ] `GET /health/` returns 503 when database is unreachable
- [ ] `ruff check core/views.py && mypy core/views.py` exits 0

### Docker Compose
- [ ] `docker compose -f docker-compose.prod.yml config --quiet` exits 0
- [ ] `migrate` service has `restart: "no"` and `condition: service_completed_successfully`
- [ ] `web`, `celery_worker`, `celery_beat` depend on `migrate` completing
- [ ] `pgbouncer` service present with healthcheck
- [ ] `flower` service present with basic auth flag
- [ ] File-based log volume mounts removed from web/celery services
- [ ] Certbot service and `letsencrypt_data` volume present

### Frontend
- [ ] `frontend/sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts` exist
- [ ] `cd frontend && npm run type-check && npm run lint` exits 0
- [ ] `@sentry/nextjs` appears in `frontend/package.json`

### Dependencies
- [ ] `python-json-logger` in `requirements.txt` and `pyproject.toml`
- [ ] `flower` in `requirements.txt` and `pyproject.toml`
- [ ] `sentry-sdk[django]` in `requirements.txt` and `pyproject.toml`
- [ ] `ruff check && ruff format --check` exits 0 for all modified Python files
- [ ] `mypy core/ condominios_manager/` exits 0
