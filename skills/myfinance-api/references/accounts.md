# 계좌 & 거래 & 카테고리

## 계좌 (Accounts)

### 계좌 목록 조회
- **URL**: `GET /api/v1/accounts`
- **설명**: 사용자의 전체 계좌 목록을 반환한다
- **응답**: `AccountResponse[]` (200)
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/accounts" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 계좌 ID |
  | account_type | string | 계좌 유형 |
  | name | string | 계좌명 |
  | currency | string | 통화 (KRW, USD 등) |
  | institution | string? | 금융기관명 |
  | interest_rate | decimal? | 이자율 |
  | interest_type | string? | 이자 유형 |
  | monthly_amount | decimal? | 월 납입액 |
  | start_date | date? | 시작일 |
  | maturity_date | date? | 만기일 |
  | tax_rate | decimal? | 세율 |
  | is_active | bool | 활성 여부 |
  | created_at | datetime | 생성 시각 |

---

### 계좌 생성
- **URL**: `POST /api/v1/accounts`
- **설명**: 새 계좌를 생성한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | account_type | string | O | 계좌 유형 |
  | name | string | O | 계좌명 |
  | currency | string | X | 통화 (기본값: KRW) |
  | institution | string | X | 금융기관명 |
  | interest_rate | decimal | X | 이자율 |
  | interest_type | string | X | 이자 유형 |
  | monthly_amount | decimal | X | 월 납입액 |
  | start_date | date | X | 시작일 |
  | maturity_date | date | X | 만기일 |
  | tax_rate | decimal | X | 세율 |
- **응답**: `AccountResponse` (201)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/accounts" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "account_type": "savings",
      "name": "비상금 통장",
      "currency": "KRW",
      "institution": "카카오뱅크"
    }'
  ```

---

### 계좌 상세 조회
- **URL**: `GET /api/v1/accounts/{account_id}`
- **설명**: 특정 계좌의 상세 정보를 반환한다
- **응답**: `AccountResponse` (200)
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/accounts/{account_id}" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 계좌 요약 조회
- **URL**: `GET /api/v1/accounts/{account_id}/summary`
- **설명**: 계좌의 잔액과 보유 자산 요약을 반환한다
- **응답**: `AccountSummary` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | string | 계좌 ID |
  | name | string | 계좌명 |
  | account_type | string | 계좌 유형 |
  | currency | string | 통화 |
  | balance | decimal | 총 잔액 |
  | cash_balance | decimal? | 현금 잔액 |
  | holdings | list[dict]? | 보유 종목 목록 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/accounts/{account_id}/summary" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 계좌 수정
- **URL**: `PATCH /api/v1/accounts/{account_id}`
- **설명**: 계좌 정보를 수정한다 (변경할 필드만 전송)
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | name | string | X | 계좌명 |
  | institution | string | X | 금융기관명 |
  | interest_rate | decimal | X | 이자율 |
  | interest_type | string | X | 이자 유형 |
  | monthly_amount | decimal | X | 월 납입액 |
  | start_date | date | X | 시작일 |
  | maturity_date | date | X | 만기일 |
  | tax_rate | decimal | X | 세율 |
  | is_active | bool | X | 활성 여부 |
- **응답**: `AccountResponse` (200)
- **예시**:
  ```bash
  curl -X PATCH "${MYFINANCE_BASE_URL}/api/v1/accounts/{account_id}" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"name": "비상금 통장 (수정)"}'
  ```

---

### 계좌 삭제
- **URL**: `DELETE /api/v1/accounts/{account_id}`
- **설명**: 계좌를 삭제한다
- **응답**: 204 No Content
- **예시**:
  ```bash
  curl -X DELETE "${MYFINANCE_BASE_URL}/api/v1/accounts/{account_id}" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 잔액 조정
- **URL**: `POST /api/v1/accounts/{account_id}/adjust`
- **설명**: 계좌의 잔액을 특정 금액으로 맞춘다. 현금 잔액뿐 아니라 증권 보유수량도 조정 가능하다.
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | target_balance | decimal | O | 맞추려는 목표 잔액 |
  | currency | string | X | 통화 (기본값: KRW) |
  | memo | string | X | 메모 |
  | security_id | UUID | X | 종목 ID (보유수량 조정 시) |
  | target_quantity | decimal | X | 목표 보유수량 |
  | unit_price | decimal | X | 단가 |
