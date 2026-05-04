# Mini Railway

A self-hosted deployment platform. Push code to GitHub → it automatically deploys to your server via SSH. No clicking. No manual work.

Running on a OnePlus 5T (2017) flashed with postmarketOS and a custom compiled kernel. 8 cores, 6GB RAM, ₹0 cost.

---

## How it works

```
GitHub push
  → POST /webhooks/github
  → HMAC-SHA256 signature verified (is this really GitHub?)
  → Event saved to PostgreSQL
  → Deploy job queued in Redis via arq
  → Worker picks up job
  → SSHes into target server
  → Runs docker compose pull && up
  → Streams each log line to database in real time
  → Deployment marked success or failed
  → Logs viewable via SSE stream
```

---

## Stack

| Tool | Why |
|------|-----|
| **FastAPI** | Async, fast, minimal boilerplate |
| **asyncpg** | Raw async PostgreSQL driver. No ORM magic. |
| **arq** | Async job queue built on Redis. Fits FastAPI naturally. |
| **asyncssh** | SSH into remote server programmatically |
| **Redis** | Job queue backend |
| **PostgreSQL** | Stores events, deployments, logs |
| **Docker Compose** | Runs everything |
| **uv** | Modern Python package manager |
| **SSE** | Streams deploy logs to client in real time |

Chose asyncpg over psycopg because the stack is fully async. Chose arq over Celery for the same reason. Raw SQL over ORM to understand what's actually happening.

---

## Project structure

```
mini-railway/
├── docker-compose.yml
├── .env
├── app/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── main.py
│   ├── database.py
│   ├── worker.py
│   ├── deployer.py
│   └── routers/
│       ├── webhooks.py
│       └── deployments.py
└── postgres/
    └── init.sql
```

---

## Setup

**Requirements:** Docker, Docker Compose, uv

```bash
# Clone
git clone https://github.com/Kuntal6002/mini-railway
cd mini-railway

# Configure
cp .env.example .env
# Edit .env with your database password and GitHub webhook secret

# Run
docker compose up --build -d

# Seed a project
docker compose exec db psql -U webhook -d webhooks -c \
"INSERT INTO projects (repo, deploy_host, deploy_user, deploy_workdir) \
VALUES ('your-username/your-repo', 'your-server-ip', 'your-user', '/srv/your-app');"
```

**Test it:**

```bash
curl -X POST http://localhost:8000/webhooks/github \
  -H "X-GitHub-Event: push" \
  -H "Content-Type: application/json" \
  -d '{"repository":{"full_name":"your-username/your-repo"},"sender":{"login":"you"}}'
```

**Watch it deploy:**

```bash
curl http://localhost:8000/deployments/1
curl http://localhost:8000/deployments/1/logs
```

---

## API

| Endpoint | Description |
|----------|-------------|
| `POST /webhooks/github` | Receive GitHub webhook |
| `GET /deployments` | List all deployments |
| `GET /deployments/{id}` | Get deployment status |
| `GET /deployments/{id}/logs` | Get deployment logs |
| `GET /deployments/{id}/stream` | Stream logs via SSE |
| `GET /health` | Health check |

---

## What I learned building this

- Async Python properly — asyncpg, asyncssh, asyncio event loop
- Connection pooling and why it matters at scale
- Job queues and background workers
- SSH automation programmatically
- HMAC signature verification for webhook security
- Raw SQL with asyncpg — no ORM, understood exactly what queries run
- Docker networking and healthchecks
- Streaming responses with SSE

---

## What's next

- [ ] Prometheus + Grafana monitoring
- [ ] Kubernetes deployment
- [ ] Web dashboard frontend
- [ ] Multi-user support with auth
- [ ] Telegram bot integration
- [ ] RAG for querying deployment history
- [ ] Custom domain and public access

---

## The server

This runs on a OnePlus 5T I flashed with postmarketOS. Had to manually enable 40+ kernel configs and debug iptables vs nftables conflicts at 2am to get Docker networking working. Accessible via Tailscale from anywhere.

Full writeup coming soon.

---

Built by [Kuntal](https://github.com/Kuntal6002) · 3rd year BTech CSE
