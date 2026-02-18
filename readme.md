# MyFinance

통합 자산 관리 웹 애플리케이션. 자산, 예산, 지출, 수입을 한곳에서 관리하고 AI 기반 재무 상담까지 제공합니다.

## 주요 기능

- **자산 관리** - 주식(국내/미국), 금, 현금 등 다양한 자산 통합 관리. 실시간 시세 연동 및 포트폴리오 분석
- **예산 관리** - 월별 예산 설정, 카테고리별 배분, 고정지출/할부 관리, 이월 설정
- **지출/수입 추적** - 거래 내역 필터링, 카테고리 분석, 캘린더 뷰
- **대시보드** - 일일 가용 예산, 자산 추이, 목표 달성률 등 9개 위젯으로 재무 현황 한눈에 파악
- **AI 재무 상담** - LangGraph 기반 Deep Agent가 시세 조회, 뉴스 분석, 맞춤 투자 조언 제공
- **뉴스 & 시장** - 금융 뉴스 수집, LLM 요약/감성 분석, 시장 트렌드 검색
- **목표 & 리밸런싱** - 자산 목표 설정, 포트폴리오 타겟 비중 관리, 리밸런싱 알림
- **설정** - 테마, API 키 관리(암호화 저장), LLM 모델/프롬프트 커스터마이징

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS v4 |
| UI | Radix UI, Lucide Icons, Recharts, dnd-kit |
| 상태 관리 | Zustand (client), TanStack Query (server) |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | MySQL 8.0, Redis 7 |
| Auth | JWT (python-jose), bcrypt |
| AI/LLM | LangGraph Deep Agent, LiteLLM (멀티 프로바이더) |
| Task Queue | Celery (worker + beat) |
| 검색/시세 | SerpAPI / Firecrawl (선택), yfinance |
| Infra | Docker Compose, PWA (vite-plugin-pwa) |

## 아키텍처

```
Frontend (React + Vite)           Backend (FastAPI)
┌──────────────────────┐          ┌──────────────────────────┐
│  FSD Architecture    │          │  API (v1)                │
│  ├─ app/             │   REST   │  ├─ endpoints/ (18개)    │
│  ├─ pages/ (10개)    │◄────────►│  ├─ services/ (20개)     │
│  ├─ widgets/         │   JSON   │  ├─ models/              │
│  ├─ features/ (11개) │          │  └─ schemas/             │
│  ├─ entities/        │          ├──────────────────────────┤
│  └─ shared/          │   SSE    │  Deep Agent (LangGraph)  │
│                      │◄─────────│  ├─ Researcher           │
└──────────────────────┘          │  ├─ Fetcher (SerpAPI)    │
                                  │  ├─ Analyzer             │
┌──────────┐  ┌──────────┐       │  └─ Advisor              │
│  MySQL   │  │  Redis   │       ├──────────────────────────┤
│  8.0     │◄─┤  7       │◄─────►│  Celery Worker / Beat    │
└──────────┘  └──────────┘       └──────────────────────────┘
```

## 시작하기

### 사전 요구사항

- Docker & Docker Compose
- Node.js 20+ (프론트엔드 로컬 개발 시)
- Python 3.11+ (백엔드 로컬 개발 시)

### Docker Compose로 실행

```bash
# 1. 저장소 클론
git clone https://github.com/HEO-hyunjun/my-finance.git
cd my-finance

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에서 JWT_SECRET_KEY, API 키 등을 수정하세요

# 3. 전체 서비스 실행
docker compose up -d

# 4. DB 마이그레이션
docker compose run --rm migrate
```

실행 후 접속:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API 문서 (Swagger): http://localhost:8000/docs

### 로컬 개발

```bash
# 인프라만 Docker로 실행
docker compose up -d db redis

# 백엔드
cd backend
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev
```

## 환경 변수

주요 환경 변수 목록입니다. 전체 목록은 [`.env.example`](.env.example)을 참고하세요.

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `JWT_SECRET_KEY` | JWT 서명 키 (반드시 변경) | `change-me` |
| `DATABASE_URL` | MySQL 접속 URL | `mysql+asyncmy://...@localhost:3307/myfinance` |
| `REDIS_URL` | Redis 접속 URL | `redis://localhost:6379/0` |
| `SEARCH_PROVIDER` | 검색 프로바이더 | `serpapi` |
| `SERPAPI_KEY` | SerpAPI 키 (뉴스/검색) | - |
| `LITELLM_MODEL` | 기본 LLM 모델 | `gpt-4o-mini` |
| `CHATBOT_MODEL` | 챗봇 전용 모델 | `gpt-5.2` |
| `OPENAI_API_KEY` | OpenAI API 키 | - |

