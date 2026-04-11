# 포트폴리오 & 시장

## 포트폴리오 (Portfolio)

### 자산 추이 조회
- **URL**: `GET /api/v1/portfolio/timeline`
- **설명**: 기간별 자산 추이(스냅샷 목록)를 반환한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 기본값 | 설명 |
  |---------|------|--------|------|
  | period | string | 1M | 기간: 1W / 1M / 3M / 6M / 1Y / ALL |
- **응답**: `AssetTimelineResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | snapshots | array | 스냅샷 배열 |
  | period | string | 조회 기간 |
  | start_date | date | 시작일 |
  | end_date | date | 종료일 |

  **snapshot 항목**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 스냅샷 ID |
  | snapshot_date | date | 스냅샷 날짜 |
  | total_krw | float | 총 자산 (KRW 환산) |
  | breakdown | dict | 자산 유형별 내역 |
  | created_at | datetime | 생성 시각 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/portfolio/timeline?period=3M" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 자산 스냅샷 생성
- **URL**: `POST /api/v1/portfolio/snapshot`
- **설명**: 현재 시점의 자산 스냅샷을 수동으로 생성한다
- **응답**: 200
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/portfolio/snapshot" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 자산 목표 조회
- **URL**: `GET /api/v1/portfolio/goal`
- **설명**: 자산 목표를 조회한다. 목표가 없으면 null 반환.
- **응답**: `GoalAssetResponse | null` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 목표 ID |
  | target_amount | float | 목표 금액 |
  | target_date | date? | 목표 달성 예정일 |
  | current_amount | float | 현재 자산 |
  | achievement_rate | float | 달성률 (%) |
  | remaining_amount | float | 남은 금액 |
  | monthly_required | float? | 월 필요 저축액 |
  | estimated_date | date? | 예상 달성일 |
  | created_at | datetime | 생성 시각 |
  | updated_at | datetime | 수정 시각 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/portfolio/goal" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 자산 목표 설정
- **URL**: `PUT /api/v1/portfolio/goal`
- **설명**: 자산 목표를 설정하거나 업데이트한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | target_amount | decimal | O | 목표 금액 (> 0) |
  | target_date | date | X | 목표 달성 예정일 |
- **응답**: `GoalAssetResponse` (200)
- **예시**:
  ```bash
  curl -X PUT "${MYFINANCE_BASE_URL}/api/v1/portfolio/goal" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "target_amount": 100000000,
      "target_date": "2028-12-31"
    }'
  ```

---

### 포트폴리오 목표 비중 조회
- **URL**: `GET /api/v1/portfolio/targets`
- **설명**: 자산 유형별 목표 비중과 현재 비중/편차를 반환한다
- **응답**: `PortfolioTargetResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 목표 ID |
  | asset_type | string | 자산 유형 |
  | target_ratio | float | 목표 비중 (0-1) |
  | current_ratio | float | 현재 비중 (0-1) |
  | deviation | float | 편차 |
  | created_at | datetime | 생성 시각 |
  | updated_at | datetime | 수정 시각 |

---

### 포트폴리오 목표 비중 설정
- **URL**: `PUT /api/v1/portfolio/targets`
- **설명**: 자산 유형별 목표 비중을 일괄 설정한다
- **요청 바디**:
  ```json
  {
    "targets": [
      {"asset_type": "stock_kr", "target_ratio": 0.4},
      {"asset_type": "stock_us", "target_ratio": 0.3},
      {"asset_type": "bond", "target_ratio": 0.2},
      {"asset_type": "cash", "target_ratio": 0.1}
    ]
  }
  ```
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | targets | array | O | 목표 비중 배열 |
  | targets[].asset_type | string | O | 자산 유형 |
  | targets[].target_ratio | decimal | O | 목표 비중 (0-1) |
- **응답**: `PortfolioTargetResponse[]` (200)

---

### 리밸런싱 분석
- **URL**: `GET /api/v1/portfolio/rebalancing`
- **설명**: 현재 포트폴리오의 리밸런싱 필요 여부와 제안을 반환한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 기본값 | 설명 |
  |---------|------|--------|------|
  | threshold | float | 0.05 | 리밸런싱 허용 편차 (0.01-0.20) |
