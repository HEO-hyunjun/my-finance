# PDCA Completion Report: deposit-savings

> **Feature**: deposit-savings (예금/적금/파킹통장)
> **Project**: MyFinance
> **Date**: 2026-02-05
> **PDCA Phase**: Completed
> **Author**: Claude Code (report-generator)

---

## 1. Executive Summary

기존 자산 관리(asset-management) 기능을 확장하여 **예금(deposit)**, **적금(savings)**, **CMA/파킹통장(parking)** 3가지 자산 유형을 추가했습니다. 사용자가 연이율을 직접 입력하면 경과 기간에 따른 이자를 자동 계산하여 자산 가치에 반영합니다.

| Metric | Value |
|--------|-------|
| **Match Rate** | 97% |
| **Checklist** | 15/15 PASS |
| **Iteration Count** | 0 (첫 Check에서 통과) |
| **Files Modified** | 7 |
| **Files Created** | 1 |

---

## 2. PDCA Cycle Summary

```
[Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ (97%) → [Report] ✅
```

| Phase | Status | Output |
|-------|--------|--------|
| Plan | ✅ Completed | `docs/01-plan/features/deposit-savings.plan.md` |
| Design | ✅ Completed | `docs/02-design/features/deposit-savings.design.md` |
| Do | ✅ Completed | Backend + Frontend 구현 완료 |
| Check | ✅ Passed (97%) | `docs/03-analysis/deposit-savings.analysis.md` |
| Report | ✅ This document | `docs/04-report/features/deposit-savings.report.md` |

---

## 3. Implementation Summary

### 3.1 Backend Changes

| File | Change Type | Description |
|------|:-----------:|-------------|
| `backend/app/models/asset.py` | Modified | AssetType에 DEPOSIT/SAVINGS/PARKING 추가, InterestType enum 신규, Asset 모델에 8개 nullable 필드 추가 |
| `backend/app/services/interest_service.py` | Created | 이자 계산 서비스 3개 함수: `calculate_deposit_interest`, `calculate_savings_interest`, `calculate_parking_interest` |
| `backend/app/schemas/asset.py` | Modified | AssetCreate에 model_validator 추가, AssetResponse/AssetHoldingResponse에 이자 관련 필드 확장 |
| `backend/app/services/asset_service.py` | Modified | `create_asset` 확장, `_calculate_holding`에 deposit/savings/parking 분기 추가 |

### 3.2 Frontend Changes

| File | Change Type | Description |
|------|:-----------:|-------------|
| `frontend/src/shared/types/index.ts` | Modified | AssetType에 3개 값 추가, InterestType 타입, Asset/AssetCreateRequest/AssetHolding 인터페이스 확장, ASSET_TYPE_LABELS 확장 |
| `frontend/src/features/assets/ui/AddAssetModal.tsx` | Modified | 8가지 자산 유형 선택(grid-cols-4), deposit/savings/parking 유형별 조건부 입력 폼 |
| `frontend/src/features/assets/ui/AssetCard.tsx` | Modified | 이자 기반 자산 전용 카드 레이아웃 (예금/적금: 원금+경과이자+만기예상, 파킹: 잔액+일일이자+월예상이자) |

### 3.3 Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Asset 모델에 nullable 필드 추가 (별도 테이블 X) | 기존 자산 유형과 동일 테이블 유지로 쿼리 단순화, 필드 수 관리 가능 수준 |
| 이자 계산을 별도 서비스로 분리 (`interest_service.py`) | 단일 책임 원칙, 계산 로직 테스트 용이성 |
| 만기일 경과 방지 guard 추가 | `min(as_of_date, maturity_date)` — 설계에 없었지만 edge case 방지를 위해 구현 시 추가 |
| 파킹통장 `principal is None` 검증 | 0원 잔액도 유효한 상태이므로 `is None` 체크로 개선 |

---

## 4. Success Criteria Verification

| # | Criteria | Status |
|---|---------|:------:|
| 1 | 예금/적금/파킹통장 자산 등록 (유형별 전용 입력 폼) | ✅ |
| 2 | 예금: 원금 기반 경과이자 자동 계산 (단리/복리) | ✅ |
| 3 | 적금: 월납입액 기반 경과이자 자동 계산 | ✅ |
| 4 | 파킹통장: 현재잔액 기반 일일이자/월예상이자 표시 | ✅ |
| 5 | 이자소득세 (15.4%) 세후이자 표시 | ✅ |
| 6 | 자산 요약에 예금/적금/파킹 포함 (총자산, 유형별 breakdown) | ✅ |
| 7 | AssetCard에서 유형별 정보 표시 (이율, 만기일/일일이자 등) | ✅ |
| 8 | 기존 자산 유형(주식/금/현금)에 영향 없음 (하위 호환) | ✅ |
| 9 | Frontend 빌드 통과 (`tsc -b && vite build`) | ✅ |

