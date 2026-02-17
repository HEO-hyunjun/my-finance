# MyFinance - 통합 자산 관리 앱

## Project Level: Dynamic

## Tech Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS v4
- **Frontend Architecture**: FSD (Feature-Sliced Design)
- **State Management**: Zustand (client) + TanStack Query (server)
- **Backend**: FastAPI (Python) + SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL + Redis
- **Auth**: JWT (python-jose)
- **External APIs**: SerpAPI (시세, 뉴스, 검색)
- **AI**: deepagents (LangChain + LangGraph) + LiteLLM
- **Infrastructure**: Docker Compose

## Project Structure
```
MyFinance/
├── frontend/          # React + Vite (FSD Architecture)
│   └── src/
│       ├── app/       # App-level: providers, routes, styles
│       ├── pages/     # Page components
│       ├── widgets/   # Complex UI blocks
│       ├── features/  # Business logic features
│       ├── entities/  # Domain entities
│       └── shared/    # Shared utilities, types, UI
├── backend/           # FastAPI Python
│   └── app/
│       ├── api/       # API endpoints
│       ├── core/      # Config, DB, security
│       ├── models/    # SQLAlchemy models
│       ├── schemas/   # Pydantic schemas
│       ├── services/  # Business logic
│       └── tasks/     # Celery tasks
├── docs/              # PDCA documents
└── docker-compose.yml
```

## Conventions
- Frontend: TypeScript strict mode, FSD layer imports (shared -> entities -> features -> widgets -> pages -> app)
- Backend: async/await, Pydantic v2 schemas, SQLAlchemy 2.0 async style
- API: RESTful, versioned (/api/v1/...)
- Naming: camelCase (TS), snake_case (Python)

## Commands
- Frontend dev: `cd frontend && npm run dev`
- Backend dev: `cd backend && uvicorn app.main:app --reload`
- Docker: `docker compose up -d`
