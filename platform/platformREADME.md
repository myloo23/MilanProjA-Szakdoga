# Platform

Self-hosted CI platform for ProjectA.

## Components

| Service | Purpose |
|----------|---------|
| Gitea | Git server and CI coordinator |
| act_runner | Executes Gitea Actions workflows |
| Docker Registry | Stores built Docker images |

---

## Architecture

```
Developer
     │
     ▼
Git Push
     │
     ▼
Gitea
     │
     ▼
Runner
     │
     ▼
Docker Registry
```

---

## Start

```bash
docker compose \
  --env-file platform/.env \
  -f platform/compose.yaml \
  up -d
```

---

## Stop

```bash
docker compose \
  --env-file platform/.env \
  -f platform/compose.yaml \
  down
```

---

## Verify

```bash
curl http://localhost:3000/api/healthz
```

```bash
curl http://localhost:5001/v2/
```

---

## Data persistence

Data is stored in Docker named volumes:

- projecta-gitea-data
- projecta-runner-data
- projecta-registry-data

Containers can be recreated safely without losing data.