- **응답**: `EntryResponse` (200)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/accounts/{account_id}/adjust" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "target_balance": 1000000,
      "memo": "실제 잔액 맞춤"
    }'
  ```

---

## 거래 (Entries)

### 거래 목록 조회
- **URL**: `GET /api/v1/entries`
- **설명**: 거래 목록을 페이지네이션으로 조회한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 기본값 | 설명 |
  |---------|------|--------|------|
  | account_id | UUID | - | 계좌 필터 |
  | type | string | - | 거래 유형 필터 (income/expense/adjustment) |
  | category_id | UUID | - | 카테고리 필터 |
  | start_date | date | - | 시작 날짜 |
  | end_date | date | - | 종료 날짜 |
  | page | int | 1 | 페이지 번호 |
  | per_page | int | 20 | 페이지당 항목 수 (최대 100) |
- **응답**: `EntryListResponse` (200)
  ```json
  {
    "data": [...],
    "total": 150,
    "page": 1,
    "per_page": 20
  }
  ```
- **응답 필드** (data 배열 각 항목):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 거래 ID |
  | account_id | UUID | 계좌 ID |
  | entry_group_id | UUID? | 그룹 ID (이체/매매 시 묶음) |
  | category_id | UUID? | 카테고리 ID |
  | security_id | UUID? | 종목 ID |
  | type | string | 거래 유형 (income/expense/adjustment) |
  | amount | decimal | 금액 (지출은 음수) |
  | currency | string | 통화 |
  | quantity | decimal? | 수량 (증권) |
  | unit_price | decimal? | 단가 (증권) |
  | fee | decimal | 수수료 |
  | exchange_rate | decimal? | 환율 |
  | memo | string? | 메모 |
  | recurring_schedule_id | UUID? | 연결된 정기거래 ID |
  | transacted_at | datetime | 거래 일시 |
  | created_at | datetime | 생성 시각 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/entries?account_id={id}&start_date=2026-04-01&end_date=2026-04-30&page=1&per_page=50" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 거래 생성
- **URL**: `POST /api/v1/entries`
- **설명**: 단일 거래(수입/지출/조정)를 생성한다. 지출 금액은 양수로 보내도 자동으로 음수로 변환된다.
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | account_id | UUID | O | 계좌 ID |
  | type | string | O | "income" / "expense" / "adjustment" |
  | amount | decimal | O | 금액 (지출은 양수로 보내도 자동 음수 변환) |
  | currency | string | X | 통화 (기본값: KRW) |
  | category_id | UUID | X | 카테고리 ID |
  | security_id | UUID | X | 종목 ID |
  | quantity | decimal | X | 수량 |
  | unit_price | decimal | X | 단가 |
  | fee | decimal | X | 수수료 (기본값: 0, >= 0) |
  | exchange_rate | decimal | X | 환율 |
  | memo | string | X | 메모 (최대 1000자) |
  | transacted_at | datetime | O | 거래 일시 |
- **응답**: `EntryResponse` (201)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/entries" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "account_id": "550e8400-...",
      "type": "expense",
      "amount": 15000,
      "category_id": "660e8400-...",
      "memo": "점심 식사",
      "transacted_at": "2026-04-11T12:30:00"
    }'
  ```

---

### 계좌 간 이체
- **URL**: `POST /api/v1/entries/transfer`
- **설명**: 두 계좌 간 이체를 생성한다. 출금/입금 계좌가 같으면 에러.
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | source_account_id | UUID | O | 출금 계좌 ID |
  | target_account_id | UUID | O | 입금 계좌 ID |
  | amount | decimal | O | 이체 금액 (> 0) |
  | currency | string | X | 통화 (기본값: KRW) |
  | memo | string | X | 메모 (최대 1000자) |
  | transacted_at | datetime | X | 거래 일시 |
