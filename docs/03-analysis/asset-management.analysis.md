# Gap Analysis: Asset Management (자산 관리)

> **Feature**: asset-management
> **Analyzed**: 2026-02-05
> **Design Reference**: `docs/02-design/features/asset-management.design.md`
> **PDCA Phase**: Check

---

## 1. 체크리스트 결과

| ID | 항목 | 상태 | 상세 |
|:---|:-----|:----:|:-----|
| **BE-1** | User 모델 + Alembic 마이그레이션 | PARTIAL | User 모델 100% 일치. Alembic env.py async 설정 완료. 단, `alembic/versions/`에 마이그레이션 파일 0개 (001~003 미생성). |
| **BE-2** | Asset CRUD API 4개 | PASS | 5개 엔드포인트 모두 구현 (GET list, POST 201, GET /summary, GET /{id}, DELETE 204) |
| **BE-3** | Transaction CRUD API 4개 | PASS | GET list(필터+페이징), POST 201, PUT, DELETE 204 모두 구현 |
| **BE-4** | Asset Summary API | PASS | GET /assets/summary — 유형별 breakdown, holdings, Market Service 호출 포함 |
| **BE-5** | Market Price API + Redis 캐싱 | PASS | SerpAPI + Redis TTL 300초, EXCHANGE_MAP, mock fallback 모두 구현 |
| **BE-6** | Exchange Rate API + Redis 캐싱 | PASS | GET /market/exchange-rate, 캐시 키 `market:exchange_rate:USDKRW` |
| **BE-7** | 자산 계산 로직 정확성 | PASS | buy/sell 분리, 평균단가(KRW 기준), 해외 환율 반영, 현금 특수 처리 |
| **BE-8** | 매도 시 보유량 초과 방지 | PASS | `_get_available_quantity()` 호출, create/update 모두 검증 |
| **BE-9** | JWT 인증 미들웨어 | PASS | HTTPBearer, decode_token, type=access 체크, user DB 조회 |
| **FE-1** | 자산 요약 카드 렌더링 | PASS | 총자산, 유형별 breakdown, 수익률 표시 |
| **FE-2** | 자산 목록 (AssetCard) 렌더링 | PASS | 이모지 아이콘, 보유량, 평가금액, 수익/손실 |
| **FE-3** | 자산 추가 모달 | PASS | AssetTypeSelector(인라인), symbol/name 입력 |
| **FE-4** | 거래 기록 모달/폼 | PASS | 자산 드롭다운, 거래유형, 수량/단가/환율/수수료/메모/일시 |
| **FE-5** | 거래 내역 리스트 + 필터 + 페이지네이션 | PARTIAL | 테이블, 배지, 페이지네이션, 삭제 구현됨. **TransactionFilter UI 미구현** (기간/자산유형 필터 없음) |
| **FE-6** | TanStack Query 캐시 무효화 | PASS | 모든 mutation onSuccess에 적절한 invalidateQueries 적용 |
| **FE-7** | 수익률 양수/음수 색상 표시 | PASS | text-green-600/text-red-600 적용 |

---

## 2. 점수

| 카테고리 | 점수 |
|:---------|:----:|
| 설계 일치도 | 88% |
| 아키텍처 준수 | 95% |
| 컨벤션 준수 | 92% |
| **종합 Match Rate** | **91%** |

- **PASS**: 14/16 (87.5%)
- **PARTIAL**: 2/16 (12.5%)
- **FAIL**: 0/16 (0%)

---

## 3. 누락된 기능 (설계 O, 구현 X)

| # | 항목 | 설계 위치 | 영향도 |
|---|------|-----------|:------:|
| 1 | Alembic 마이그레이션 파일 (001~003) | 1.5절 | Medium |
| 2 | TransactionFilter UI 컴포넌트 | 2.3.1절 | Medium |
| 3 | SymbolSearchInput 컴포넌트 | 2.3.1절 | Low |
| 4 | TransactionForm 별도 컴포넌트 분리 | 2.3.1절 | Low |
| 5 | marketKeys 쿼리 키 + useMarketPrice hook | 2.2절 | Low |
| 6 | TransactionFilter Pydantic 모델 (BE) | 1.2.2절 | Low |

---

## 4. 추가된 기능 (설계 X, 구현 O)

| # | 항목 | 구현 위치 | 평가 |
|---|------|-----------|:----:|
| 1 | TransactionUpdateRequest 타입 (FE) | shared/types/index.ts | 필요 |
| 2 | ExchangeRate 타입 (FE) | shared/types/index.ts | 유용 |
| 3 | CurrencyType 타입 (FE) | shared/types/index.ts | 필요 |
| 4 | ASSET_TYPE_LABELS, TRANSACTION_TYPE_LABELS | shared/types/index.ts | 유용 |
| 5 | ApiResponse, PaginatedResponse 공용 타입 | shared/types/index.ts | 유용 |
| 6 | Budget 인터페이스 | shared/types/index.ts | 다른 기능용 |

---

## 5. 변경된 구현 (설계 != 구현)

| 항목 | 설계 | 구현 | 영향도 |
|:-----|:-----|:-----|:------:|
| TransactionFilter 처리 | Pydantic 모델 | Query 파라미터 직접 | 낮음 |
| Asset transactions 힌트 | 타입 힌트 없음 | `Mapped[list["Transaction"]]` | 없음(개선) |
| deps.py user_id | str 그대로 | UUID 변환 추가 | 없음(수정) |
| AssetSummary.breakdown | `Record<AssetType, number>` | `Record<string, number>` | 낮음 |
| FE User.nickname vs BE User.name | name | nickname | 낮음 |

---

## 6. 권장 조치

### High Priority
1. **Alembic 마이그레이션 파일 생성** — DB 테이블 생성에 필수
2. **TransactionFilter UI 구현** — 설계에 명시된 필터 기능 노출 필요

### Medium Priority
3. 설계 문서에 추가된 프론트엔드 타입/상수 반영
4. FE User `nickname` → `name` 필드명 통일

### Low Priority (향후 과제)
5. SymbolSearchInput (종목 자동완성 검색)
6. TransactionForm 별도 컴포넌트 분리
7. marketKeys + useMarketPrice hook