**결과: 9/9 성공 기준 충족**

---

## 5. Gap Analysis Results

### 5.1 Scores

| Category | Score |
|----------|:-----:|
| Design Match | 97% |
| Architecture Compliance | 100% |
| Convention Compliance | 98% |
| **Overall** | **97%** |

### 5.2 Checklist Summary

- **PASS**: 15/15 (100%)
- **PARTIAL**: 0/15
- **FAIL**: 0/15

### 5.3 Notable Findings

| Type | Count | Description |
|------|:-----:|-------------|
| 설계 대비 개선 | 2 | 만기일 경과 방지 guard, INTEREST_BASED_TYPES 상수 추가 |
| 사소한 차이 (영향 없음) | 3 | comment 속성, principal 검증 방식, annual_interest 반환값 |
| 미구현 (선택사항) | 1 | PUT /api/v1/assets/{id}/balance (설계에서 "선택"으로 표기) |

---

## 6. Interest Calculation Formulas (Implemented)

### 예금 (Deposit)

```
[단리] 세전이자 = 원금 × (연이율/100) × (경과일수/365)
[복리] 세전이자 = 원금 × (1 + 연이율/100/12)^경과월수 - 원금
세후이자 = 세전이자 × (1 - 세율)
현재가치 = 원금 + 세후이자
```

### 적금 (Savings)

```
총납입액 = 월납입액 × 납입회차
세전이자 = 월납입액 × (연이율/100/12) × n(n+1)/2
세후이자 = 세전이자 × (1 - 세율)
현재가치 = 총납입액 + 세후이자
```

### CMA/파킹통장 (Parking)

```
일일이자 = 현재잔액 × (연이율/100) / 365
월예상이자 = 일일이자 × 30 × (1 - 세율)
현재가치 = 잔액 (이자는 별도 표시)
```

---

## 7. Lessons Learned

| Category | Lesson |
|----------|--------|
| **설계 품질** | 설계 문서에서 필드별 nullable, 타입, 검증 규칙을 명확히 지정한 것이 구현 속도를 높임 |
| **확장 패턴** | 기존 Asset 모델에 nullable 필드를 추가하는 방식이 하위 호환성을 자연스럽게 보장 |
| **이자 계산 분리** | 별도 서비스(`interest_service.py`)로 분리하여 `asset_service.py`의 복잡도를 관리 가능 수준으로 유지 |
| **조건부 UI** | `isDeposit/isSavings/isParking/isInterestBased` 변수로 조건부 렌더링을 깔끔하게 구현 |
| **Edge Case** | 구현 시 발견한 edge case(만기일 경과, 0원 잔액)를 방어적으로 처리 — 설계 단계에서 미리 고려하면 더 좋음 |

---

## 8. Future Improvements

| Priority | Item | Description |
|:--------:|------|-------------|
| Low | PUT /balance API | 파킹통장 잔액 업데이트 전용 API (현재는 자산 삭제 후 재등록) |
| Low | Alembic 마이그레이션 | DB 스키마 변경 마이그레이션 파일 생성 |
| Medium | 만기 도래 알림 | 예금/적금 만기일 N일 전 알림 기능 |
| Low | 자유적금 지원 | 변동 납입액 적금 계산 |
| Low | 이율 변경 이력 | 파킹통장 이율 변경 시 이력 관리 |

---

## 9. Conclusion

deposit-savings 기능은 PDCA 사이클을 완전히 통과했습니다.

- **Plan**: 3가지 자산 유형 정의, 이자 계산 공식, 구현 범위 확정
- **Design**: Backend/Frontend 상세 설계, 15개 검증 체크리스트 정의
- **Do**: Backend 4개 파일 + Frontend 3개 파일 구현 완료
- **Check**: Match Rate 97%, 15/15 체크리스트 PASS
- **성공 기준**: 9/9 충족

기존 asset-management 기능과의 하위 호환성을 유지하면서, 예금/적금/파킹통장이라는 새로운 자산 유형을 자연스럽게 통합했습니다.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-05 | Initial completion report | Claude Code (report-generator) |