- **응답**: `RebalancingAnalysisResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | targets | array | 자산별 목표/현재 비중 |
  | total_deviation | float | 총 편차 |
  | needs_rebalancing | bool | 리밸런싱 필요 여부 |
  | threshold | float | 적용된 허용 편차 |
  | suggestions | array | 리밸런싱 제안 목록 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/portfolio/rebalancing?threshold=0.05" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 리밸런싱 알림 조회
- **URL**: `GET /api/v1/portfolio/alerts`
- **설명**: 리밸런싱 알림 목록을 반환한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 기본값 | 설명 |
  |---------|------|--------|------|
  | threshold | float | 0.05 | 허용 편차 |
- **응답**: `RebalancingAlertResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 알림 ID |
  | snapshot_date | date | 스냅샷 날짜 |
  | deviations | dict | 자산별 편차 |
  | suggestion | dict | 제안 내용 |
  | threshold | float | 적용된 허용 편차 |
  | is_read | bool | 읽음 여부 |
  | created_at | datetime | 생성 시각 |

---

### 알림 읽음 처리
- **URL**: `PATCH /api/v1/portfolio/alerts/{alert_id}/read`
- **설명**: 리밸런싱 알림을 읽음 처리한다
- **응답**: 204 No Content

---

## 시장 (Market)

### 종목 시세 조회
- **URL**: `GET /api/v1/market/price`
- **설명**: 특정 종목의 현재 시세를 조회한다 (Redis 캐시 활용)
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 필수 | 설명 |
  |---------|------|------|------|
  | symbol | string | O | 종목 심볼 (예: "005930", "AAPL") |
  | exchange | string | X | 거래소: KRX / NASDAQ / NYSE / NYSEARCA |
- **응답**: `PriceResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | symbol | string | 종목 심볼 |
  | name | string? | 종목명 |
  | price | float | 현재가 |
  | currency | string | 통화 |
  | change | float? | 변동액 |
  | change_percent | float? | 변동률 (%) |
  | is_market_open | bool | 장 운영 여부 |
  | cached | bool | 캐시된 데이터 여부 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/market/price?symbol=005930&exchange=KRX" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 환율 조회
- **URL**: `GET /api/v1/market/exchange-rate`
- **설명**: USD/KRW 환율을 조회한다
- **응답**: `ExchangeRateResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | pair | string | 통화쌍 (기본: "USD/KRW") |
  | rate | float | 환율 |
  | change | float? | 변동액 |
  | change_percent | float? | 변동률 (%) |
  | cached | bool | 캐시 여부 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/market/exchange-rate" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 시장 동향
- **URL**: `GET /api/v1/market/trends`
- **설명**: 주요 지수, 상승주, 하락주 동향을 반환한다
- **응답**: `MarketTrendsResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | indices | array | 주요 지수 목록 |
  | gainers | array | 상승 종목 |
  | losers | array | 하락 종목 |
  | cached | bool | 캐시 여부 |

  각 항목: `{symbol, name, price, change, change_percent, currency}`

---

### 종목 검색
- **URL**: `GET /api/v1/market/search`
- **설명**: 종목명 또는 심볼로 검색한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 필수 | 설명 |
  |---------|------|------|------|
  | query | string | O | 검색어 |
- **응답**: `MarketSearchResponse` (200)
- **응답 필드**:
  ```json
  {
    "query": "삼성",
    "results": [
      {"symbol": "005930", "name": "삼성전자", "exchange": "KRX", "asset_type": "stock"}
    ],
    "cached": false
  }
  ```
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/market/search?query=AAPL" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### 시세 강제 새로고침
- **URL**: `POST /api/v1/market/refresh-price`
- **설명**: 특정 종목의 시세를 캐시 무시하고 강제 갱신한다
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | symbol | string | O | 종목 심볼 |
  | exchange | string | X | 거래소 |
- **응답**: `PriceResponse` (200)

---

### 환율 강제 새로고침
- **URL**: `POST /api/v1/market/refresh-exchange-rate`
- **설명**: 환율을 캐시 무시하고 강제 갱신한다
- **응답**: `ExchangeRateResponse` (200)

---

### 전체 시세 일괄 새로고침
- **URL**: `POST /api/v1/market/refresh-all`
- **설명**: 보유 중인 모든 증권의 시세와 환율을 일괄 갱신한다
- **응답**: 200
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/market/refresh-all" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```
