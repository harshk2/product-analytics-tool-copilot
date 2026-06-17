# AI Product Analytics Copilot

## System Overview

An autonomous AI system that behaves like a senior product analyst, investigating business questions through multi-agent orchestration.

## Architecture

```
Client (Next.js) → API Gateway (FastAPI) → Orchestration (LangGraph) → Agents → Services → Data Stores
```

## Agent System

| Agent | Responsibility |
|-------|----------------|
| Intent Agent | Parse business questions into structured investigation plans |
| Metrics Agent | Identify relevant metrics and data sources |
| SQL Agent | Generate, validate, and execute safe SQL queries |
| Segmentation Agent | Segment users/customers by behavior patterns |
| Cohort Analysis Agent | Perform cohort-based retention/revenue analysis |
| Root Cause Agent | Generate and test hypotheses, rank by confidence |
| Visualization Agent | Create charts and visual representations |
| Executive Summary Agent | Synthesize findings into actionable recommendations |

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, Python 3.11+, Pydantic v2
- **AI**: LangGraph, LangChain, Claude API
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Workers**: Celery 5
- **Infrastructure**: Docker, Kubernetes, GitHub Actions

## Quick Start

```bash
# Development
docker-compose up -d
make dev

# Production
make build
make deploy
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc