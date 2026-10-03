# MasterCatalog Ã¢â€ â€™ Coin

main push and manual workflow_dispatch run build/smoke tests Ã¢â€ â€™ Tailscale Ã¢â€ â€™ SSH Ã¢â€ â€™ release Ã¢â€ â€™ HTTPS verification. Only main deploys. Runtime uses Python 3 standard library, port 28765. Database stays outside releases. No root deployment script or passwordless sudo is required. Existing AppGallery is untouched.

## One-time user setup

1. Provide the existing populated aareas.db (do not commit it). The repository cannot recreate products: import_sqlite.py requires ignored master_products.json. Transfer the database while its writer is stopped, or use SQLite backup; do not copy a live WAL database alone:

   scp /path/to/aareas.db coin:/srv/ai-apps/mastercatalog/data/aareas.db

2. GitHub repository Settings Ã¢â€ â€™ Secrets and variables Ã¢â€ â€™ Actions (repository secrets, no paid environment required):
   - TS_OAUTH_CLIENT_ID / TS_OAUTH_SECRET: Tailscale OAuth client, auth_keys write scope, tag:github-deploy. Allow this tag to reach 100.80.142.52:22 only in the tailnet policy.
   - COIN_SSH_KEY: a dedicated Ed25519 deployment private key. Add its public key to Coin jason ~/.ssh/authorized_keys with `restrict` prefix. Use `gh secret set COIN_SSH_KEY -R zxgtor/MasterCatalog < private-key-file` locally; never paste the key into chat. It grants access as jason; a dedicated restricted account would require additional administrator provisioning.
   - COIN_KNOWN_HOSTS: pinned Coin Ed25519 host key (already populated by setup after authenticated SSH inspection). Never use StrictHostKeyChecking=no.

3. DNS/HTTPS completed on Coin: proxied wildcard CNAME `* â†’ myforges.com` resolves MasterCatalog. A dedicated Let's Encrypt certificate for mastercatalog.myforges.com was issued (expires 2027-01-01), and /etc/nginx/conf.d/mastercatalog.conf serves the application on port 28765. Until the backend is deployed, HTTP redirects to HTTPS and HTTPS returns 503 with no-store. ACME HTTP challenge remains accessible. Do not install a duplicate sites-enabled configuration.

4. Unknown domains no longer fall through to Gallery: /etc/nginx/conf.d/coin-unknown-hosts.conf returns HTTP 404 and rejects unknown TLS handshakes. Existing Gallery was verified HTTP 200. Certbot scheduled renewal and an Nginx deploy reload hook are present. Cloudflare's dashboard SSL mode could not be inspected; select Full (strict). No Flexible workaround was used.

A reusable origin certificate for *.myforges.com is still separate work: current origin certificates cover myforges.com and mastercatalog.myforges.com individually. Wildcard issuance requires DNS-01, either a Cloudflare token limited to this zone's DNS edits plus certbot DNS plugin, or manual _acme-challenge TXT records (manual renewal). Do not send credentials in chat. Public Cloudflare edge TLS is separate from the origin certificate.

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

Nginx rollback removes only /etc/nginx/conf.d/mastercatalog.conf, then `sudo nginx -t && sudo systemctl reload nginx`. Data rollback is separate; releases do not change its schema. Failed public HTTPS verification fails the workflow but retains a locally healthy release; fix DNS/TLS or roll back explicitly.