- **응답**: `EntryResponse[]` (201) — 출금/입금 2건의 거래가 반환됨
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/entries/transfer" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "source_account_id": "550e8400-...",
      "target_account_id": "660e8400-...",
      "amount": 500000,
      "memo": "적금 이체"
    }'
  ```

---

### 증권 매매
- **URL**: `POST /api/v1/entries/trade`
- **설명**: 증권 매수/매도를 기록한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | account_id | UUID | O | 투자 계좌 ID |
  | security_id | UUID | O | 종목 ID |
  | trade_type | string | O | "buy" / "sell" |
  | quantity | decimal | O | 수량 (> 0) |
  | unit_price | decimal | O | 단가 (> 0) |
  | currency | string | X | 통화 (기본값: KRW) |
  | fee | decimal | X | 수수료 (기본값: 0, >= 0) |
  | exchange_rate | decimal | X | 환율 |
  | memo | string | X | 메모 (최대 1000자) |
  | transacted_at | datetime | X | 거래 일시 |
- **응답**: `EntryResponse[]` (201)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/entries/trade" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "account_id": "550e8400-...",
      "security_id": "770e8400-...",
      "trade_type": "buy",
      "quantity": 10,
      "unit_price": 75000,
      "fee": 1500
    }'
  ```

---

### 거래 상세 조회
- **URL**: `GET /api/v1/entries/{entry_id}`
- **설명**: 특정 거래의 상세 정보를 반환한다
- **응답**: `EntryResponse` (200)
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/entries/{entry_id}" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 거래 수정
- **URL**: `PATCH /api/v1/entries/{entry_id}`
- **설명**: 거래 정보를 수정한다 (변경할 필드만 전송)
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | amount | decimal | X | 금액 |
  | category_id | UUID | X | 카테고리 ID |
  | memo | string | X | 메모 (최대 1000자) |
  | quantity | decimal | X | 수량 |
  | unit_price | decimal | X | 단가 |
  | fee | decimal | X | 수수료 (>= 0) |
  | transacted_at | datetime | X | 거래 일시 |
- **응답**: `EntryResponse` (200)
- **예시**:
  ```bash
  curl -X PATCH "${MYFINANCE_BASE_URL}/api/v1/entries/{entry_id}" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"memo": "점심 식사 (수정)", "amount": 16000}'
  ```

---

### 거래 삭제
- **URL**: `DELETE /api/v1/entries/{entry_id}`
- **설명**: 거래를 삭제한다
- **응답**: 204 No Content
- **예시**:
  ```bash
  curl -X DELETE "${MYFINANCE_BASE_URL}/api/v1/entries/{entry_id}" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

## 카테고리 (Categories)

### 카테고리 목록 조회
- **URL**: `GET /api/v1/categories`
- **설명**: 카테고리 목록을 조회한다. 방향(수입/지출)으로 필터링 가능.
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 설명 |
  |---------|------|------|
  | direction | string | "income" 또는 "expense" 필터 |
- **응답**: `CategoryResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 카테고리 ID |
  | direction | string | "income" / "expense" |
  | name | string | 카테고리명 |
  | icon | string? | 아이콘 |
  | color | string? | 색상 코드 |
  | sort_order | int | 정렬 순서 |
  | is_active | bool | 활성 여부 |
  | created_at | datetime | 생성 시각 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/categories?direction=expense" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 카테고리 생성
- **URL**: `POST /api/v1/categories`
- **설명**: 새 카테고리를 생성한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | direction | string | O | "income" / "expense" |
  | name | string | O | 카테고리명 |
  | icon | string | X | 아이콘 |
  | color | string | X | 색상 코드 |
  | sort_order | int | X | 정렬 순서 (기본값: 0) |
- **응답**: `CategoryResponse` (201)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/categories" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "direction": "expense",
      "name": "교통비",
      "icon": "🚌",
      "color": "#3B82F6"
    }'
  ```

---

### 카테고리 수정
- **URL**: `PATCH /api/v1/categories/{category_id}`
- **설명**: 카테고리 정보를 수정한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | name | string | X | 카테고리명 |
  | icon | string | X | 아이콘 |
  | color | string | X | 색상 코드 |
  | sort_order | int | X | 정렬 순서 |
  | is_active | bool | X | 활성 여부 |
- **응답**: `CategoryResponse` (200)

---

### 카테고리 삭제
- **URL**: `DELETE /api/v1/categories/{category_id}`
- **설명**: 카테고리를 삭제한다
- **응답**: 204 No Content
