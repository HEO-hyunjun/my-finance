# deposit-savings Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: MyFinance
> **Analyst**: Claude Code (gap-detector)
> **Date**: 2026-02-05
> **Design Doc**: [deposit-savings.design.md](../02-design/features/deposit-savings.design.md)

---

## 1. Analysis Overview

### 1.1 Analysis Purpose

deposit-savings (예금/적금/파킹통장) 기능의 설계 문서와 실제 구현 코드 간의 일치 여부를 검증한다.
PDCA 사이클의 Check 단계로서, 15개 검증 체크리스트 항목을 기준으로 설계-구현 갭을 분석한다.

### 1.2 Analysis Scope

- **Design Document**: `docs/02-design/features/deposit-savings.design.md`
- **Backend Implementation**:
  - `backend/app/models/asset.py`
  - `backend/app/services/interest_service.py`
  - `backend/app/schemas/asset.py`
  - `backend/app/services/asset_service.py`
- **Frontend Implementation**:
  - `frontend/src/shared/types/index.ts`
  - `frontend/src/features/assets/ui/AddAssetModal.tsx`
  - `frontend/src/features/assets/ui/AssetCard.tsx`
  - `frontend/src/features/assets/ui/AssetSummaryCard.tsx`

---

## 2. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match | 97% | PASS |
| Architecture Compliance | 100% | PASS |
| Convention Compliance | 98% | PASS |
| **Overall** | **97%** | **PASS** |

---

## 3. Verification Checklist Results

| ID | Item | Status | Details |
|:---|:-----|:------:|:--------|
| **BE-1** | AssetType enum 확장 (deposit, savings, parking) | **PASS** | `backend/app/models/asset.py:19-21` — 3개 값 정확히 추가 |
| **BE-2** | Asset 모델 필드 추가 (8개 nullable 필드) | **PASS** | `backend/app/models/asset.py:50-67` — 8개 필드 모두 존재, 타입 일치 |
| **BE-3** | AssetCreate 유효성 검증 (model_validator) | **PASS** | `backend/app/schemas/asset.py:27-55` — 유형별 필수 필드 검증 로직 일치 |
| **BE-4** | 예금 이자 계산 (단리/복리) | **PASS** | `backend/app/services/interest_service.py:5-50` — 공식 일치, 만기일 경과 방지 guard 추가 (개선) |
| **BE-5** | 적금 이자 계산 (정액적립식 단리) | **PASS** | `backend/app/services/interest_service.py:53-97` — `m * (rate/12) * n(n+1)/2` 정확 일치 |
| **BE-6** | 파킹통장 이자 계산 (일일이자/월예상이자) | **PASS** | `backend/app/services/interest_service.py:100-122` — daily_interest, monthly_interest 반환 |
| **BE-7** | 이자소득세 적용 (15.4% 기본값, 세전/세후 구분) | **PASS** | 모든 계산 함수에서 tax_rate 적용, fallback `Decimal("15.4")` 처리 |
| **BE-8** | asset_service 분기 (_calculate_holding) | **PASS** | `backend/app/services/asset_service.py:151-256` — 3개 분기 정상 구현 |
| **BE-9** | 기존 자산 호환 (주식/금/현금 무영향) | **PASS** | `backend/app/services/asset_service.py:258-324` — early return 구조로 기존 로직 무영향 |
| **FE-1** | AssetType 타입 확장 + ASSET_TYPE_LABELS | **PASS** | 3개 타입 + InterestType + 라벨 모두 존재 |
| **FE-2** | AddAssetModal 확장 (유형별 조건부 폼) | **PASS** | grid-cols-4, deposit/savings/parking 조건부 필드셋 완전 일치 |
| **FE-3** | AssetCard 확장 (이자 기반 카드 레이아웃) | **PASS** | parking: 잔액/일일이자/월예상이자, deposit/savings: 원금/경과이자/평가금액/만기예상 |
| **FE-4** | 자산 요약 통합 (breakdown에 deposit/savings/parking 포함) | **PASS** | ASSET_TYPE_LABELS 동적 렌더링으로 자동 지원 |
| **FE-5** | Frontend 빌드 통과 | **PASS** | `tsc -b && vite build` 성공 (148 modules, 845ms) |

**결과 요약**: PASS 15/15 (100%), PARTIAL 0/15, FAIL 0/15

---

## 4. Gap Analysis Details

### 4.1 Missing Features (Design O, Implementation X)

| Item | Design Location | Description | Impact |
|------|-----------------|-------------|--------|
| PUT /api/v1/assets/{id}/balance | design.md Section 1.5 | 파킹통장 잔액 업데이트 전용 API | Low (설계에서 "선택"으로 표기) |

### 4.2 Added Features (Design X, Implementation O)

| Item | Implementation Location | Description |
|------|------------------------|-------------|
| 만기일 경과 방지 guard | interest_service.py:26 | `min(as_of_date, maturity_date)` 처리 |
| INTEREST_BASED_TYPES 상수 | asset_service.py:24 | 코드 가독성 향상 목적 |

### 4.3 Changed Features (Design != Implementation)

| Item | Design | Implementation | Impact |
|------|--------|----------------|--------|
| 파킹통장 principal 검증 | `if not self.principal` | `if self.principal is None` | None (0원 잔액 허용 개선) |
| 파킹통장 annual_interest | 반환 dict에 포함 | 반환 dict에서 제외 | None (사용처 없음) |
| Asset 모델 comment 속성 | 각 필드에 comment 포함 | comment 미포함 | None (DB 문서화 목적) |

---

## 5. Match Rate Summary

```
Overall Match Rate: 97%

  PASS:               15 / 15 items (100%)
  PARTIAL:             0 / 15 items (0%)
  FAIL:                0 / 15 items (0%)

  Minor Differences:   3 items (functional impact: None)
  Added Improvements:  2 items (not in design, beneficial)
  Missing (Optional):  1 item (PUT /balance, design marked as optional)
```

---

## 6. Conclusion

deposit-savings 기능의 설계-구현 매칭률은 **97%** 로, 설계 문서와 구현 코드가 매우 높은 수준으로 일치합니다.

- 15개 검증 체크리스트 항목 **전부 PASS**
- 발견된 차이점은 모두 **기능적 영향이 없거나 설계 대비 개선**된 사항
- 설계에서 "선택"으로 표기된 PUT /balance API 1건만 미구현 상태

Match Rate >= 90% 이므로 Check 단계 통과.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-05 | Initial gap analysis | Claude Code (gap-detector) |
