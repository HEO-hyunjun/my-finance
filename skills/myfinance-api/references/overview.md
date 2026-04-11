# 대시보드 & 캘린더

## 대시보드 (Dashboard)

### 대시보드 요약
- **URL**: `GET /api/v1/dashboard/summary`
- **설명**: 자산, 예산, 최근 거래, 시장 정보, 예정 결제, 만기 알림을 한 번에 반환한다
- **응답**: `DashboardSummaryResponse` (200)
- **응답 필드**:

  **asset_summary** (자산 요약):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | total_value_krw | float | 총 자산 (KRW 환산) |
  | total_invested_krw | float | 총 투자 원금 |
  | total_profit_loss | float | 총 수익/손실 |
  | total_profit_loss_rate | float | 총 수익률 (%) |
  | daily_change | float? | 전일 대비 변동 |
  | daily_change_rate | float? | 전일 대비 변동률 (%) |
  | breakdown | dict | 자산 유형별 금액 |

  **budget_summary** (예산 요약):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | total_budget | float | 총 예산 |
  | total_spent | float | 총 지출 |
  | total_remaining | float | 잔여 예산 |
  | total_usage_rate | float | 사용률 (%) |
  | total_fixed_expenses | float | 고정 지출 합계 |
  | total_installments | float | 할부 합계 |
  | daily_available | float | 일일 가용 예산 |
  | today_spent | float | 오늘 지출 |
  | remaining_days | int | 예산 잔여 일수 |
  | top_categories | array | 상위 카테고리별 예산/지출 |

  **recent_transactions** (최근 거래):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | string | 거래 ID |
  | asset_name | string | 자산/계좌명 |
  | asset_type | string | 자산 유형 |
  | type | string | 거래 유형 |
  | quantity | float | 수량 |
  | unit_price | float | 단가 |
  | currency | string | 통화 |
  | transacted_at | datetime | 거래 일시 |

  **market_info** (시장 정보):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | exchange_rate | object | 환율 (symbol, name, price, change, change_percent) |
  | gold_price | object? | 금 시세 |

  **upcoming_payments** (예정 결제):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | name | string | 결제명 |
  | amount | float | 금액 |
  | payment_day | int | 결제일 |
  | type | string | 유형 |
  | remaining | string? | 잔여 횟수 |
  | category_name | string? | 카테고리명 |
  | category_color | string? | 카테고리 색상 |

  **maturity_alerts** (만기 알림):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | name | string | 자산명 |
  | asset_type | string | 자산 유형 |
  | maturity_date | date | 만기일 |
  | principal | float | 원금 |
  | maturity_amount | float? | 만기 수령액 |
  | days_remaining | int | 남은 일수 |
  | bank_name | string? | 은행명 |

- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/dashboard/summary" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

### AI 재무 인사이트
- **URL**: `GET /api/v1/dashboard/insights`
- **설명**: AI가 생성한 재무 인사이트(소비 패턴, 예산 경고, 투자 제안 등)를 반환한다
- **응답**: `AIInsightsResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | insights | array | 인사이트 배열 |

  **insight 항목**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | type | string | 유형: spending / budget / investment / saving / alert |
  | title | string | 제목 |
  | description | string | 상세 설명 |
  | severity | string | 심각도: info / warning / success |
  | generated_at | date? | 생성 날짜 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/dashboard/insights" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

## 캘린더 (Calendar)

### 월별 캘린더 이벤트
- **URL**: `GET /api/v1/calendar/events`
- **설명**: 특정 월의 캘린더 이벤트(고정지출, 할부, 만기, 수입/지출)를 반환한다
- **쿼리 파라미터**:
  | 파라미터 | 타입 | 필수 | 설명 |
  |---------|------|------|------|
  | year | int | O | 연도 (2020-2100) |
  | month | int | O | 월 (1-12) |
- **응답**: `CalendarEventsResponse` (200)
- **응답 필드**:

  **events** (이벤트 배열):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | date | date | 이벤트 날짜 |
  | type | string | fixed_expense / installment / maturity / expense / income |
  | title | string | 이벤트명 |
  | amount | float | 금액 |
  | color | string | HEX 색상 코드 |
  | description | string? | 설명 |
  | source_asset_name | string? | 출금 자산명 |

  **day_summaries** (일자별 요약):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | date | date | 날짜 |
  | total_amount | float | 총 금액 |
  | total_expense | float | 총 지출 |
  | total_income | float | 총 수입 |
  | event_count | int | 이벤트 수 |
  | event_types | string[] | 이벤트 유형 목록 |

  **month_summary** (월 요약):
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | year | int | 연도 |
  | month | int | 월 |
  | total_scheduled_amount | float | 총 예정 금액 |
  | total_expense_amount | float | 총 지출 |
  | total_income_amount | float | 총 수입 |
  | event_count | int | 이벤트 수 |
  | maturity_count | int | 만기 건수 |
  | budget_period_start | date? | 예산 기간 시작 |
  | budget_period_end | date? | 예산 기간 종료 |

- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/calendar/events?year=2026&month=4" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```
