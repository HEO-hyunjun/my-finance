# 예산 & 이월

## 예산 (Budget)

### 예산 개요
- **URL**: `GET /api/v1/budget/overview`
- **설명**: Top-down 방식의 예산 개요를 반환한다. 수입 - 고정지출 - 이체 = 가용예산, 배분/미배분 금액을 보여준다.
- **응답**: `BudgetOverviewResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | period_start | string | 예산 기간 시작일 |
  | period_end | string | 예산 기간 종료일 |
  | period_start_day | int | 예산 시작 일자 (급여일) |
  | total_income | decimal | 총 수입 |
  | total_fixed_expense | decimal | 총 고정 지출 |
  | total_transfer | decimal | 총 이체 |
  | available_budget | decimal | 가용 예산 (수입 - 고정지출 - 이체) |
  | total_allocated | decimal | 배분된 금액 |
  | unallocated | decimal | 미배분 금액 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/budget/overview" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 카테고리별 예산 배분 조회
- **URL**: `GET /api/v1/budget/categories`
- **설명**: 카테고리별 배분 금액과 실제 지출을 반환한다
- **응답**: `CategoryBudgetResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | allocation_id | string | 배분 ID |
  | category_id | string | 카테고리 ID |
  | allocated | decimal | 배분 금액 |
  | spent | decimal | 실제 지출 |
  | remaining | decimal | 잔여 예산 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/budget/categories" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 예산 배분 생성/업데이트
- **URL**: `POST /api/v1/budget/allocations`
- **설명**: 카테고리에 예산을 배분한다. 이미 배분이 있으면 업데이트된다.
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | category_id | UUID | O | 카테고리 ID |
  | amount | decimal | O | 배분 금액 |
- **응답**: 201 Created
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/budget/allocations" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "category_id": "660e8400-...",
      "amount": 300000
    }'
  ```

---

### 예산 배분 수정
- **URL**: `PATCH /api/v1/budget/allocations/{allocation_id}`
- **설명**: 배분 금액을 수정한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | amount | decimal | O | 새 배분 금액 |
- **응답**: 200

---

### 예산 배분 삭제
- **URL**: `DELETE /api/v1/budget/allocations/{allocation_id}`
- **설명**: 예산 배분을 삭제한다
- **응답**: 204 No Content

---

### 예산 기간 조회
- **URL**: `GET /api/v1/budget/period`
- **설명**: 예산 기간 설정(시작일)을 조회한다
- **응답**: 200
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/budget/period" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 예산 기간 시작일 변경
- **URL**: `PATCH /api/v1/budget/period`
- **설명**: 예산 기간 시작일을 변경한다 (보통 급여일에 맞춤)
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | period_start_day | int | O | 시작일 (1-28) |
- **응답**: 200
- **예시**:
  ```bash
  curl -X PATCH "${MYFINANCE_BASE_URL}/api/v1/budget/period" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"period_start_day": 25}'
  ```

---

### 예산 분석
- **URL**: `GET /api/v1/budget/analysis`
- **설명**: 일일 예산, 주간 분석, 카테고리별 소비율, 고정비 요약, 이월 예측 등 종합 분석을 반환한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 설명 |
  |---------|------|------|
  | start | date | 분석 시작일 |
  | end | date | 분석 종료일 |
- **응답**: `BudgetAnalysisResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | daily_budget | object | 일일 가용 예산, 오늘 지출, 잔여일수 |
  | weekly_analysis | object | 주간 지출, 주평균 대비 비율 |
  | category_rates | array | 카테고리별 소비율 + 상태 (normal/warning/exceeded) |
  | fixed_deductions | object | 고정비 항목, 납부 여부, 잔여 금액 |
  | carryover_predictions | array | 이월 예측 (카테고리별 잔여/이월 유형/이월 금액) |
  | alerts | string[] | 예산 경고 메시지 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/budget/analysis?start=2026-03-25&end=2026-04-24" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

## 이월 (Carryover)

