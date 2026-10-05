# Frontend

One page over the backend's notes CRUD: Vite + React + TypeScript, built into
static files and served by unprivileged nginx on port 8080. Every API call goes
to the relative path `/api/…` (`src/api.ts`), so the browser talks to a single
origin and no CORS configuration exists.

| Where | Who forwards `/api` | To |
|---|---|---|
| Development (`npm run dev`) | Vite dev server (`vite.config.ts`) | `http://localhost:8000`, prefix stripped |
| Cluster | nginx (`nginx.conf`) | the `backend` Service, prefix stripped |

```bash
npm ci
npm run dev        # with the backend running on :8000
npm run lint
npm run build      # tsc -b && vite build → dist/
```

The image (`Dockerfile`) is two stages: `node:22-alpine` builds, the
`nginx-unprivileged` runtime ships only `dist/` and `nginx.conf`. Both base
images are digest-pinned; bump them only with `scripts/pin-base-images.sh`.
In the pipeline the Dockerfile is linted by hadolint and the image is scanned
by Trivy, like the backend's. Why Vite and not Next.js: decision D6 in
`szakdolgozat/01-megvalositasi-terv.md`.
