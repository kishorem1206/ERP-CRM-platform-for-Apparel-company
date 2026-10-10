# Deploying Apparel ERP (Render + Neon + Cloudflare, all free tier)

| Piece | Where | Free-tier notes |
|---|---|---|
| App (Next.js + FastAPI in one container) | Render web service | 512 MB RAM (app uses ~270 MB). Sleeps after 15 min without traffic; 750 instance hours/month per workspace |
| Redis (login OTPs, rate limits, 2FA, live notifications, AI chat history) | Render Key Value | One free instance per workspace, memory only — contents reset on restart, which these uses tolerate |
| Postgres | Neon | 0.5 GB storage (the database is ~20 MB today); suspends when idle and wakes on the next query |
| Scheduled jobs (alerts, cleanups, delayed WhatsApp sends) | Cloudflare Worker Cron Trigger | Calls the app every 10 min in Indian working hours (keeps it awake, no cold starts for users) and hourly overnight |
| Attachments (optional) | Cloudflare R2 | 10 GB. Without it, uploaded attachments are lost whenever Render restarts the app |

Celery is gone: jobs run inside the app when `/api/v1/internal/cron/tick` is called (see `backend/app/workers/jobs.py`).

---

## 1. Neon — the database

1. Sign up at <https://neon.tech> → **New project**.
2. **Postgres version 16** (matches local), **region: AWS Asia Pacific (Singapore)** — the same region as the Render service.
3. On the project dashboard, **Connect** → turn **Connection pooling off** → copy the connection string. It looks like
   `postgresql://neondb_owner:...@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
   Use this direct one, not the `-pooler` host.
4. Copy the local database into it (schema, data and migration version), with the local Docker stack running:
   ```bash
   ./deploy/migrate-to-neon.sh 'postgresql://neondb_owner:...@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
   ```
   It refuses to run against a non-empty database, and prints a row-count comparison at the end.

## 2. Render — the app

1. Sign up at <https://render.com> with GitHub, and give it access to this repository.
2. **New → Blueprint** → pick this repository. Render reads `render.yaml` and proposes two resources: `apparel-erp` (web) and `apparel-erp-cache` (Key Value).
3. Fill in the prompted values:
   - `DATABASE_URL` — the Neon connection string from step 1.3.
   - `ADMIN_SEED_PASSWORD` — the password for `admin@company.com`. Only used if the database has no admin yet; with a copied database the existing password stays.
   - `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_API_BASE_URL`, `LLM_MODEL` — copy from your local `.env` to keep the AI assistant working (leave empty to disable it).
4. **Apply**. The first build takes ~10 minutes. On every start the container runs database migrations, then the idempotent seed, then the API and web server — so deploying a new version needs nothing but a push to `main`.
5. Note the URL Render gives the service (e.g. `https://apparel-erp.onrender.com`) and the generated **CRON_SECRET** (service → Environment).

## 3. Cloudflare — scheduled jobs

From a machine with Node.js:

```bash
cd deploy/cloudflare-cron
# set APP_URL in wrangler.toml to the Render URL from step 2.5
npx wrangler login
npx wrangler deploy
npx wrangler secret put CRON_SECRET     # paste the value from Render
```

Check it's firing (after the next 10-minute mark in working hours):

```bash
curl -s -H "X-Cron-Secret: <CRON_SECRET>" https://apparel-erp.onrender.com/api/v1/internal/cron/status
```

Every job should show `last_status: ok`. Cloudflare dashboard → Workers → `apparel-erp-cron` → Logs also shows each tick.

The cron times are UTC (`wrangler.toml`): `*/10 3-15 * * *` is roughly 08:30–21:30 IST. Change them if your client works different hours; at most 5 cron triggers per Cloudflare account on the free plan.

## 4. Optional — your own domain through Cloudflare

1. Render → `apparel-erp` → Settings → **Custom Domains** → add e.g. `erp.yourcompany.com`.
2. Cloudflare DNS for that domain → add `CNAME erp → apparel-erp.onrender.com` with **Proxy status: DNS only** (grey cloud), so Render can verify it and issue the certificate.
3. Once Render shows the domain as verified you can switch the record to **Proxied** (orange cloud) with SSL/TLS mode **Full (strict)**.
4. Update `APP_URL` in `deploy/cloudflare-cron/wrangler.toml` and run `npx wrangler deploy` again.

## 5. Optional — attachments on Cloudflare R2

1. Cloudflare → R2 → **Create bucket** (e.g. `apparel-erp-files`).
2. R2 → **Manage API tokens** → create a token with Object Read & Write on that bucket. Note the Access Key ID, Secret Access Key and the S3 endpoint (`https://<account_id>.r2.cloudflarestorage.com`).
3. Render → `apparel-erp` → Environment → add:
   `STORAGE_BACKEND=s3`, `S3_ENDPOINT_URL=<endpoint>`, `AWS_S3_BUCKET=<bucket>`, `AWS_ACCESS_KEY_ID=<key id>`, `AWS_SECRET_ACCESS_KEY=<secret>`.

## Day-to-day

- **Deploy a change:** push to `main`. Render rebuilds and migrations run at startup.
- **Run one job now:** `curl -X POST -H "X-Cron-Secret: <secret>" "https://<app>/api/v1/internal/cron/tick?job=check_low_stock"`.
- **First request after a quiet night** can take ~30–60 s while Render wakes the service; during working hours the cron keeps it awake.
- **Local development** is unchanged (`docker compose up`); a small `cron` container calls the same tick every 10 minutes.
