#!/bin/bash
set -euo pipefail
base=/srv/ai-apps/mastercatalog
revision=${1:?commit required}
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || exit 2
mkdir -p "$base/releases" "$base/data"
exec 9>"$base/deploy.lock"
flock -n 9
# An empty database must never be mistaken for a successful production deploy.
test -s "$base/data/aareas.db" || { echo 'Missing production data/aareas.db'; exit 1; }
python3 - "$base/data/aareas.db" <<'PY'
import sqlite3, sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro', uri=True)
assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
assert c.execute('SELECT COUNT(*) FROM products').fetchone()[0]>0, 'Database has no products'
PY
release="$base/releases/$revision"
test ! -e "$release"
mkdir "$release"
tar -xzf "$base/incoming.tar.gz" -C "$release" --no-same-owner
previous=$(readlink "$base/current" || true)
ln -s "$release" "$base/current.next"
mv -Tf "$base/current.next" "$base/current"
rollback() {
  if [[ -n "$previous" ]]; then
    ln -s "$previous" "$base/current.next"
    mv -Tf "$base/current.next" "$base/current"
    systemctl --user restart mastercatalog
  else
    systemctl --user stop mastercatalog
    rm -f "$base/current"
  fi
}
systemctl --user restart mastercatalog || { rollback; exit 1; }
for attempt in {1..15}; do
  if curl --fail --silent http://127.0.0.1:28765/api/stats | python3 -c 'import json,sys; assert json.load(sys.stdin)["products"]>0'; then
    echo "Deployed $revision (previous: $previous)"
    exit 0
  fi
  sleep 1
done
rollback
exit 1
