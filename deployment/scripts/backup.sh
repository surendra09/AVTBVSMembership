#!/usr/bin/env sh
# Nightly backup of the MySQL database and the private document store.
# Usage (cron, on the Docker host):  0 2 * * * /opt/avtbvs/deployment/scripts/backup.sh /var/backups/avtbvs
set -eu
DEST="${1:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"
cd "$(dirname "$0")/../.."
. ./.env
docker compose exec -T db sh -c "mysqldump --single-transaction --routines --triggers -u root -p\"\$MYSQL_ROOT_PASSWORD\" ${MYSQL_DATABASE:-avtbvs}" \
  | gzip > "$DEST/db-$STAMP.sql.gz"
docker compose run --rm -T --no-deps -v "$(realpath "$DEST")":/backup --entrypoint "" api \
  tar czf "/backup/files-$STAMP.tar.gz" -C /data private
chmod 600 "$DEST"/*-"$STAMP".*
# keep 30 days
find "$DEST" -type f -mtime +30 -delete
echo "Backup written to $DEST (db-$STAMP.sql.gz, files-$STAMP.tar.gz)"
