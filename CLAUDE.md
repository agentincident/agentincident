# CLAUDE.md

## Deployment

After making changes to the web app, always deploy. See `platform/DEPLOY.md` for full details.

### Deploy web (Cloudflare Pages)

```sh
cd platform
CLOUDFLARE_ACCOUNT_ID=5458d33f33adbb228600a2a3c8bfa422 pnpm deploy:web
```

This builds the Vite SPA and uploads `apps/web/dist/` to Cloudflare Pages (`agentincident-platform.pages.dev`).

### Deploy API (Cloudflare Workers)

```sh
cd platform
CLOUDFLARE_ACCOUNT_ID=5458d33f33adbb228600a2a3c8bfa422 pnpm deploy:api
```

### Deploy everything

```sh
cd platform
CLOUDFLARE_ACCOUNT_ID=5458d33f33adbb228600a2a3c8bfa422 pnpm deploy
```
