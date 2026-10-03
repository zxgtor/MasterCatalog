# MasterCatalog → Coin

main push and manual workflow_dispatch run build/smoke tests → Tailscale → SSH → release → HTTPS verification. Only main deploys. Runtime uses Python 3 standard library, port 28765. Database stays outside releases. No root deployment script or passwordless sudo is required. Existing AppGallery is untouched.

## One-time user setup

1. Provide the existing populated aareas.db (do not commit it). The repository cannot recreate products: import_sqlite.py requires ignored master_products.json. Transfer the database while its writer is stopped, or use SQLite backup; do not copy a live WAL database alone:

   scp /path/to/aareas.db coin:/srv/ai-apps/mastercatalog/data/aareas.db

2. GitHub repository Settings → Secrets and variables → Actions (repository secrets, no paid environment required):
   - TS_OAUTH_CLIENT_ID / TS_OAUTH_SECRET: Tailscale OAuth client, auth_keys write scope, tag:mastercatalog-ci. Allow this tag to reach 100.80.142.52:22 only in the tailnet policy.
   - COIN_SSH_KEY: a dedicated Ed25519 deployment private key. Add its public key to Coin jason ~/.ssh/authorized_keys with `restrict` prefix. Use `gh secret set COIN_SSH_KEY -R zxgtor/MasterCatalog < private-key-file` locally; never paste the key into chat. It grants access as jason; a dedicated restricted account would require additional administrator provisioning.
   - COIN_KNOWN_HOSTS: pinned Coin Ed25519 host key (already populated by setup after authenticated SSH inspection). Never use StrictHostKeyChecking=no.

3. Cloudflare DNS: A record mastercatalog → 99.228.229.150 (Coin public IPv4 observed during setup; confirm router/public IP before saving). Start DNS-only for certificate issuance. Do not add an AAAA record unless IPv6 routing is verified. The existing 80/443 router forwarding must reach Coin. After certificate verification, optional proxy mode must use Full (strict).

4. Coin administrator terminal, after reviewing this repository's configuration. Bootstrap only this subdomain for ACME:

```bash
sudo install -d -m 755 /var/www/mastercatalog-acme
sudo tee /etc/nginx/sites-available/mastercatalog.myforges.com >/dev/null <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name mastercatalog.myforges.com;
    location /.well-known/acme-challenge/ { root /var/www/mastercatalog-acme; }
    location / { return 503; }
}
EOF
sudo ln -s /etc/nginx/sites-available/mastercatalog.myforges.com /etc/nginx/sites-enabled/mastercatalog.myforges.com
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/mastercatalog-acme -d mastercatalog.myforges.com
# Review the staged file, then install it as data, never execute a user-writable root script:
cat /srv/ai-apps/mastercatalog/mastercatalog.nginx.conf
sudo install -o root -g root -m 644 /srv/ai-apps/mastercatalog/mastercatalog.nginx.conf /etc/nginx/sites-available/mastercatalog.myforges.com
sudo nginx -t && sudo systemctl reload nginx
sudo certbot renew --dry-run
```

If nginx -t fails, restore the bootstrap file before reload. Do not edit the existing myforges.com site. No coin-site helper installation is needed for this app.

5. Trigger once after data, Secrets and DNS/TLS are ready:

```bash
gh workflow run deploy.yml -R zxgtor/MasterCatalog --ref main
gh run list -R zxgtor/MasterCatalog --workflow deploy.yml --limit 1
curl -f https://mastercatalog.myforges.com/api/stats
```

## Coin paths and rollback

User service is staged/enabled but not started until a populated production DB exists. `loginctl show-user jason -p Linger` was confirmed yes. Releases: /srv/ai-apps/mastercatalog/releases/<commit>. Current is an atomic symlink; DB: /srv/ai-apps/mastercatalog/data/aareas.db. Deployment never runs crawlers, migrations or overwrites the DB. Concurrent GitHub runs are serialized and server deployment uses flock. A repeated deployment of an existing commit is rejected to avoid changing immutable releases. Use a new commit or administrator-reviewed rollback.

Manual rollback as jason on Coin (replace PREVIOUS_COMMIT with a retained release):

```bash
cd /srv/ai-apps/mastercatalog
test -d releases/PREVIOUS_COMMIT
ln -s "$PWD/releases/PREVIOUS_COMMIT" current.next
mv -Tf current.next current
systemctl --user restart mastercatalog
curl -f http://127.0.0.1:28765/api/stats
```

Nginx rollback removes only the new subdomain symlink, then `sudo nginx -t && sudo systemctl reload nginx`. Data rollback is separate; releases do not change its schema. Failed public HTTPS verification fails the workflow but retains a locally healthy release; fix DNS/TLS or roll back explicitly.