### 이월 설정 목록
- **URL**: `GET /api/v1/carryover/settings`
- **설명**: 카테고리별 이월 설정 목록을 반환한다
- **응답**: `CarryoverSettingResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 설정 ID |
  | category_id | UUID | 카테고리 ID |
  | category_name | string | 카테고리명 |
  | carryover_type | string | 이월 유형 (아래 참조) |
  | carryover_limit | float? | 이월 한도 |
  | source_asset_id | UUID? | 출금 자산 ID |
  | source_asset_name | string? | 출금 자산명 |
  | target_asset_id | UUID? | 입금 자산 ID |
  | target_savings_name | string? | 적금명 |
  | target_annual_rate | float? | 연이율 |
  | created_at | datetime | 생성 시각 |
  | updated_at | datetime | 수정 시각 |

**이월 유형 (carryover_type)**:
| 값 | 설명 |
|---|------|
| expire | 소멸 (잔여 예산 소멸) |
| next_month | 다음 달로 이월 |
| savings | 적금으로 이체 |
| transfer | 다른 계좌로 이체 |
| deposit | 예금으로 이체 |

- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/carryover/settings" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 이월 설정 생성/업데이트
- **URL**: `POST /api/v1/carryover/settings`
- **설명**: 카테고리의 이월 설정을 생성하거나 업데이트한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | category_id | UUID | O | 카테고리 ID |
  | carryover_type | string | O | expire/next_month/savings/transfer/deposit |
  | carryover_limit | decimal | X | 이월 한도 (>= 0) |
  | source_asset_id | UUID | X | 출금 자산 ID |
  | target_asset_id | UUID | X | 입금 자산 ID |
  | target_savings_name | string | X | 적금명 (최대 100자) |
  | target_annual_rate | decimal | X | 연이율 (0-100) |
- **응답**: `CarryoverSettingResponse` (201)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/carryover/settings" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "category_id": "660e8400-...",
      "carryover_type": "next_month"
    }'
  ```

---

### 이월 미리보기
- **URL**: `GET /api/v1/carryover/preview`
- **설명**: 지정 기간의 이월 결과를 미리 확인한다 (실제 실행 없음)
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 필수 | 설명 |
  |---------|------|------|------|
  | period_start | date | O | 예산 기간 시작일 |
  | period_end | date | O | 예산 기간 종료일 |
- **응답**: `CarryoverPreviewResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | category_id | UUID | 카테고리 ID |
  | category_name | string | 카테고리명 |
  | carryover_type | string | 이월 유형 |
  | budget | float | 예산 |
  | spent | float | 지출 |
  | remaining | float | 잔여 |
  | carryover_amount | float | 이월 금액 |
  | target_description | string? | 이월 대상 설명 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/carryover/preview?period_start=2026-03-25&period_end=2026-04-24" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 이월 실행
- **URL**: `POST /api/v1/carryover/execute`
- **설명**: 이월을 실행한다. **되돌릴 수 없으므로 반드시 사용자 확인 후 실행.**
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | period_start | date | O | 예산 기간 시작일 |
  | period_end | date | O | 예산 기간 종료일 |
- **응답**: `CarryoverLogResponse[]` (200)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/carryover/execute" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "period_start": "2026-03-25",
      "period_end": "2026-04-24"
    }'
  ```

---

### 이월 로그 조회
- **URL**: `GET /api/v1/carryover/logs`
- **설명**: 이월 실행 로그를 조회한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 설명 |
  |---------|------|------|
  | period_start | date | 예산 기간 시작일 필터 |
  | period_end | date | 예산 기간 종료일 필터 |
- **응답**: `CarryoverLogResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 로그 ID |
  | category_id | UUID | 카테고리 ID |
  | category_name | string | 카테고리명 |
  | budget_period_start | date | 예산 기간 시작 |
  | budget_period_end | date | 예산 기간 종료 |
  | carryover_type | string | 이월 유형 |
  | amount | float | 이월 금액 |
  | target_description | string? | 이월 대상 설명 |
  | executed_at | datetime | 실행 시각 |
  | created_at | datetime | 생성 시각 |
