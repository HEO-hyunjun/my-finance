---
name: myfinance-api
description: |
  MyFinance 통합 자산 관리 앱의 API 레퍼런스 스킬.
  계좌/거래/예산/투자/시장 데이터에 접근하여 조회, 생성, 수정, 삭제를 수행한다.

  다음 상황에서 트리거된다:
  - MyFinance 데이터를 조회하거나 수정해야 할 때
  - 자산, 거래, 예산, 투자 관련 작업을 요청받았을 때
  - "내 자산 보여줘", "거래 추가해줘", "예산 현황" 등의 요청
---

# MyFinance API

MyFinance 앱의 핵심 데이터에 접근하는 REST API 레퍼런스. 계좌, 거래, 예산, 투자, 시장 데이터를 조회/생성/수정/삭제할 수 있다.

## 환경 설정

이 스킬 폴더의 `.env` 파일에서 환경변수를 로드한다:

```bash
source "$(dirname "$0")/.env" 2>/dev/null || source .claude/skills/myfinance-api/.env
```

### .env 파일이 없거나 값이 비어있는 경우

**MYFINANCE_API_KEY 발급:**
1. 웹 브라우저에서 MyFinance에 로그인
2. 설정 페이지 → 하단 "Personal API Key" 섹션
3. "키 발급하기" 클릭 → `myf_...` 형식의 키를 복사 (이 화면에서만 원본 확인 가능)
4. 키를 잊은 경우: 설정 → Personal API Key → "키 보기" → 비밀번호 입력

**MYFINANCE_BASE_URL 확인:**
1. Docker Compose 확인: `grep -A2 'ports:' docker-compose.yml`
   - Frontend(Nginx) 포트: 3000 → `http://localhost:3000`
   - Backend 직접 접근: 8000 → `http://localhost:8000`
2. Nginx 설정 확인: `frontend/nginx.conf`에서 `/api/` 프록시 확인
3. 위 방법으로 안 되면 사용자에게 질문

Base URL에 `/api`를 포함하지 않는다. 경로는 항상 `/api/v1/...`으로 시작한다.

## 공통 사항

### 인증
모든 요청에 `X-API-Key` 헤더를 포함한다:
```bash
curl -H "X-API-Key: ${MYFINANCE_API_KEY}" "${MYFINANCE_BASE_URL}/api/v1/..."
```

### 에러 코드
| 코드 | 의미 |
|------|------|
| 400 | 잘못된 요청 (필수 필드 누락, 유효성 검사 실패) |
| 401 | 인증 실패 (API 키 없음/만료) |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복 데이터) |

### 페이지네이션
Entries 목록만 페이지네이션 지원: `?page=1&per_page=20` (최대 100)

### 데이터 타입
- ID: UUID 문자열 (예: `"550e8400-e29b-41d4-a716-446655440000"`)
- 금액: Decimal 문자열 또는 숫자
- 날짜: ISO 8601 (`"2026-04-11"`, `"2026-04-11T09:30:00"`)

## 안전 규칙

- **DELETE 요청**: 반드시 사용자에게 확인 후 실행
- **금액 관련 POST/PATCH**: 실행 전 금액과 대상을 사용자에게 확인 권장
- **이월 실행** (`POST /carryover/execute`): 되돌릴 수 없으므로 반드시 확인
- **잔액 조정** (`POST /accounts/{id}/adjust`): 기존 잔액이 덮어써지므로 확인

## 도메인 라우팅 테이블

| 하고 싶은 일 | 읽을 파일 |
|-------------|----------|
| 계좌 조회/생성/수정/삭제, 거래 내역 관리, 이체, 매매, 카테고리 관리 | [references/accounts.md](references/accounts.md) |
| 예산 개요, 카테고리별 배분, 예산 분석, 이월 설정/실행 | [references/budget.md](references/budget.md) |
| 정기거래(자동이체) 조회/생성/수정/삭제/토글 | [references/schedules.md](references/schedules.md) |
| 자산 추이, 스냅샷, 목표 자산, 리밸런싱, 시세/환율 조회 | [references/investment.md](references/investment.md) |
| 대시보드 요약, AI 인사이트, 캘린더 이벤트 | [references/overview.md](references/overview.md) |
| 투자 프롬프트(투자 전략) 조회 | [references/settings.md](references/settings.md) |
