# 정기거래 (Schedules)

정기적으로 발생하는 수입/지출/이체를 관리한다. 활성화된 스케줄은 해당 일자에 자동으로 거래가 생성된다.

## 정기거래 목록 조회
- **URL**: `GET /api/v1/schedules`
- **설명**: 사용자의 전체 정기거래 목록을 반환한다
- **응답**: `ScheduleResponse[]` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | id | UUID | 정기거래 ID |
  | type | string | "income" / "expense" / "transfer" |
  | name | string | 정기거래명 |
  | amount | decimal | 금액 |
  | currency | string | 통화 |
  | schedule_day | int | 실행일 (0 = 월말) |
  | start_date | date | 시작일 |
  | end_date | date? | 종료일 |
  | total_count | int? | 총 실행 횟수 |
  | executed_count | int | 실행된 횟수 |
  | source_account_id | UUID? | 출금 계좌 ID |
  | target_account_id | UUID? | 입금 계좌 ID |
  | category_id | UUID? | 카테고리 ID |
  | memo | string? | 메모 |
  | is_active | bool | 활성 여부 |
  | created_at | datetime | 생성 시각 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/schedules" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```

---

## 정기거래 생성
- **URL**: `POST /api/v1/schedules`
- **설명**: 새 정기거래를 생성한다. type이 "transfer"이면 source/target 계좌가 모두 필요하고 서로 달라야 한다.
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | type | string | O | "income" / "expense" / "transfer" |
  | name | string | O | 정기거래명 (1-100자) |
  | amount | decimal | O | 금액 (> 0) |
  | currency | string | X | 통화 (기본값: KRW) |
  | schedule_day | int | O | 실행일 (0 = 월말, 1-31) |
  | start_date | date | O | 시작일 |
  | end_date | date | X | 종료일 |
  | total_count | int | X | 총 실행 횟수 (>= 1) |
  | source_account_id | UUID | X | 출금 계좌 (transfer 시 필수) |
  | target_account_id | UUID | X | 입금 계좌 (transfer 시 필수) |
  | category_id | UUID | X | 카테고리 ID |
  | memo | string | X | 메모 (최대 500자) |
- **응답**: `ScheduleResponse` (201)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/schedules" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "type": "expense",
      "name": "넷플릭스 구독료",
      "amount": 17000,
      "schedule_day": 15,
      "start_date": "2026-01-01",
      "category_id": "660e8400-..."
    }'
  ```

---

## 정기거래 상세 조회
- **URL**: `GET /api/v1/schedules/{schedule_id}`
- **설명**: 특정 정기거래의 상세 정보를 반환한다
- **응답**: `ScheduleResponse` (200)

---

## 정기거래 수정
- **URL**: `PATCH /api/v1/schedules/{schedule_id}`
- **설명**: 정기거래 정보를 수정한다 (변경할 필드만 전송)
- **요청 바디**:
  | 필드 | 타입 | 필수 | 설명 |
  |------|------|------|------|
  | name | string | X | 정기거래명 (1-100자) |
  | amount | decimal | X | 금액 (> 0) |
  | schedule_day | int | X | 실행일 (0-31) |
  | end_date | date | X | 종료일 |
  | source_account_id | UUID | X | 출금 계좌 |
  | target_account_id | UUID | X | 입금 계좌 |
  | category_id | UUID | X | 카테고리 ID |
  | memo | string | X | 메모 (최대 500자) |
  | is_active | bool | X | 활성 여부 |
- **응답**: `ScheduleResponse` (200)

---

## 정기거래 삭제
- **URL**: `DELETE /api/v1/schedules/{schedule_id}`
- **설명**: 정기거래를 삭제한다
- **응답**: 204 No Content

---

## 정기거래 토글
- **URL**: `POST /api/v1/schedules/{schedule_id}/toggle`
- **설명**: 정기거래의 활성/비활성 상태를 전환한다
- **응답**: `ScheduleResponse` (200)
- **예시**:
  ```bash
  curl -X POST "${MYFINANCE_BASE_URL}/api/v1/schedules/{schedule_id}/toggle" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```
