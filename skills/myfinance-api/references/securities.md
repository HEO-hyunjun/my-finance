# 종목 (Securities)

증권 종목 마스터 데이터. 매매(trade) 기록이나 보유수량 조정 시 필요한 `security_id`를 얻기 위한 엔드포인트.

## 종목 목록/검색

- **URL**: `GET /api/v1/securities`
- **설명**: 등록된 종목 목록을 반환한다. `symbol` 쿼리로 정확 일치 필터 가능.
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 설명 |
  |---------|------|------|
  | symbol | string | 심볼로 정확 일치 필터 (예: "VOO") |
- **응답**: `SecurityResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 종목 ID |
  | symbol | string | 종목 심볼 (예: AAPL, 005930) |
  | name | string | 종목명 |
  | currency | string | 통화 (KRW, USD 등) |
  | asset_class | string | equity_kr / equity_us / commodity / currency_pair |
  | data_source | string | yahoo / manual |
  | exchange | string? | 거래소 |
  | created_at | datetime | 생성 시각 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/securities?symbol=VOO" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

## 종목 생성

- **URL**: `POST /api/v1/securities`
- **설명**: 새 종목을 등록한다. 이미 같은 symbol이 있으면 409.
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | symbol | string | O | 종목 심볼 (최대 20자) |
  | name | string | O | 종목명 (최대 100자) |
  | currency | string | X | 통화 (기본값: KRW) |
  | asset_class | string | O | equity_kr / equity_us / commodity / currency_pair |
  | data_source | string | X | yahoo / manual (기본값: manual) |
  | exchange | string | X | 거래소 (예: NMS, PCX, KRX) |
- **응답**: `SecurityResponse` (201)
- **에러**:
  - 409 Conflict: 같은 symbol의 종목이 이미 존재. detail에 기존 `id` 포함.
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/securities" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "symbol": "VOO",
      "name": "Vanguard S&P 500 ETF",
      "currency": "USD",
      "asset_class": "equity_us",
      "exchange": "PCX"
    }'
  ```

---

## 매매 기록 워크플로우

매매(`POST /entries/trade`) 또는 종목 보유수량 조정(`POST /accounts/{id}/adjust` with `security_id`)에는 UUID `security_id`가 필수다. 일반적인 순서:

1. `GET /securities?symbol=VOO`로 존재 여부 확인
2. 없으면 `POST /securities`로 등록 → `id` 획득
3. 해당 `id`를 `security_id`로 매매/조정 API 호출
