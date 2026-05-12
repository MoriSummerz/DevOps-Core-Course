# edge-api — Lab 17

Cloudflare Workers serverless HTTP API for **DevOps Core Course Lab 17**.

See [WORKERS.md](./WORKERS.md) for the full submission write-up
(deployment summary, evidence, K8s vs Workers comparison, reflection).

---

## Project layout

```
edge-api/
├── src/
│   └── index.ts          # Worker source (all routes)
├── wrangler.jsonc        # Worker configuration (vars + KV binding)
├── tsconfig.json
├── package.json
├── .dev.vars.example     # Local secret template (copy → .dev.vars)
├── .gitignore
├── screenshots/          # Dashboard / logs / metrics screenshots
└── WORKERS.md            # Lab 17 submission document
```

---

## Routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | App metadata + endpoint list |
| `GET` | `/health` | `{"status":"ok"}` liveness check |
| `GET` | `/edge` | `request.cf` edge metadata (colo, country, asn, tls, …) |
| `GET` | `/counter` | KV-persisted visit counter (`SETTINGS` binding) |
| `GET` | `/config` | Reflects vars and reports secret presence (masked) |

---

## Local development

```bash
cd edge-api
npm install
cp .dev.vars.example .dev.vars       # set local secret values
npx wrangler dev                     # http://localhost:8787
```

Type-check and dry-build:

```bash
npx tsc --noEmit
npx wrangler deploy --dry-run --outdir=.wrangler/dry
```

---

## Deployment runbook

Steps the maintainer must run once (they need Cloudflare account access
and a browser session for OAuth):

```bash
cd edge-api

# 1. Authenticate Wrangler against your Cloudflare account
npx wrangler login
npx wrangler whoami

# 2. Create the KV namespace and copy the returned id into wrangler.jsonc
#    Replace the "REPLACE_WITH_KV_NAMESPACE_ID" placeholder.
npx wrangler kv namespace create SETTINGS

# 3. Push secrets (run each command; it will prompt for the value)
npx wrangler secret put API_TOKEN
npx wrangler secret put ADMIN_EMAIL

# 4. Deploy
npx wrangler deploy

# 5. Verify the public URL printed by wrangler
curl -s https://edge-api.<your-subdomain>.workers.dev/health   | jq
curl -s https://edge-api.<your-subdomain>.workers.dev/         | jq
curl -s https://edge-api.<your-subdomain>.workers.dev/edge     | jq
curl -s https://edge-api.<your-subdomain>.workers.dev/counter  | jq
curl -s https://edge-api.<your-subdomain>.workers.dev/config   | jq

# 6. Tail logs from a second terminal (run while curling the URL)
npx wrangler tail

# 7. Deploy a second version (any small edit — e.g. bump VERSION in src/index.ts)
#    then redeploy to populate deployment history.
npx wrangler deploy

# 8. Inspect history and demonstrate rollback
npx wrangler deployments list
npx wrangler rollback <previous-version-id>
```

After step 8, take the following screenshots and save them to
`edge-api/screenshots/` with these exact filenames so they render inline in
`WORKERS.md`:

| Filename | What to capture |
|---|---|
| `lab17-dashboard.png` | Workers & Pages → `edge-api` overview page |
| `lab17-edge-response.png` | Browser or terminal showing `/edge` JSON output |
| `lab17-logs.png` | Terminal output of `wrangler tail` while hitting `/edge` |
| `lab17-metrics.png` | `edge-api → Metrics` tab in the dashboard |

Then update `WORKERS.md` section **2.2** with your actual `/edge`
response, section **2.6** with the real version IDs from
`wrangler deployments list`, and the `<your-subdomain>` placeholders
throughout.
