#!/bin/bash
# Copies the local docker-compose Postgres (schema + data + alembic_version)
# into an EMPTY target database, e.g. a new Neon database.
#
#   ./deploy/migrate-to-neon.sh 'postgresql://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
#
# Runs pg_dump/psql inside the local postgres container, so no local Postgres
# client is needed. Stops on the first error; the target is left as-is so
# you can inspect it, drop its schema and retry.
set -euo pipefail

TARGET_URL="${1:?usage: $0 <target-postgres-url>}"
cd "$(dirname "$0")/.."

PG_USER=$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-)
PG_DB=$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2-)

echo "Checking the target is empty..."
TABLES=$(docker compose exec -T postgres psql "$TARGET_URL" -tAc \
  "select count(*) from information_schema.tables where table_schema='public'")
if [ "$TABLES" != "0" ]; then
  echo "Target already has $TABLES tables in schema public — refusing to overwrite. Use an empty database." >&2
  exit 1
fi

echo "Copying ${PG_DB} -> target (this can take a minute)..."
docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$PG_DB" \
    --no-owner --no-privileges --format=plain \
  | docker compose exec -T postgres psql "$TARGET_URL" --quiet --set ON_ERROR_STOP=1 >/dev/null

echo "Verifying..."
for t in companies users production_lots sales_orders alembic_version; do
  src=$(docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -tAc "select count(*) from $t")
  dst=$(docker compose exec -T postgres psql "$TARGET_URL" -tAc "select count(*) from $t")
  printf '  %-18s local=%-6s target=%-6s %s\n' "$t" "$src" "$dst" "$([ "$src" = "$dst" ] && echo ok || echo MISMATCH)"
done
echo "Target migration version: $(docker compose exec -T postgres psql "$TARGET_URL" -tAc 'select version_num from alembic_version')"
echo "Done."
