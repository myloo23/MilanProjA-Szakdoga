# Platform Architecture

## Components

- Flask API
- Docker
- Gitea
- Gitea Actions Runner
- Docker Registry

## Communication

Developer
↓
Git Push
↓
Gitea
↓
Runner
↓
Docker Engine
↓
Registry

## Docker Network

projecta-platform

Services communicate using Docker DNS.

Examples:

gitea:3000

registry:5000

Never use localhost between containers.

## Persistent Data

projecta-gitea-data

projecta-runner-data

projecta-registry-data