## 프로젝트 구조

```
MyFinance/
├── frontend/                    # React + Vite (FSD 아키텍처)
│   └── src/
│       ├── app/                 # 라우팅, 프로바이더, 글로벌 스타일
│       ├── pages/               # 페이지 (10개)
│       │   ├── dashboard/       #   대시보드 (9개 위젯)
│       │   ├── assets/          #   자산 관리
│       │   ├── budget/          #   예산 관리
│       │   ├── expenses/        #   지출 내역
│       │   ├── transactions/    #   거래 내역
│       │   ├── calendar/        #   캘린더
│       │   ├── news/            #   뉴스
│       │   ├── chatbot/         #   AI 상담
│       │   ├── settings/        #   설정
│       │   └── auth/            #   로그인/회원가입
│       ├── widgets/             # 레이아웃 (Header, Sidebar)
│       ├── features/            # 비즈니스 로직 (11개 도메인)
│       ├── entities/            # 도메인 엔티티
│       └── shared/              # 공통 유틸, 타입, UI 컴포넌트
├── backend/                     # FastAPI (Python)
│   └── app/
│       ├── api/v1/endpoints/    # REST API 엔드포인트
│       ├── services/            # 비즈니스 로직
│       │   └── agents/          # Deep Agent (LangGraph)
│       ├── models/              # SQLAlchemy 모델
│       ├── schemas/             # Pydantic 스키마
│       ├── core/                # 설정, DB, 보안, Celery
│       └── tasks/               # Celery 비동기 작업
├── docker-compose.yml           # 서비스 오케스트레이션
└── .env.example                 # 환경 변수 템플릿
```

## API

모든 API는 `/api/v1` 접두사를 사용합니다.

| 도메인 | 엔드포인트 | 설명 |
|--------|-----------|------|
| 인증 | `/auth` | 회원가입, 로그인, 토큰 갱신 |
| 사용자 | `/users` | 프로필 조회/수정 |
| 자산 | `/assets` | 자산 CRUD, 요약, 시세 |
| 거래 | `/transactions` | 매매 거래 기록 |
| 예산 | `/budget` | 예산 설정, 카테고리 배분 |
| 지출 | `/expenses` | 지출 내역 CRUD |
| 고정지출 | `/fixed-expenses` | 고정 지출 관리 |
| 할부 | `/installments` | 할부 내역 관리 |
| 이월 | `/carryover` | 예산 이월 설정 |
| 수입 | `/incomes` | 수입 내역 관리 |
| 포트폴리오 | `/portfolio` | 목표, 리밸런싱 |
| 뉴스 | `/news` | 뉴스 조회, LLM 분석 |
| 시장 | `/market` | 트렌드, 종목 검색 |
| 챗봇 | `/chatbot` | AI 상담 (SSE 스트리밍) |
| 대시보드 | `/dashboard` | 위젯 데이터 |
| 캘린더 | `/calendar` | 일별 지출 요약 |
| 설정 | `/settings` | 테마, API 키, LLM |

자세한 API 문서는 서버 실행 후 http://localhost:8000/docs 에서 확인할 수 있습니다.

## Deep Agent (AI 시스템)

LangGraph 기반 멀티 에이전트 시스템으로, 4개의 서브에이전트가 협력하여 재무 상담을 수행합니다.

```
사용자 질문
    │
    ▼
┌─────────────┐     ┌─────────────┐
│ Researcher  │────►│   Fetcher   │
│ 질문 분석   │     │ 실시간 데이터│
│ 컨텍스트 수집│     │ 시세/뉴스   │
└─────────────┘     └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Analyzer   │
                    │ 데이터 분석  │
                    │ 트렌드 파악  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Advisor   │
                    │ 맞춤 조언   │
                    │ SSE 스트리밍 │
                    └─────────────┘
```

- **Researcher**: 사용자 질문을 분석하고 필요한 컨텍스트(보유 자산, 예산 현황)를 수집
- **Fetcher**: SerpAPI를 통해 실시간 시세, 뉴스, 환율 데이터를 조회
- **Analyzer**: 수집된 데이터를 분석하여 트렌드와 인사이트를 도출
- **Advisor**: 분석 결과를 바탕으로 사용자에게 맞춤 투자 조언을 SSE 스트리밍으로 제공

LiteLLM을 통해 OpenAI, Anthropic, Google, Ollama 등 다양한 LLM 프로바이더를 지원합니다.

## 라이선스

MIT
