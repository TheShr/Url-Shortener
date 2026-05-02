# Distributed URL Shortener

A production-grade URL shortening service engineered for high throughput, horizontal scalability, and fault tolerance. Built with a fully async backend, multi-layer caching, and a real-time analytics pipeline — designed to handle over 10,000 requests per second with sub-100ms redirect latency at the p99.

Live demo: [url-shortener-frontend-hncn5herv.vercel.app](https://url-shortener-frontend-hncn5herv.vercel.app/)

---

## What This Demonstrates

This project goes beyond a typical CRUD application. It addresses real distributed systems problems that appear at scale:

- **Cache stampede prevention** via negative caching and cache-warming on first DB hit
- **Coordination-free ID generation** using a Snowflake-inspired base62 algorithm — no DB round-trips to generate unique short codes
- **Non-blocking analytics** using a Redis queue with a background worker that batch-inserts click events every 2 seconds, keeping the hot path free of write contention
- **Sliding window rate limiting** via Redis sorted sets — accurate under burst traffic with no boundary-reset artifacts
- **Stateless horizontal scaling** — any number of FastAPI workers can be added without code changes; all shared state is externalized to Redis and PostgreSQL

---

## Architecture

```
Client (Next.js / Vercel)
        |  HTTPS
        v
  Rate Limiter  <-- Redis sliding window
        |
  Load Balancer (round-robin)
     |       |
 API #1   API #2  ...   <-- Stateless FastAPI workers
     |       |
  +----------+----------+
  |                     |
Redis Cache         PostgreSQL
(hot URLs,          (primary + read replicas)
 rate limits,            |
 click queue)       Shard router (hash(shortCode) mod N)
        |
  Background Worker
  (batch-writes analytics from Redis queue to PostgreSQL)
```

### Redirect Request Flow (Hot Path)

1. `GET /{code}` arrives at a stateless FastAPI worker
2. Redis lookup on `url:{code}` — cache hit returns a 301 redirect in ~5ms
3. On cache miss, the shard router selects the correct PostgreSQL shard, fetches the record, warms the cache, and returns 301
4. A click event is pushed to a Redis list — non-blocking, zero added latency
5. Background worker drains the queue in 2-second batches into PostgreSQL

### Latency Profile

| Layer | Technique | Latency |
|-------|-----------|---------|
| Cache hit | Redis in-memory lookup | ~3–8ms |
| Cache miss | Partial index on `short_code` (active rows only) | ~20–40ms |
| Analytics write | Async queue, batch insert | 0ms (non-blocking) |

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Backend | FastAPI + asyncio | Native async I/O, automatic OpenAPI docs, Pydantic validation |
| Database | PostgreSQL + asyncpg | ACID guarantees, partial indexes, range partitioning |
| Cache | Redis | Sub-millisecond reads, TTL support, atomic sorted-set operations |
| Frontend | Next.js 14 | App Router, SSR, TypeScript, Vercel CDN |
| ID Generation | Snowflake-inspired base62 | Globally unique IDs without DB coordination |
| Rate Limiting | Redis sorted sets | Sliding window — accurate burst control |

---

## Performance Targets

| Metric | Target | How |
|--------|--------|-----|
| p50 redirect latency | < 10ms | Redis cache hit |
| p99 redirect latency | < 100ms | Partial index on active URLs |
| Throughput | > 10,000 req/s | Stateless workers + Redis |
| Availability | 99.9% | Worker redundancy + PG read replicas |

---

## Scaling Design

**Horizontal scaling** — Workers are fully stateless. Scaling out requires no code changes. Each worker is assigned a unique `MACHINE_ID` (0–1023) to partition the Snowflake ID space and prevent collisions across instances.

**Database sharding** — Short codes are routed to PostgreSQL shards via `hash(short_code) % N`. PgBouncer sits in front of each shard for connection pooling.

**Caching policy:**
- Hot URLs cached with a 1-hour TTL (Pareto principle covers ~80% of traffic)
- 404 results negatively cached for 60 seconds to protect against DB hammering
- Redis eviction policy set to `allkeys-lru`

**Read replicas** — Analytics and redirect GETs are routed to PG read replicas via SQLAlchemy multi-engine configuration, reserving the primary for writes.

---

## Database Schema Highlights

```sql
-- Partial index on active URLs only — keeps the index small and lookups fast
CREATE INDEX ix_urls_short_code_active
  ON urls (short_code)
  WHERE is_active = true;

-- Composite index for expiration sweep jobs
CREATE INDEX ix_urls_expires_at_is_active
  ON urls (expires_at, is_active);

-- Time-series index for analytics queries
CREATE INDEX ix_clicks_url_id_clicked_at
  ON clicks (url_id, clicked_at);
```

---

## API Reference

### Shorten a URL

```
POST /api/v1/shorten
```

```json
{
  "url": "https://very-long-url.com/path",
  "custom_alias": "my-link",
  "expiry_days": 30
}
```

Response:

```json
{
  "short_code": "abc1234",
  "short_url": "https://yourdomain.com/abc1234",
  "original_url": "https://...",
  "expires_at": "2025-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Redirect

```
GET /api/v1/{short_code}
```

Returns `301 Redirect`. Cache-hit path averages ~5ms.

### Analytics

```
GET /api/v1/analytics/{short_code}
```

Returns click time-series, top referrers, and recent click events.

### Health Check

```
GET /api/v1/health
```

Liveness probe — verifies PostgreSQL and Redis connectivity.

---

## Local Development

**Prerequisites:** Docker, Docker Compose, Python 3.12+, Node.js 20+

```bash
git clone https://github.com/yourname/url-shortener
cd url-shortener

cp backend/.env.example backend/.env

docker compose up -d

docker compose exec api alembic upgrade head

cd frontend && npm install && npm run dev
```

API docs available at `http://localhost:8000/docs`  
Frontend at `http://localhost:3000`

**Run backend tests:**

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v --asyncio-mode=auto --cov=app
```

---

## Project Structure

```
url-shortener/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # Route handlers
│   │   ├── core/               # Config, logging
│   │   ├── db/                 # Session management, Redis client
│   │   ├── middleware/         # Rate limiting
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic, background worker
│   │   └── utils/              # Base62 encoder, Snowflake ID generator
│   ├── alembic/                # Database migrations
│   ├── tests/
│   ├── main.py                 # FastAPI application factory
│   ├── render.yaml             # Render deployment config
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # URL shortener form
│   │   │   └── analytics/      # Analytics dashboard
│   │   ├── lib/api.ts          # Typed API client
│   │   └── types/              # TypeScript interfaces
│   └── package.json
└── docker-compose.yml
```
