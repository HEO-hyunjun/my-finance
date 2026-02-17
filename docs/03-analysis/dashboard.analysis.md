# Analysis: Dashboard (통합 대시보드)

> **Feature**: dashboard
> **Analyzed**: 2026-02-13
> **Design Reference**: `docs/02-design/features/dashboard.design.md`
> **PDCA Phase**: Check (Gap Analysis)

---

## 1. 분석 개요

| 항목 | 값 |
|------|-----|
| 체크리스트 항목 수 | 19 |
| PASS | 19 |
| PARTIAL | 0 |
| FAIL | 0 |
| **Match Rate** | **100%** |

---

## 2. 체크리스트 항목별 판정

### Backend (BE-1 ~ BE-7) — 100%

| 항목 | 설명 | 판정 | 근거 |
|------|------|:----:|------|
| BE-1 | DashboardSummaryResponse Pydantic 스키마 | PASS | 9개 모델 완전 일치 |
| BE-2 | get_dashboard_summary() asyncio.gather 병렬 조회 | PASS | 7개 서비스 통합 gather (Design 대비 개선) |
| BE-3 | GET /api/v1/dashboard/summary 엔드포인트 | PASS | 라우터 등록 + JWT 인증 완료 |
| BE-4 | Redis 캐싱 (60초 TTL, 사용자별 키) | PASS | dashboard:{user_id} 키, graceful degradation |
| BE-5 | 만기 임박 예금/적금 필터링 (30일 이내) | PASS | _get_maturity_alerts() 완전 구현 |
| BE-6 | 이번 달 남은 결제 일정 필터링 | PASS | 고정비/할부 활성 상태 + 오늘 이후 필터 |
| BE-7 | 금 시세 실패 시 graceful degradation | PASS | try/except + None 반환 |

### Frontend (FE-1 ~ FE-12) — 100%

| 항목 | 설명 | 판정 | 근거 |
|------|------|:----:|------|
| FE-1 | useDashboardSummary TanStack Query hook | PASS | staleTime/refetchInterval 5분 일치 |
| FE-2 | TotalAssetWidget 총 자산/수익률/투자금 | PASS | 금액 포맷 + 양수/음수 색상 + Empty State |
| FE-3 | AssetDistChart Recharts 도넛 차트 | PASS | PieChart + 색상 8종 + 기타 합산(<3%) |
| FE-4 | BudgetStatusWidget 예산 진행률 바 | PASS | 3단계 색상 + 카테고리 상위 5개 + 고정비/할부 |
| FE-5 | RecentTxWidget 최근 5건 거래 | PASS | 유형별 색상 + 전체보기 링크 |
| FE-6 | MarketInfoWidget 환율 + 금 시세 | PASS | 한국 관행 색상 + null 숨김 |
| FE-7 | PaymentScheduleWidget 결제 일정 | PASS | 고정비/할부 배지 + 합계 |
| FE-8 | MaturityAlertWidget 만기 알림 (D-day) | PASS | D-day 3단계 색상 + 수령액 표시 |
| FE-9 | 반응형 그리드 레이아웃 | PASS | 1열/2열/3열 breakpoint 일치 |
| FE-10 | 로딩 스켈레톤 + 에러 상태 UI | PASS | animate-pulse + 재시도 버튼 |
| FE-11 | 각 위젯 Empty State | PASS | 6개 위젯 모두 구현 |
| FE-12 | Dashboard 타입 정의 | PASS | 9개 인터페이스 필드 완전 일치 |

---

## 3. 미세 차이 (Design 대비)

기능적 영향 없는 미세 차이 8건:

| # | 항목 | Design | 구현 | 판단 |
|---|------|--------|------|------|
| 1 | FE-1 | import: `@/shared/config` | `@/shared/api/client` | 실제 프로젝트 구조 반영 |
| 2 | FE-1 | API: `/api/v1/...` | `/v1/...` | baseURL에 `/api` 포함 |
| 3 | FE-3 | innerRadius=60 | innerRadius=50 | 시각적 미세 조정 |
| 4 | FE-7 | bg-blue-100 | bg-blue-50 | 톤 미세 조정 |
| 5 | FE-10 | Early return | 조건부 렌더링 | refetch 전달을 위한 개선 |
| 6 | BE-2 | BudgetService 클래스 메서드 | 모듈 함수 | 실제 서비스 구현에 맞춤 |
| 7 | BE-2 | 5개 gather + 2개 순차 | 7개 gather 통합 | 성능 개선 |
| 8 | FE lib | formatKRW 만 단위 | 억 단위 추가 지원 | 기능 확장 |

---

## 4. 결론

- **Match Rate: 100%** — 19개 항목 모두 PASS
- Design 문서와 구현 코드가 완전히 일치하며, 일부 미세 차이는 의도적 개선
- **Act(개선) 단계 불필요** → Report 단계로 진행 가능
