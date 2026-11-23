#!/usr/bin/env sh
# Restore from backups made by backup.sh.  Usage: restore.sh db-XXXX.sql.gz files-XXXX.tar.gz
set -eu
DB_FILE="$1"; FILES="$2"
cd "$(dirname "$0")/../.."
. ./.env
echo "This will OVERWRITE the database ${MYSQL_DATABASE:-avtbvs} and private files. Ctrl+C to abort."; sleep 5
gunzip -c "$DB_FILE" | docker compose exec -T db sh -c "mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" ${MYSQL_DATABASE:-avtbvs}"
docker compose run --rm -T --no-deps -v "$(realpath "$(dirname "$FILES")")":/backup --entrypoint "" api \
  sh -c "rm -rf /data/private && tar xzf /backup/$(basename "$FILES") -C /data"
echo "Restore complete. Restart: docker compose restart api worker"
