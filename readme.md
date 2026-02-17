# My Finance — 통합 자산 관리 앱 PRD (v2.0)

> **문서 버전:** v2.6 (6차 피드백 반영)  
> **v2.5 → v2.6 변경사항:** ① 포트폴리오 리밸런싱 기능을 백로그에서 정식 기능(2.3.5)으로 승격 — 목표 비율 설정, 괴리도 분석, AI 시뮬레이션(Analyzer 서브에이전트), 알림 트리거. 데이터 모델(portfolio_targets, rebalancing_alerts), API 엔드포인트(6개), 설정(2.7.5) 추가. ② PWA 모바일 대응 — vite-plugin-pwa(Workbox) 기반 Service Worker, 오프라인 캐싱(Cache-First/Network-First), 홈 화면 설치, 반응형 레이아웃(모바일 단일컬럼/태블릿 2컬럼/데스크톱 사이드바). 프론트엔드 기술 스택 및 인프라 반영

---

## 1. 기획 배경

금, 주식, 미국주식, 가계부, 예산관리 등 다양한 재산 관리 기능이 여러 앱에 산재해 있어 통합 조회가 어려운 문제가 있다. 모든 자산 정보를 한곳에서 관리하고, 현재 재정 상태 분석 및 미래 계획에 대한 AI 기반 조언, 보유 자산 관련 뉴스 요약과 투자 인사이트를 제공하는 통합 앱을 만든다.

### 1.1 핵심 가치 제안

- **통합 조회**: 주식·금·현금·예산을 단일 대시보드에서 확인
- **실시간 추적**: 환율·시세 반영으로 정확한 자산 가치 파악
- **AI 인사이트**: 자산 상태 분석, 뉴스 기반 투자 인사이트, 대화형 상담
- **셀프호스트**: Docker Compose로 어디서든 배포 가능

### 1.2 대상 사용자

- 다양한 자산(국내주식, 미국주식, 금, 현금)을 보유한 개인 투자자
- 월별 예산 관리와 자산 추적을 한곳에서 하고 싶은 사용자
- AI 기반 투자 인사이트에 관심 있는 사용자

---

## 2. 핵심 기능

### 2.1 자산 관리 (Asset Management)

자산의 매수·매도·환전 내역을 기록하고, 현재 시세를 반영한 실시간 자산 가치를 추적한다.

#### 2.1.1 지원 자산 유형

| 자산 유형  | 통화    | 시세 추적   | 비고                      |
| ---------- | ------- | ----------- | ------------------------- |
| 국내 주식  | KRW     | 실시간      | 종목코드 기반             |
| 미국 주식  | USD     | 실시간      | 티커 기반, 환율 자동 적용 |
| 금 (Gold)  | KRW/USD | 실시간      | g/oz 단위 선택            |
| 현금 (KRW) | KRW     | -           | 수동 입력                 |
| 현금 (USD) | USD     | 실시간 환율 | 환전 기록 포함            |

#### 2.1.2 거래 기록 항목

모든 거래에 공통으로 필요한 필드:

- **거래 유형**: 매수(buy) / 매도(sell) / 환전(exchange)
- **자산 유형**: stock_kr / stock_us / gold / cash_krw / cash_usd
- **거래일시**: 과거 날짜 입력 가능 (소급 기록 지원)
- **수량**: 주식 수량 / 금 중량 / 화폐 금액
- **단가**: 거래 시점의 단가 (수동 입력 또는 API 자동 조회)
- **수수료**: 거래 수수료 (선택)
- **환율**: 거래 시점의 USD/KRW 환율 (해외 자산의 경우 자동 기록, 수동 수정 가능)
- **메모**: 자유 텍스트

#### 2.1.3 시세 데이터 소스

**데이터 소스: SerpAPI — Google Finance Engine**

SerpAPI의 `google_finance` 엔진을 통해 주식, 금, 환율 시세를 통합 조회한다. SerpAPI 단일 API 키로 금융 데이터, 뉴스(2.4절), 챗봇 실시간 웹 검색(2.6절)을 모두 처리할 수 있어 외부 의존성을 최소화한다.

| 데이터         | SerpAPI 엔진             | 쿼리 예시                    | 응답 데이터                                              |
| -------------- | ------------------------ | ---------------------------- | -------------------------------------------------------- |
| 미국 주식      | `google_finance`         | `q=TSLA:NASDAQ`              | 현재가, 등락률, 시계열 그래프, 관련 뉴스, 재무제표       |
| 국내 주식      | `google_finance`         | `q=005930:KRX`               | 현재가, 등락률, 시계열 그래프                            |
| 금 시세        | `google_finance`         | `q=GLD:NYSEARCA` 또는 금 ETF | 현재가, 등락률                                           |
| 환율 (USD/KRW) | `google_finance`         | `q=USD-KRW`                  | 현재 환율, 등락폭                                        |
| 시장 동향      | `google_finance_markets` | `trend=indexes`              | 주요 지수, 상승/하락 종목                                |
| 뉴스 검색      | `google_news`            | `q=테슬라 실적`              | 뉴스 기사 목록 (제목, 소스, 날짜, URL)                   |
| 웹 검색        | `google`                 | `q=미국 금리 인상 영향`      | 검색 결과 (organic_results, answer_box, knowledge_graph) |

**Python 연동 예시:**

```python
from serpapi import GoogleSearch

params = {
    "engine": "google_finance",
    "q": "TSLA:NASDAQ",
    "hl": "ko",
    "api_key": os.environ["SERPAPI_KEY"]
}
result = GoogleSearch(params).get_dict()

# 사용 가능한 데이터:
# result["summary"]       — 현재가, 등락률
# result["graph"]          — 시계열 가격 데이터 (1D/5D/1M/6M/YTD/1Y/5Y/MAX)
# result["news_results"]   — 해당 종목 관련 뉴스 (뉴스 기능과 연계 가능)
# result["financials"]     — 재무제표 (income statement, balance sheet, cash flow)
# result["knowledge_graph"] — 기업 정보 요약
```

**시세 갱신 전략:**

- **실시간**: 대시보드 진입 시 또는 사용자 요청 시 조회
- **캐싱**: SerpAPI 자체 1시간 캐시 제공 (캐시 결과는 무료, 크레딧 차감 없음). 추가로 Redis에 5분 캐싱하여 동일 요청 최소화
- **장외 시간**: 마지막 종가 표시, "장 마감" 라벨 노출
- **과거 시세**: `google_finance` 엔진의 `window` 파라미터로 기간별 시계열 조회 (1D/5D/1M/6M/YTD/1Y/5Y/MAX)
- **API 크레딧 관리**: 무료 플랜 월 100건, 유료 플랜 5,000건~. 캐시 적극 활용하여 크레딧 절약

> ⚠️ **크레딧 최적화**: 종목별 시세 조회 시 `google_finance` 결과에 `news_results`가 포함되어 있으므로, 별도의 뉴스 API 호출 없이 시세 조회 한 번으로 해당 종목 뉴스도 함께 수집 가능

#### 2.1.4 자산 요약 뷰

- **총 자산**: 모든 자산의 현재 시세 기준 KRW 환산 합계
- **자산 유형별 합계**: 주식(국내/해외), 금, 현금별 소계
- **총 수익률**: (현재 평가액 - 총 투자금) / 총 투자금 × 100
- **개별 자산 수익률**: 종목별 평균 매입가 대비 현재가 수익률
- **예산 차감 후 가용 자산**: 총 자산 - 이번 달 남은 예산 할당액

---

### 2.2 가계부 & 예산 관리 (Budget Management)

월별 카테고리별 예산을 설정하고, 실제 지출을 기록하여 예산 대비 소비를 추적한다. 고정비·할부금을 별도 관리하며, 미사용 예산은 사용자가 선택한 방식으로 이월한다.

#### 2.2.1 예산 설정

- **월별 총 예산**: 매월 사용 가능한 총 금액
- **카테고리별 예산**: 식비, 교통, 주거, 문화/여가, 쇼핑, 의료, 교육, 저축, 기타 (사용자 커스텀 카테고리 추가 가능)
- **예산 기간**: 월급일 기준 사이클. 예: 급여일이 25일이면 25일~다음달 24일이 한 예산 기간

#### 2.2.2 지출 기록

- **필수 항목**: 날짜, 금액, 카테고리
- **선택 항목**: 메모, 결제수단(현금/카드/이체), 태그
- **반복 지출**: 고정비용에서 자동 차감 (2.2.5 참조)

#### 2.2.3 고정 비용 관리 (Fixed Expenses)

매월 반복되는 고정 지출을 별도로 관리한다. 고정비용은 예산에서 자동 차감되어 실질 가용 예산을 정확히 파악할 수 있다.

- **등록 항목**: 이름, 금액, 결제일(매월 N일), 카테고리, 결제수단
- **유형 예시**: 월세, 관리비, 보험료, 구독서비스(넷플릭스, 스포티파이 등), 통신비
- **자동 차감**: 매월 결제일에 해당 카테고리 지출로 자동 기록 (Celery Beat 스케줄)
- **활성/비활성**: 일시 정지 가능 (is_active 토글)
- **예산 반영**: 월 예산에서 고정비 총합을 선차감하여 "가변 예산"을 별도 표시

```
월 총 예산: 200만원
- 고정비 합계: 80만원 (월세 50 + 보험 15 + 구독 5 + 통신 10)
- 할부금 합계: 30만원 (2.2.4 참조)
= 가변 예산: 90만원 ← 실제 자유롭게 쓸 수 있는 금액
```

#### 2.2.4 할부금 관리 (Installments)

기간이 정해진 분할 결제(할부)를 별도로 추적한다. 할부 완료 시 자동으로 비활성화된다.

- **등록 항목**: 이름, 총 금액, 월 할부금, 결제일(매월 N일), 할부 시작일, 할부 종료일(또는 총 할부 회차), 카테고리
- **유형 예시**: 가전제품 할부, 자동차 할부, 학자금 분납, 카드 할부
- **자동 차감**: 매월 결제일에 해당 카테고리 지출로 자동 기록
- **진행률 추적**: N회차 / 총 M회차, 남은 금액, 완료 예정일
- **완료 처리**: 마지막 회차 결제 후 자동 비활성화, 완료 알림
- **예산 반영**: 고정비와 동일하게 월 예산에서 선차감

#### 2.2.5 예산 이월 정책 (Budget Carryover)

미사용 예산의 처리 방식을 사용자가 카테고리별로 선택한다. 단순 소멸이 아니라, 저축·투자 방향으로 이월하여 자산 증식과 연결한다.

**이월 대상 금액 계산:**

```
이월 가능 금액 = 카테고리 예산 - 해당 카테고리 실 지출
```

**이월 방식 선택지 (카테고리별 개별 설정 가능):**

| 이월 방식              | 설명                                | 설정 항목               |
| ---------------------- | ----------------------------------- | ----------------------- |
| **소멸**               | 미사용 예산 그대로 소멸 (이월 없음) | -                       |
| **다음 달 이월**       | 동일 카테고리의 다음 달 예산에 합산 | 이월 상한액 (선택)      |
| **저축 카테고리 이동** | 저축 카테고리로 자동 이동           | 대상 저축 카테고리 선택 |
| **투자 계좌 이동**     | 특정 투자 방향으로 밀어넣기         | 대상 선택 (아래 상세)   |
| **예금 계좌 이동**     | 특정 예금/적금 계좌로 이동          | 대상 계좌, 연이율 설정  |

**투자 방향 밀어넣기 상세:**

미사용 예산을 다음 투자/저축 대상으로 자동 배분할 수 있다:

| 대상 유형     | 예시                         | 추적 방식                                                                    |
| ------------- | ---------------------------- | ---------------------------------------------------------------------------- |
| **주식**      | 삼성전자 적립식, TSLA 적립식 | 자산관리(2.1)에 매수 예정금으로 누적, 실제 매수는 사용자가 수동 확인 후 실행 |
| **금**        | 금 적립                      | 동일                                                                         |
| **예금/적금** | 특정 은행 계좌               | 계좌명, 연이율 설정 → 이자 수익 자동 계산 표시                               |
| **자유 저축** | 비상금, 여행 자금 등         | 목적별 저축 항목으로 누적                                                    |

**자동 처리 시점:**

- 예산 기간(월급일 기준 사이클) 종료 시 Celery Beat으로 자동 실행
- 이월 내역은 로그로 기록하여 달력(2.5) 및 대시보드(2.3)에서 확인 가능

#### 2.2.6 월급일 전후 예산 전환 관리

월급일을 기준으로 전후 1주(총 2주)를 **예산 전환 기간**으로 설정하여, 이전 달과 다음 달의 예산을 동시에 관리할 수 있다.

**전환 기간 로직:**

```
월급일: 25일 기준

[전환 기간: 18일 ~ 1일(다음달)]
├── 18일~24일 (월급일 전 1주): 이번 달 예산 마감 관리
│   - 남은 예산 강조 표시
│   - 이월 대상 금액 미리보기
│   - "이번 달 마감까지 N일" 알림
│
├── 25일: 월급일 (예산 기간 전환)
│   - 이전 달 예산 이월 자동 실행
│   - 새 예산 기간 시작
│   - 고정비/할부금 새 기간 차감 시작
│
└── 25일~1일 (월급일 후 1주): 새 예산 기간 초기 관리
    - 이월된 금액 확인
    - 새 예산 배분 확인
    - 고정비 차감 현황
```

**UI 동작:**

- 전환 기간 중에는 대시보드와 가계부에 "이전 예산 기간"과 "새 예산 기간"을 탭 또는 토글로 동시 조회 가능
- 전환 기간이 아닐 때는 현재 예산 기간만 표시
- 전환 기간 시작 시 푸시 알림(향후): "예산 마감까지 7일 남았습니다. 남은 예산: XX만원"

#### 2.2.7 예산 분석

- **일별 사용 가능 금액**: (이번 달 남은 가변 예산) ÷ (이번 예산 기간 남은 일수)
- **주별 사용 현황**: 이번 주 사용 금액 / 주간 평균 예산
  - **주간 평균 예산 계산**: 월 수입(급여 등)과 수입일 기준으로 산출. 수입일부터 다음 수입일까지의 기간을 기준으로 주간 가변 예산을 배분한다.
  - 예: 월급일 25일, 월급 300만원, 고정비 80만원, 할부금 30만원 → 가변 예산 190만원 ÷ 약 4.3주 ≈ 주간 약 44.2만원
  - 수입일과 금액은 설정(2.7.2)에서 관리
- **카테고리별 소진율**: 카테고리별 예산 대비 사용 비율 (프로그레스 바)
- **고정비/할부금 차감 현황**: 이번 달 차감 완료 / 예정 목록
- **이월 예측**: 현재 소비 추세 기반 예산 기간 종료 시 예상 이월 금액
- **초과 알림**: 카테고리별 예산의 80%, 100% 도달 시 알림

---

### 2.3 자산 대시보드 (Dashboard)

#### 2.3.1 자산 배분 차트

- **파이/도넛 차트**: 주식(국내/해외), 금, 현금의 전체 자산 대비 비율
- **트리맵**: 개별 종목까지 드릴다운 가능한 자산 구성
- Apache ECharts 사용

#### 2.3.2 시계열 자산 추이

- **기간 선택**: 1주 / 1개월 / 3개월 / 6개월 / 1년 / 전체
- **라인 차트**: 총 자산 가치 변화 (일별/주별/월별 그래뉴얼리티)
- **투자 소스별 분리**: 국내주식, 해외주식, 금, 현금 각각의 자산 변화 추이
- **스냅샷 방식**: 매일 미국 장 마감 후 자동 스냅샷 저장

**스냅샷 타이밍:**

- **기준 시각**: 미국 동부시간(ET) 16:00 (장 마감) + 5분 = **16:05 ET**
- **KST 환산**: 서머타임 적용 시 `06:05 KST (다음날)`, 비적용 시 `07:05 KST (다음날)`
- **이유**: 미국 장 마감 후 최종 종가가 확정된 시점에 스냅샷을 찍어야 해외 주식 포함 전체 자산의 정확한 일일 가치를 기록할 수 있음
- **구현**: Celery Beat cron 스케줄로 매일 지정 시각에 배치 실행
- **휴장일 처리**: 미국 휴장일에도 스냅샷은 저장 (전일 종가 기준), 별도 플래그로 휴장 여부 기록

#### 2.3.3 목표 자산 트래커

- **목표 금액 설정**: 사용자가 목표 순자산 입력
- **달성률**: 현재 자산 / 목표 자산 × 100 (프로그레스 바)
- **예상 달성일**: 최근 N개월 자산 증가 추세 기반 선형 회귀 예측 (numpy)
- **필요 월 저축액**: 목표 달성을 위해 매월 필요한 추가 저축 금액

#### 2.3.4 오늘의 예산 요약

- 오늘 사용한 금액
- 이번 주 사용한 금액
- 이번 달 남은 예산
- 오늘 사용 가능 금액 (남은 예산 ÷ 남은 일수)

#### 2.3.5 포트폴리오 리밸런싱 제안

사용자가 설정한 **목표 자산 배분 비율**과 **현재 실제 비율**을 비교하여 리밸런싱이 필요한 시점과 구체적 행동을 제안한다.

**목표 비율 설정 (Settings → 포트폴리오 목표):**

사용자가 자산 유형별 목표 비율을 직접 설정한다. 합계는 100%여야 한다.

```
예시)
  국내주식: 30%
  해외주식: 40%
  금:       10%
  현금:     20%
  ───────────
  합계:    100%
```

**리밸런싱 분석:**

| 항목            | 설명                                                    |
| --------------- | ------------------------------------------------------- |
| 현재 비율       | `asset_snapshots.breakdown` 기반 실시간 계산            |
| 목표 비율       | `portfolio_targets` 테이블에서 조회                     |
| 괴리도          | 자산 유형별 `                                           |
| 리밸런싱 트리거 | 괴리도가 임계값(기본 5%p) 초과 시 알림                  |
| 구체적 제안     | 초과 자산 "매도 추천 금액" + 부족 자산 "매수 추천 금액" |

**리밸런싱 대시보드 UI:**

```
┌──────────────────────────────────────────────────┐
│  포트폴리오 리밸런싱                               │
│                                                  │
│  자산 유형    목표     현재     괴리    조정 필요    │
│  ─────────  ──────  ──────  ──────  ──────────   │
│  국내주식     30%     22%    -8%p   +₩1,200,000  │
│  해외주식     40%     48%    +8%p   -$600        │
│  금           10%     12%    +2%p   -            │
│  현금         20%     18%    -2%p   -            │
│                                                  │
│  ⚠️ 괴리도 5%p 초과: 국내주식, 해외주식            │
│                                                  │
│  [리밸런싱 시뮬레이션] [임계값 설정] [히스토리]      │
└──────────────────────────────────────────────────┘
```

**리밸런싱 시뮬레이션:**

사용자가 "리밸런싱 시뮬레이션" 버튼을 누르면 AI Analyzer 서브에이전트가 다음을 계산한다:

- 목표 비율에 도달하기 위한 최소 거래 계획 (매수/매도 종목, 수량, 예상 금액)
- 거래 수수료 및 세금 예상 (양도소득세 등)
- 시뮬레이션 결과를 카드 형태로 표시 (실제 거래는 사용자가 직접 수행)

**알림 조건:**

- 괴리도가 임계값(기본 5%p, 사용자 변경 가능) 초과 시 대시보드 배너로 표시
- 일일 스냅샷(2.3.2) 시점에 괴리도 자동 점검
- 환율 급변동(일 2% 이상) 시 해외자산 비중 변동에 대한 추가 알림

> ⚠️ **면책**: 리밸런싱 제안은 정보 제공 목적이며, 투자 권유나 매매 추천이 아닙니다. 실제 투자 결정은 사용자 본인의 판단에 따릅니다.

#### 2.3.6 AI 자산 첨언 — Deep Agent 기반

**아키텍처: LangChain `deepagents` + SubAgent 오케스트레이션**

LangChain의 `deepagents` 라이브러리를 활용하여 메인 Deep Agent가 계획(Planning) → 서브에이전트 위임(Delegation) → 결과 종합의 흐름으로 자산 인사이트를 생성한다. 기존 커스텀 ReAct 구현 대비 계획 도구(`write_todos`), 파일 시스템 기반 컨텍스트 관리, 서브에이전트 컨텍스트 격리가 내장되어 있어 복잡한 멀티스텝 분석에 유리하다.

```
┌──────────────────────────────────────────────────────┐
│            Finance Deep Agent (Orchestrator)          │
│  create_deep_agent()                                 │
│                                                      │
│  Built-in:                                           │
│  ├── write_todos  (계획 수립/업데이트)                  │
│  ├── read_file / write_file (컨텍스트 관리)            │
│  └── task (서브에이전트 호출)                           │
│                                                      │
│  Subagents (via SubAgentMiddleware):                  │
│  ┌──────────────┐ ┌────────────┐ ┌──────────────┐   │
│  │  Researcher  │ │  Analyzer  │ │   Fetcher    │   │
│  │ (뉴스/시장   │ │ (자산분석   │ │ (시세/환율   │   │
│  │  조사)       │ │  예산분석)  │ │  실시간 수집) │   │
│  │              │ │            │ │              │   │
│  │ Tools:       │ │ Tools:     │ │ Tools:       │   │
│  │ · SerpAPI    │ │ · DB 조회  │ │ · SerpAPI    │   │
│  │   google_news│ │ · NumPy    │ │   google_    │   │
│  │ · 뉴스 DB   │ │ · Pandas   │ │   finance    │   │
│  └──────────────┘ └────────────┘ └──────────────┘   │
└──────────────────────────────────────────────────────┘
```

**Deep Agent 실행 흐름:**

```
1. [write_todos] 계획 수립:
   - "환율 확인 필요", "보유 종목 뉴스 확인", "자산 배분 분석", "예산 소진율 확인"

2. [task → Fetcher] 서브에이전트 호출 (컨텍스트 격리):
   - USD/KRW 환율 조회, 보유 종목 시세 조회
   → 결과 반환: "환율 1,380원 (+12), TSLA $248.50 (+2.1%)"

3. [task → Researcher] 서브에이전트 호출 (컨텍스트 격리):
   - 보유 종목 관련 뉴스 검색 및 요약
   → 결과 반환: "테슬라 실적 발표 예정, 시장 반응 엇갈림"

4. [task → Analyzer] 서브에이전트 호출 (컨텍스트 격리):
   - 자산 배분 비율, 예산 소진율, 수익률 추세 분석
   → 결과 반환: "해외주식 65%, 이번달 예산 70% 소진"

5. [write_todos] 계획 업데이트: 모든 항목 완료 체크

6. [write_file] 분석 결과를 파일로 저장 (컨텍스트 오버플로우 방지)

7. Final: 수집된 결과를 종합하여 인사이트 텍스트 생성
```

**서브에이전트 정의 (Python 구현 예시):**

```python
from deepagents import create_deep_agent
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.chat_models import init_chat_model

# --- 커스텀 도구 정의 ---
@tool
def search_finance_news(query: str, symbol: str) -> str:
    """SerpAPI google_news로 금융 뉴스 검색"""
    result = GoogleSearch({
        "engine": "google_news", "q": query,
        "gl": "kr", "hl": "ko",
        "api_key": os.environ["SERPAPI_KEY"]
    }).get_dict()
    return json.dumps(result.get("news_results", [])[:5])

@tool
def web_search(query: str, num: int = 5, recent_days: int | None = None) -> str:
    """SerpAPI google 엔진으로 실시간 웹 검색. 금융 외 일반 질문에도 활용 가능.
    recent_days: 최근 N일 이내 결과만 필터링 (as_qdr 파라미터)"""
    params = {
        "engine": "google", "q": query,
        "gl": "kr", "hl": "ko", "num": num,
        "api_key": os.environ["SERPAPI_KEY"]
    }
    if recent_days:
        params["tbs"] = f"qdr:d{recent_days}"  # 최근 N일 이내 결과
    result = GoogleSearch(params).get_dict()
    organic = result.get("organic_results", [])[:num]
    answer_box = result.get("answer_box")  # Knowledge Graph 즉답
    return json.dumps({"answer_box": answer_box, "results": organic})

@tool
def fetch_stock_price(symbol: str) -> str:
    """SerpAPI google_finance로 종목 시세 조회"""
    result = GoogleSearch({
        "engine": "google_finance", "q": symbol,
        "api_key": os.environ["SERPAPI_KEY"]
    }).get_dict()
    return json.dumps({
        "summary": result.get("summary"),
        "news": result.get("news_results", [])[:3]
    })

@tool
def query_news_db(symbol: str = None, days: int = 3) -> str:
    """DB에 캐시된 뉴스 조회 (배치 수집된 데이터). 실시간 검색 전 1차 조회용."""
    # SQLAlchemy async → news_articles 테이블에서 최근 N일 뉴스 조회
    ...

@tool
def query_user_assets(user_id: str) -> str:
    """사용자 자산/예산 DB 조회 및 분석"""
    # SQLAlchemy async 쿼리 → 자산 배분, 예산 소진율 등 계산
    ...

# --- Deep Agent 구성 ---
finance_agent = create_deep_agent(
    model=init_chat_model(user_settings.default_model),  # LiteLLM 호환
    system_prompt="""
    당신은 개인 자산 관리 AI 어시스턴트입니다.
    사용자의 자산, 예산, 시장 상황을 종합 분석하여 인사이트를 제공합니다.
    투자 권유가 아닌 정보 제공 목적입니다.
    복잡한 분석은 서브에이전트에 위임하세요.
    """,
    subagents=[
        {
            "name": "researcher",
            "description": "보유 종목 관련 뉴스 검색, 시장 동향 조사를 수행. "
                           "DB 캐시 뉴스를 먼저 확인하고, 부족하면 실시간 웹 검색으로 보충",
            "prompt": """금융 뉴스 전문 리서처. 다음 순서로 정보를 수집합니다:
            1) query_news_db로 DB 캐시된 최근 뉴스 먼저 확인
            2) 캐시가 부족하거나 최신 정보가 필요하면 search_finance_news로 뉴스 검색
            3) 더 넓은 맥락이 필요하면 web_search로 일반 웹 검색
            항상 출처 URL을 포함하여 결과를 반환합니다.""",
            "tools": [query_news_db, search_finance_news, web_search],
            "model": user_settings.default_model,
        },
        {
            "name": "analyzer",
            "description": "자산 배분 분석, 예산 소진율 계산, 수익률 추세 분석을 수행",
            "prompt": "금융 데이터 분석 전문가. DB에서 데이터를 조회하고 수치 분석을 수행합니다.",
            "tools": [query_user_assets, numpy_calculate],
            "model": user_settings.default_model,
        },
        {
            "name": "fetcher",
            "description": "실시간 주식 시세, 환율, 시장 지표를 조회",
            "prompt": "실시간 금융 데이터 수집 전문. SerpAPI google_finance로 최신 시세를 가져옵니다.",
            "tools": [fetch_stock_price, fetch_exchange_rate, fetch_market_trends],
            "model": user_settings.default_model,
        },
    ],
)
```

**기존 ReAct 대비 Deep Agent 장점:**

| 항목              | 기존 (커스텀 ReAct)             | Deep Agent                       |
| ----------------- | ------------------------------- | -------------------------------- |
| 계획 수립         | 수동 구현 필요                  | `write_todos` 내장               |
| 서브에이전트 격리 | Tool로 정의, 컨텍스트 공유      | `task` 도구로 컨텍스트 격리 자동 |
| 컨텍스트 관리     | 컨텍스트 윈도우 오버플로우 위험 | 파일 시스템으로 오프로드         |
| 장기 기억         | 별도 구현 필요                  | LangGraph Store 연동 내장        |
| 미들웨어 확장     | 커스텀 코드                     | `AgentMiddleware` 조합           |

**생성되는 인사이트 유형:**

- **자산 배분 첨언**: 현재 비율 평가 및 리밸런싱 제안
- **시장 동향 연계 분석**: 보유 종목 뉴스와 자산 가치 변동의 상관관계
- **예산 경고**: 소진율 기반 지출 패턴 분석
- **환율 리스크 알림**: 해외 자산 보유자를 위한 환율 변동 영향 분석

**운영:**

- 대시보드 진입 시 자동 생성 또는 "인사이트 새로고침" 버튼
- 생성된 인사이트는 캐싱 (기본 1시간, 새로고침 시 갱신)
- LiteLLM을 통해 사용자 설정 모델로 추론

---

### 2.4 뉴스 & 투자 인사이트 (News)

#### 2.4.1 뉴스 수집

**데이터 소스: SerpAPI — Google News Engine + Google Finance News**

SerpAPI의 `google_news` 엔진과 `google_finance` 응답 내 `news_results`를 조합하여 보유 종목 관련 뉴스를 수집한다. 시세 조회(2.1.3)에서 이미 종목별 뉴스가 함께 반환되므로 추가 API 호출을 최소화할 수 있다.

**2가지 뉴스 수집 경로:**

| 경로        | SerpAPI 엔진                      | 용도                              | 비고                                     |
| ----------- | --------------------------------- | --------------------------------- | ---------------------------------------- |
| 종목별 뉴스 | `google_finance` → `news_results` | 보유 종목 관련 뉴스               | 시세 조회 시 자동 포함, 추가 크레딧 없음 |
| 키워드 뉴스 | `google_news`                     | 시장 전반 / 키워드 기반 심층 검색 | 별도 API 호출 (1건 = 1크레딧)            |

**Python 연동 예시:**

```python
# 1) 종목 시세 조회 시 뉴스도 함께 수집 (추가 비용 없음)
finance_result = GoogleSearch({
    "engine": "google_finance",
    "q": "TSLA:NASDAQ",
    "api_key": os.environ["SERPAPI_KEY"]
}).get_dict()
stock_news = finance_result.get("news_results", [])

# 2) 키워드 기반 심층 뉴스 검색 (별도 크레딧)
news_result = GoogleSearch({
    "engine": "google_news",
    "q": "테슬라 실적",
    "gl": "kr",
    "hl": "ko",
    "api_key": os.environ["SERPAPI_KEY"]
}).get_dict()
keyword_news = news_result.get("news_results", [])
```

**수집 전략:**

- **자동 수집 (Celery Beat)**: 매일 09:00, 18:00 KST에 보유 종목별 `google_finance` 조회로 시세 + 뉴스 동시 수집
- **심층 수집**: 주요 이슈 발생 시 또는 사용자 요청 시 `google_news` 엔진으로 키워드 기반 심층 검색
- **크레딧 최적화**: 시세 조회에 포함된 뉴스를 1차로 활용하고, `google_news`는 보조 수단으로만 사용

#### 2.4.2 뉴스 처리 파이프라인

```
SerpAPI 수집 (google_finance + google_news)
  → 중복 제거 (URL 기준)
  → 이슈별 클러스터링
  → LLM 요약 (LangChain summarize chain)
  → 투자 인사이트 생성 (긍정/부정/중립)
```

- **이슈별 클러스터링**: 유사 뉴스를 그룹화하여 이슈 단위로 정리
- **요약**: 이슈별 핵심 내용 3~5문장 요약 (LangChain summarize chain)
- **투자 인사이트**: 보유 자산에 미치는 영향 분석 (긍정/부정/중립 레이블)
- **원문 링크**: 반드시 원본 기사 URL 제공

#### 2.4.3 뉴스 UI

- 종목별 필터링
- 이슈별 카드 뷰 (요약 + 감성 레이블 + 원문 링크)
- "내 자산에 미치는 영향" 섹션

---

### 2.5 달력 (Calendar)

#### 2.5.1 달력 뷰

- **월간 캘린더**: 각 날짜 셀에 요약 정보 표시
- **일별 표시 항목**:
  - 수입 (초록): 급여, 부수입 등
  - 고정 지출 (파랑): 월세, 구독료 등
  - 변동 지출 (빨강): 해당일 총 지출액
  - 투자 거래 (보라): 매수/매도 기록
- **일별 상세**: 날짜 클릭 시 해당일의 모든 거래 내역 리스트

#### 2.5.2 수입 관리

- **급여**: 월 고정 수입 (입금일 설정)
- **부수입**: 비정기 수입 기록
- **투자 수익 실현**: 매도 차익 자동 반영

---

### 2.6 챗봇 (Chatbot)

#### 2.6.1 데이터 조회 전략 — 2-Layer Architecture

챗봇은 **DB 캐시 (Layer 1)** + **실시간 SerpAPI 검색 (Layer 2)** 의 2-레이어 구조로 데이터를 조회한다. 배치로 수집해둔 데이터를 1차로 활용하여 응답 속도와 크레딧을 최적화하고, 부족하거나 최신 정보가 필요할 때만 실시간 검색으로 보충한다.

```
사용자 질문
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ Deep Agent (Orchestrator) — 질문 의도 판단               │
│                                                         │
│ ① 내부 데이터로 충분한가?                                 │
│    YES → Layer 1 (DB 캐시)                              │
│    NO  → Layer 1 + Layer 2 (실시간 검색)                 │
│                                                         │
│ ┌─────────────────────┐  ┌───────────────────────────┐ │
│ │  Layer 1: DB 캐시    │  │  Layer 2: 실시간 SerpAPI  │ │
│ │                     │  │                           │ │
│ │ · 자산/예산 DB      │  │ · google (웹 검색)        │ │
│ │ · 거래 내역 DB      │  │ · google_finance (시세)   │ │
│ │ · 배치 뉴스 DB      │  │ · google_news (뉴스)      │ │
│ │   (09:00/18:00 수집)│  │ · google_finance_markets  │ │
│ │ · 자산 스냅샷 DB    │  │   (시장 동향)             │ │
│ │                     │  │                           │ │
│ │ 응답 속도: 빠름     │  │ 응답 속도: 1~3초          │ │
│ │ 크레딧: 무료        │  │ 크레딧: 1건/호출          │ │
│ └─────────────────────┘  └───────────────────────────┘ │
│                                                         │
│ ② 결과 종합 → 응답 생성 (SSE 스트리밍)                   │
└─────────────────────────────────────────────────────────┘
```

**Layer 전환 판단 기준:**

| 질문 유형                | Layer 1 (DB)              | Layer 2 (실시간)         | 판단 로직                                       |
| ------------------------ | ------------------------- | ------------------------ | ----------------------------------------------- |
| "이번 달 식비 얼마?"     | ✅ expenses DB            | -                        | 내부 데이터만으로 충분                          |
| "테슬라 최근 뉴스"       | ✅ news_articles DB (1차) | ✅ google_news (보충)    | DB 뉴스가 6시간 이내면 DB만, 아니면 실시간 추가 |
| "지금 테슬라 주가 얼마?" | -                         | ✅ google_finance        | 실시간 시세는 항상 Layer 2                      |
| "미국 금리 인상 영향"    | ✅ news_articles DB       | ✅ google (웹 검색)      | 폭넓은 맥락 필요 → 웹 검색                      |
| "반도체 산업 전망은?"    | -                         | ✅ google (웹 검색)      | 보유 종목 외 일반 금융 질문                     |
| "내 자산에 환율 영향"    | ✅ assets + snapshots DB  | ✅ google_finance (환율) | 내부 자산 + 실시간 환율 결합                    |

#### 2.6.2 컨텍스트 구성

챗봇은 2.3.6의 Finance Deep Agent와 동일한 `deepagents` 인프라를 공유하되, 대화형 인터페이스에 최적화된 별도 Deep Agent 인스턴스로 구성한다.

```
[시스템 프롬프트 — create_deep_agent의 system_prompt]
- 역할 정의: 개인 자산 관리 어시스턴트
- 응답 가이드라인: 투자 권유가 아닌 정보 제공 목적 명시 (면책 조항)
- 데이터 조회 전략: DB 캐시 우선, 실시간 검색 보충 (2-Layer 지시)

[사용자 자산 컨텍스트 — Deep Agent 파일 시스템으로 주입]
- 총 자산 요약 (자산 유형별)
- 이번 달 예산 현황
- 최근 거래 내역 (최근 10건)
- 목표 자산 및 달성률

[뉴스 컨텍스트 — Researcher 서브에이전트가 DB 1차 + 실시간 2차로 수집]
- 보유 종목 관련 최신 뉴스 요약 (최근 3일)

[대화 히스토리 — LangGraph 체크포인팅으로 관리]
- 현재 세션의 대화 기록
```

#### 2.6.3 주요 질의 유형 및 데이터 흐름

| 질의 예시                                   | 서브에이전트              | 조회 경로                                        |
| ------------------------------------------- | ------------------------- | ------------------------------------------------ |
| "이번 달 식비 얼마나 썼어?"                 | `Analyzer`                | expenses DB 조회                                 |
| "테슬라 관련 최근 뉴스 알려줘"              | `Researcher`              | news_articles DB → (부족 시) SerpAPI google_news |
| "지금 테슬라 주가 얼마야?"                  | `Fetcher`                 | SerpAPI google_finance (실시간)                  |
| "현재 자산 배분이 적절한지 분석해줘"        | `Analyzer` + `Fetcher`    | assets DB + 실시간 시세                          |
| "3개월 후 목표 달성 가능할까?"              | `Analyzer`                | snapshots DB + NumPy 추세 분석                   |
| "미국 금리 인상이 내 자산에 미치는 영향은?" | `Researcher` + `Analyzer` | SerpAPI google (웹 검색) + assets DB 분석        |
| "반도체 산업 전망 알려줘"                   | `Researcher`              | SerpAPI google (웹 검색)                         |
| "S&P 500 오늘 어때?"                        | `Fetcher`                 | SerpAPI google_finance_markets                   |

#### 2.6.4 구현 방식

```python
# --- 챗봇 전용 Deep Agent ---
chatbot_agent = create_deep_agent(
    model=init_chat_model(user_settings.inference_model),
    system_prompt=CHATBOT_SYSTEM_PROMPT,
    subagents=[
        # Researcher: DB 캐시 뉴스 + 실시간 뉴스 + 실시간 웹 검색
        {
            "name": "researcher",
            "description": "뉴스, 시장 동향, 일반 금융 정보를 조사. "
                           "DB 캐시를 먼저 확인하고 부족하면 실시간 검색 수행",
            "prompt": """금융 리서처. 정보 수집 우선순위:
            1) query_news_db → DB 캐시된 뉴스 (무료, 빠름)
            2) search_finance_news → SerpAPI google_news (실시간 뉴스)
            3) web_search → SerpAPI google (일반 웹 검색, 금융 외 질문에도 활용)
            DB 데이터가 6시간 이내이면 충분히 최신으로 간주.
            항상 출처 URL을 포함하여 결과를 반환합니다.""",
            "tools": [query_news_db, search_finance_news, web_search],
        },
        # Analyzer: 내부 DB 전용 (실시간 검색 불필요)
        {
            "name": "analyzer",
            "description": "자산/예산/거래 데이터 분석, 수치 계산을 수행",
            "prompt": "금융 데이터 분석 전문가. DB 데이터를 조회하고 수치 분석을 수행합니다.",
            "tools": [query_user_assets, query_expenses, query_snapshots, numpy_calculate],
        },
        # Fetcher: 실시간 전용 (DB 캐시 불필요)
        {
            "name": "fetcher",
            "description": "실시간 주식 시세, 환율, 시장 지표를 즉시 조회",
            "prompt": "실시간 금융 데이터 수집 전문. SerpAPI로 최신 시세를 가져옵니다.",
            "tools": [fetch_stock_price, fetch_exchange_rate, fetch_market_trends],
        },
    ],
    tools=[query_chat_history],  # 챗봇 전용 추가 도구
)
```

**SerpAPI 엔진 활용 총정리 (챗봇에서 사용하는 전체 엔진):**

| SerpAPI 엔진             | 서브에이전트 | 용도                                    | 호출 조건                        |
| ------------------------ | ------------ | --------------------------------------- | -------------------------------- |
| `google`                 | Researcher   | 일반 웹 검색 (금리, 산업 전망, 정책 등) | DB에 없는 범용 정보 필요 시      |
| `google_news`            | Researcher   | 키워드 뉴스 실시간 검색                 | DB 뉴스가 오래되었거나 부족할 때 |
| `google_finance`         | Fetcher      | 실시간 종목 시세 + 종목 뉴스            | 현재가 질문, 시세 확인           |
| `google_finance_markets` | Fetcher      | 시장 지수, 상승/하락 종목               | 시장 전반 동향 질문              |

#### 2.6.5 크레딧 최적화 전략

실시간 검색은 SerpAPI 크레딧을 소모하므로 다음 전략으로 비용을 관리한다:

- **DB 캐시 우선 원칙**: 배치 수집된 뉴스(09:00/18:00)와 시세 스냅샷을 1차로 활용. 6시간 이내 데이터는 "최신"으로 간주
- **SerpAPI 캐시 활용**: 동일 쿼리는 SerpAPI 서버에 1시간 캐시되어 무료 재사용 가능
- **Redis 2차 캐시**: 자주 조회되는 시세/검색 결과를 Redis에 5분 캐싱
- **검색 횟수 제한**: 단일 대화 턴에서 실시간 검색은 최대 3회로 제한 (시스템 프롬프트에 명시)
- **`google_finance` 뉴스 재활용**: 시세 조회 시 포함되는 `news_results`를 DB에 저장하여 후속 뉴스 질문에 활용

#### 2.6.6 핵심 포인트

- **서브에이전트 재사용**: 2.3.6 인사이트와 동일한 Researcher/Analyzer/Fetcher를 공유하여 코드 중복 제거
- **모델 분리**: 인사이트는 `default_model`, 챗봇은 `inference_model` (설정에서 별도 선택 가능)
- **컨텍스트 격리**: 서브에이전트 호출 시 `task` 도구로 격리되어 메인 대화 컨텍스트 오염 방지
- **장기 기억**: LangGraph Store를 통해 대화 간 기억 유지 가능 (사용자 선호도, 반복 질문 패턴 등)
- **스트리밍**: LangGraph의 `.stream()` 또는 `.astream()` → SSE 기반 스트리밍 응답
- **실시간성 보장**: 시세·환율은 항상 실시간, 뉴스는 DB 캐시 + 실시간 하이브리드, 범용 질문은 웹 검색으로 커버

---

### 2.7 설정 (Settings)

#### 2.7.1 카테고리 관리

- 지출 카테고리 CRUD (이름, 아이콘/색상)
- 카테고리별 월 예산 금액 설정
- 기본 카테고리 세트 제공 (초기 설정)

#### 2.7.2 수입 & 고정 지출 & 할부 관리

- **수입 설정**: 월 고정 수입 설정 (급여일, 금액), 부수입 등록
- **고정 비용 관리**: 월세, 구독료, 보험, 통신비 등 (이름, 금액, 결제일, 카테고리, 결제수단)
- **할부금 관리**: 할부 항목 등록 (이름, 총 금액, 월 할부금, 회차, 시작일, 카테고리)
- **예산 이월 정책**: 카테고리별 이월 방식 설정 (소멸/다음달이월/저축/투자/예금)
- **예산 기간 설정**: 급여일 기준 예산 사이클 시작일 설정

#### 2.7.3 AI/LLM 설정

- **기본 모델 선택**: 대시보드 인사이트, 뉴스 요약 등에 사용할 기본 모델
- **추론 모델 선택**: 챗봇 대화에 사용할 모델 (별도 설정 가능)
- **API 키 관리**: LLM 제공자별 API 키 입력 (OpenAI, Anthropic, 기타 — LiteLLM 지원 모델)
- **모델 목록 관리**: 사용할 모델 추가/제거

> ⚠️ **보안**: API 키는 서버 사이드에서 암호화 저장. 프론트엔드에 절대 노출 금지.

#### 2.7.4 외부 API 키 관리

- **SerpAPI 키** (필수): 금융 시세(google_finance) + 뉴스(google_news) + 웹 검색(google) 통합 제공
- LLM 제공자 API 키 (2.7.3에서 관리)

#### 2.7.5 포트폴리오 목표 설정

- **자산 유형별 목표 비율**: 국내주식 / 해외주식 / 금 / 현금 비율 입력 (합계 100% 검증)
- **리밸런싱 임계값**: 괴리도 알림 트리거 기준 (기본 5%p, 1~20%p 범위 슬라이더)
- **알림 빈도**: 매일 / 주 1회 / 알림 끄기 선택

#### 2.7.6 일반 설정

- 통화 단위 기본값 (KRW)
- 뉴스 수집 주기
- 다크 모드 / 라이트 모드
- 전환 기간 알림 설정 (ON/OFF)
- **앱 설치 (PWA)**: "홈 화면에 추가" 버튼 (모바일 환경에서 표시)

---

## 3. 사용자 관리 (원본 PRD에서 구체화 필요)

### 3.1 인증 방식

**이메일/비밀번호 (JWT)** 방식을 사용한다.

- 셀프호스트 환경에 적합하며 외부 OAuth 의존성 없음
- JWT Access Token (15분) + Refresh Token (7일)
- 비밀번호는 bcrypt 해싱 후 저장
- 향후 필요 시 OAuth 2.0 확장 가능한 구조로 설계

### 3.2 사용자별 데이터 격리

- 모든 데이터 테이블에 `user_id` FK 포함
- API 레벨에서 사용자별 데이터 접근 제어

---

## 4. 기술 스택

### 4.1 프론트엔드

| 항목            | 기술                         | 비고                                                |
| --------------- | ---------------------------- | --------------------------------------------------- |
| 프레임워크      | React + TypeScript           |                                                     |
| 스타일링        | Tailwind CSS                 | ※ 원본의 "taliswift"는 Tailwind CSS로 해석          |
| 아키텍처        | FSD (Feature-Sliced Design)  |                                                     |
| 차트            | Apache ECharts               |                                                     |
| 상태 관리       | Zustand                      | 경량, 보일러플레이트 최소, FSD 아키텍처와 궁합 좋음 |
| 서버 상태 관리  | TanStack Query (React Query) | API 캐싱, 동기화, 리페칭 전담 (Zustand와 병행 사용) |
| HTTP 클라이언트 | Axios                        | 인터셉터로 JWT 자동 갱신 처리에 유리                |
| 라우팅          | React Router v6+             |                                                     |
| 빌드 도구       | Vite                         |                                                     |
| PWA             | vite-plugin-pwa (Workbox)    | 모바일 대응. Service Worker, 오프라인 캐싱, 앱 설치 |

**PWA (Progressive Web App) 구성:**

웹앱을 PWA로 제공하여 모바일 기기에서도 네이티브에 가까운 사용 경험을 제공한다. 별도 앱스토어 배포 없이 홈 화면 설치가 가능하다.

| PWA 기능         | 구현                                    | 설명                                                         |
| ---------------- | --------------------------------------- | ------------------------------------------------------------ |
| Web App Manifest | `manifest.json`                         | 앱 이름, 아이콘, 테마 컬러, `display: standalone`            |
| Service Worker   | `vite-plugin-pwa` → Workbox             | 정적 자산 프리캐싱 + API 런타임 캐싱                         |
| 오프라인 지원    | Cache-First (정적), Network-First (API) | 오프라인 시 캐시된 대시보드 표시, 온라인 복귀 시 자동 동기화 |
| 앱 설치          | `beforeinstallprompt` 이벤트            | 설정 페이지에 "앱 설치" 버튼 표시                            |
| 반응형 레이아웃  | Tailwind CSS 브레이크포인트             | `sm:` / `md:` / `lg:` 으로 모바일 ↔ 데스크톱 적응형 UI       |
| 터치 최적화      | 모바일 전용 UX                          | 스와이프 네비게이션, 터치 친화적 버튼 크기(48px+)            |

**캐싱 전략 (Workbox):**

```javascript
// vite.config.ts
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "My Finance",
        short_name: "MyFinance",
        theme_color: "#1a1a2e",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            // API 응답: Network First (온라인 우선, 실패 시 캐시)
            urlPattern: /\/api\/v1\/.*/,
            handler: "NetworkFirst",
            options: { cacheName: "api-cache", expiration: { maxAgeSeconds: 300 } },
          },
          {
            // 시세 데이터: Stale While Revalidate (캐시 즉시 반환 + 백그라운드 갱신)
            urlPattern: /\/api\/v1\/market\/.*/,
            handler: "StaleWhileRevalidate",
            options: { cacheName: "market-cache", expiration: { maxAgeSeconds: 60 } },
          },
        ],
      },
    }),
  ],
});
```

**모바일 반응형 레이아웃 기준:**

| 브레이크포인트           | 대상     | 레이아웃                                 |
| ------------------------ | -------- | ---------------------------------------- |
| `< 640px` (sm 미만)      | 모바일   | 단일 컬럼, 하단 탭 네비게이션, 카드형 UI |
| `640px ~ 1024px` (sm~lg) | 태블릿   | 2컬럼, 사이드바 접힘 가능                |
| `> 1024px` (lg 이상)     | 데스크톱 | 사이드바 + 메인 콘텐츠, 현재 디자인 유지 |

### 4.2 백엔드

| 항목              | 기술                                      | 비고                                                                  |
| ----------------- | ----------------------------------------- | --------------------------------------------------------------------- |
| 프레임워크        | FastAPI                                   |                                                                       |
| AI 에이전트       | `deepagents` (LangChain + LangGraph 기반) | `pip install deepagents`. 계획/서브에이전트/파일시스템 내장           |
| LLM 호출          | LiteLLM                                   | 멀티 프로바이더 지원, deepagents의 `init_chat_model`과 호환           |
| 외부 데이터       | SerpAPI (`google-search-results` 패키지)  | 금융 시세 + 뉴스 통합. `pip install google-search-results`            |
| 데이터 처리       | NumPy, Pandas                             | ※ Pandas 추가 권장 (시계열 분석)                                      |
| DB 드라이버 / ORM | SQLAlchemy 2.0 (async) + asyncpg          | FastAPI async와 최적 궁합, 타입 힌트 지원                             |
| 마이그레이션      | Alembic                                   | DB 스키마 버전 관리                                                   |
| 인증              | python-jose (JWT)                         |                                                                       |
| 스케줄링          | Celery + Celery Beat + Redis (broker)     | 뉴스 수집, 시세 스냅샷, 할부 자동 차감 등 배치 작업용. 분산 처리 가능 |

> ※ Celery 선택 이유: 스냅샷, 뉴스 수집, 고정비 자동 차감, 할부금 처리 등 주기적 배치 작업이 다수 존재하며, 향후 사용자 수 증가 시 분산 처리가 필요할 수 있음. Redis를 메시지 브로커로 사용하여 Docker Compose 내 기존 Redis 인스턴스를 재활용.

### 4.3 데이터베이스

| 항목  | 기술         | 비고                 |
| ----- | ------------ | -------------------- |
| RDBMS | PostgreSQL   |                      |
| 캐시  | Redis (선택) | 시세 캐싱, 세션 관리 |

### 4.4 인프라

| 항목          | 기술                      | 비고                    |
| ------------- | ------------------------- | ----------------------- |
| 컨테이너화    | Docker + Docker Compose   |                         |
| 리버스 프록시 | Nginx 또는 Traefik (선택) | HTTPS, 프론트/백 라우팅 |

---

## 5. 데이터 모델 (원본 PRD에 완전 누락 — 추가)

### 5.1 주요 테이블

```
users
├── id (PK, UUID)
├── email (UNIQUE)
├── password_hash
├── name
├── default_currency (default: 'KRW')
├── created_at
└── updated_at

assets
├── id (PK, UUID)
├── user_id (FK → users)
├── asset_type (ENUM: stock_kr, stock_us, gold, cash_krw, cash_usd)
├── symbol (nullable, ex: 'TSLA', '005930')
├── name (ex: '테슬라', '삼성전자')
└── created_at

transactions
├── id (PK, UUID)
├── user_id (FK → users)
├── asset_id (FK → assets)
├── type (ENUM: buy, sell, exchange)
├── quantity (DECIMAL)
├── unit_price (DECIMAL)
├── currency (ENUM: KRW, USD)
├── exchange_rate (DECIMAL, nullable — 해외자산일 때 USD/KRW)
├── fee (DECIMAL, default: 0)
├── memo (TEXT, nullable)
├── transacted_at (TIMESTAMP — 실제 거래일시)
└── created_at

budget_categories
├── id (PK, UUID)
├── user_id (FK → users)
├── name
├── icon (nullable)
├── color (nullable)
├── monthly_budget (DECIMAL)
├── sort_order (INT)
└── is_active (BOOLEAN)

expenses
├── id (PK, UUID)
├── user_id (FK → users)
├── category_id (FK → budget_categories)
├── amount (DECIMAL)
├── memo (TEXT, nullable)
├── payment_method (ENUM: cash, card, transfer)
├── tags (TEXT[], nullable)
├── spent_at (DATE)
└── created_at

incomes
├── id (PK, UUID)
├── user_id (FK → users)
├── type (ENUM: salary, side, investment, other)
├── amount (DECIMAL)
├── description
├── is_recurring (BOOLEAN)
├── recurring_day (INT, nullable — 매월 입금일)
├── received_at (DATE)
└── created_at

fixed_expenses (고정 비용)
├── id (PK, UUID)
├── user_id (FK → users)
├── category_id (FK → budget_categories)
├── name (ex: '넷플릭스', '월세', '통신비')
├── amount (DECIMAL)
├── payment_day (INT — 매월 결제일)
├── payment_method (ENUM: cash, card, transfer)
├── is_active (BOOLEAN, default: true)
├── created_at
└── updated_at

installments (할부금)
├── id (PK, UUID)
├── user_id (FK → users)
├── category_id (FK → budget_categories)
├── name (ex: 'LG 냉장고 할부', '자동차 할부')
├── total_amount (DECIMAL — 총 할부 금액)
├── monthly_amount (DECIMAL — 월 할부금)
├── payment_day (INT — 매월 결제일)
├── total_installments (INT — 총 할부 회차)
├── paid_installments (INT, default: 0 — 납부 완료 회차)
├── start_date (DATE — 할부 시작일)
├── end_date (DATE — 할부 종료 예정일)
├── payment_method (ENUM: cash, card, transfer)
├── is_active (BOOLEAN, default: true — 완료 시 자동 false)
├── created_at
└── updated_at

budget_carryover_settings (카테고리별 이월 설정)
├── id (PK, UUID)
├── user_id (FK → users)
├── category_id (FK → budget_categories, UNIQUE with user_id)
├── carryover_type (ENUM: expire, next_month, savings, investment, deposit)
├── carryover_limit (DECIMAL, nullable — 이월 상한액, next_month일 때 사용)
├── target_asset_id (FK → assets, nullable — investment일 때 대상 자산)
├── target_savings_name (TEXT, nullable — savings/deposit일 때 대상명)
├── target_annual_rate (DECIMAL, nullable — deposit일 때 연이율, ex: 3.5)
├── created_at
└── updated_at

budget_carryover_logs (이월 실행 기록)
├── id (PK, UUID)
├── user_id (FK → users)
├── category_id (FK → budget_categories)
├── budget_period_start (DATE — 이월 원천 예산 기간 시작일)
├── budget_period_end (DATE — 이월 원천 예산 기간 종료일)
├── carryover_type (ENUM: expire, next_month, savings, investment, deposit)
├── amount (DECIMAL — 이월된 금액)
├── target_description (TEXT — 이월 대상 설명)
├── executed_at (TIMESTAMP)
└── created_at

asset_snapshots (시계열 추적용)
├── id (PK, UUID)
├── user_id (FK → users)
├── snapshot_date (DATE, UNIQUE with user_id)
├── total_krw (DECIMAL — 전체 자산 KRW 환산)
├── breakdown (JSONB — { stock_kr: ..., stock_us: ..., gold: ..., cash: ... })
└── created_at

portfolio_targets (포트폴리오 목표 비율)
├── id (PK, UUID)
├── user_id (FK → users)
├── asset_type (ENUM: stock_kr, stock_us, gold, cash_krw, cash_usd)
├── target_ratio (DECIMAL — 목표 비율, ex: 0.30 = 30%)
├── created_at
└── updated_at
※ UNIQUE(user_id, asset_type) — 유저당 자산 유형별 1개 목표
※ 사용자별 전체 target_ratio 합계 = 1.0 (앱 레벨 유효성 검증)

rebalancing_alerts (리밸런싱 알림 기록)
├── id (PK, UUID)
├── user_id (FK → users)
├── snapshot_date (DATE — 트리거된 스냅샷 날짜)
├── deviations (JSONB — { stock_kr: +0.08, stock_us: -0.05, ... })
├── suggestion (JSONB — { buy: [...], sell: [...] } AI 생성 제안)
├── threshold (DECIMAL — 트리거 임계값, ex: 0.05 = 5%p)
├── is_read (BOOLEAN, default: false)
├── created_at
└── updated_at

news_articles
├── id (PK, UUID)
├── source
├── title
├── url (UNIQUE)
├── summary (LLM 생성 요약)
├── sentiment (ENUM: positive, negative, neutral)
├── related_symbols (TEXT[])
├── published_at
├── fetched_at
└── cluster_id (nullable — 이슈 클러스터링용)

chat_sessions
├── id (PK, UUID)
├── user_id (FK → users)
├── title (nullable)
├── created_at
└── updated_at

chat_messages
├── id (PK, UUID)
├── session_id (FK → chat_sessions)
├── role (ENUM: user, assistant, system)
├── content (TEXT)
└── created_at

api_keys (사용자별 외부 API 키)
├── id (PK, UUID)
├── user_id (FK → users)
├── service (ENUM: serpapi, openai, anthropic, google, mistral, custom_llm)
├── encrypted_key (TEXT — 암호화 저장)
└── updated_at

llm_settings
├── id (PK, UUID)
├── user_id (FK → users)
├── default_model (TEXT — ex: 'gpt-4o')
├── inference_model (TEXT — ex: 'claude-sonnet-4-20250514')
└── updated_at
```

### 5.2 인덱스 전략

- `transactions`: `(user_id, transacted_at)` 복합 인덱스
- `expenses`: `(user_id, spent_at)`, `(user_id, category_id, spent_at)` 복합 인덱스
- `asset_snapshots`: `(user_id, snapshot_date)` UNIQUE 복합 인덱스
- `news_articles`: `(related_symbols)` GIN 인덱스, `(published_at)` 인덱스
- `fixed_expenses`: `(user_id, is_active, payment_day)` 복합 인덱스
- `installments`: `(user_id, is_active)` 복합 인덱스, `(end_date)` 인덱스
- `budget_carryover_settings`: `(user_id, category_id)` UNIQUE 복합 인덱스
- `budget_carryover_logs`: `(user_id, budget_period_start)` 복합 인덱스
- `portfolio_targets`: `(user_id, asset_type)` UNIQUE 복합 인덱스
- `rebalancing_alerts`: `(user_id, is_read)` 복합 인덱스, `(snapshot_date)` 인덱스

---

## 6. API 설계 개요 (원본 PRD에 누락 — 추가)

### 6.1 주요 엔드포인트

```
Auth
  POST   /api/v1/auth/register
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh

Assets
  GET    /api/v1/assets                    # 보유 자산 목록
  POST   /api/v1/assets                    # 자산 추가
  GET    /api/v1/assets/{id}               # 자산 상세
  DELETE /api/v1/assets/{id}               # 자산 삭제

Transactions
  GET    /api/v1/transactions              # 거래 내역 (필터: 기간, 자산유형)
  POST   /api/v1/transactions              # 거래 기록
  PUT    /api/v1/transactions/{id}         # 거래 수정
  DELETE /api/v1/transactions/{id}         # 거래 삭제

Budget
  GET    /api/v1/budget/categories         # 카테고리 목록
  POST   /api/v1/budget/categories         # 카테고리 추가
  PUT    /api/v1/budget/categories/{id}    # 카테고리 수정
  GET    /api/v1/budget/summary?period=    # 예산 기간별 요약 (급여일 기준 사이클)
  GET    /api/v1/budget/transition         # 전환 기간 데이터 (이전/새 예산 동시 조회)

Fixed Expenses (고정 비용)
  GET    /api/v1/fixed-expenses            # 고정 비용 목록
  POST   /api/v1/fixed-expenses            # 고정 비용 추가
  PUT    /api/v1/fixed-expenses/{id}       # 고정 비용 수정
  DELETE /api/v1/fixed-expenses/{id}       # 고정 비용 삭제
  PATCH  /api/v1/fixed-expenses/{id}/toggle # 활성/비활성 토글

Installments (할부금)
  GET    /api/v1/installments              # 할부금 목록 (필터: active/completed)
  POST   /api/v1/installments              # 할부금 등록
  PUT    /api/v1/installments/{id}         # 할부금 수정
  DELETE /api/v1/installments/{id}         # 할부금 삭제
  GET    /api/v1/installments/{id}/progress # 할부 진행률 상세

Budget Carryover (이월 정책)
  GET    /api/v1/budget/carryover/settings           # 카테고리별 이월 설정 조회
  PUT    /api/v1/budget/carryover/settings/{cat_id}  # 카테고리별 이월 설정 수정
  GET    /api/v1/budget/carryover/logs               # 이월 실행 기록 조회
  GET    /api/v1/budget/carryover/preview             # 현재 예산 기간 이월 예측

Expenses
  GET    /api/v1/expenses                  # 지출 내역 (필터: 기간, 카테고리)
  POST   /api/v1/expenses                  # 지출 기록
  PUT    /api/v1/expenses/{id}             # 지출 수정
  DELETE /api/v1/expenses/{id}             # 지출 삭제

Dashboard
  GET    /api/v1/dashboard/summary         # 대시보드 요약 데이터
  GET    /api/v1/dashboard/timeline        # 시계열 자산 추이
  GET    /api/v1/dashboard/insight         # AI 자산 인사이트

Portfolio Rebalancing
  GET    /api/v1/portfolio/targets         # 목표 비율 조회
  PUT    /api/v1/portfolio/targets         # 목표 비율 설정/수정 (전체 덮어쓰기)
  GET    /api/v1/portfolio/deviation       # 현재 괴리도 분석 (현재비율 vs 목표비율)
  POST   /api/v1/portfolio/simulate        # 리밸런싱 시뮬레이션 (AI Analyzer → 매수/매도 제안)
  GET    /api/v1/portfolio/alerts          # 리밸런싱 알림 목록
  PATCH  /api/v1/portfolio/alerts/{id}     # 알림 읽음 처리

News
  GET    /api/v1/news                      # 뉴스 목록 (필터: 종목)
  POST   /api/v1/news/refresh              # 뉴스 수동 새로고침

Calendar
  GET    /api/v1/calendar?month=           # 월별 달력 데이터

Market (SerpAPI google_finance 프록시)
  GET    /api/v1/market/price?symbol=      # 실시간 시세 조회 (→ SerpAPI google_finance)
  GET    /api/v1/market/exchange-rate      # 현재 환율 (→ SerpAPI google_finance q=USD-KRW)
  GET    /api/v1/market/trends             # 시장 동향 (→ SerpAPI google_finance_markets)
  GET    /api/v1/market/search?q=          # 실시간 웹 검색 (→ SerpAPI google, 챗봇 에이전트 전용)

Chat
  POST   /api/v1/chat/sessions             # 채팅 세션 생성
  GET    /api/v1/chat/sessions             # 세션 목록
  POST   /api/v1/chat/messages             # 메시지 전송 (SSE 스트리밍)
  GET    /api/v1/chat/sessions/{id}/messages # 세션 메시지 조회

Settings
  GET    /api/v1/settings                  # 전체 설정 조회
  PUT    /api/v1/settings                  # 설정 업데이트
  PUT    /api/v1/settings/api-keys         # API 키 업데이트
  PUT    /api/v1/settings/llm              # LLM 설정 업데이트
```

---

## 7. Docker Compose 구성

```yaml
# docker-compose.yml (예시 구조)
version: "3.8"

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/myfinance
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/1
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - db
      - redis
    env_file:
      - .env

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/myfinance
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis
    env_file:
      - .env

  celery-beat:
    build: ./backend
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - redis
    env_file:
      - .env

  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=myfinance
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

**Celery Beat 스케줄 (주요 배치 작업):**

| 작업             | 스케줄                                   | 설명                                      |
| ---------------- | ---------------------------------------- | ----------------------------------------- |
| 자산 스냅샷      | 매일 06:05 KST (서머타임 시) / 07:05 KST | 미국장 마감+5분 후 실행                   |
| 뉴스 수집        | 매일 09:00, 18:00 KST                    | 보유 종목 기반 뉴스 배치 수집             |
| 고정비 자동 차감 | 매일 00:05 KST                           | 해당일이 결제일인 고정비/할부금 자동 기록 |
| 예산 이월 실행   | 급여일 00:10 KST                         | 사용자별 급여일에 이전 기간 이월 처리     |
| 할부 완료 체크   | 매일 00:15 KST                           | 완료된 할부 자동 비활성화                 |

### 7.1 환경변수 (.env)

```env
# Database
DB_USER=myfinance
DB_PASSWORD=<strong-password>

# Auth
JWT_SECRET=<random-secret>
ENCRYPTION_KEY=<32-byte-key>  # API 키 암호화

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# SerpAPI (금융 시세 + 뉴스 + 웹 검색 통합)
# google_finance, google_finance_markets, google_news, google 엔진 사용
# 무료: 100건/월, 유료: $50/5,000건~ (캐시 결과는 무료)
SERPAPI_KEY=

# LLM (기본값, UI에서 오버라이드 가능)
DEFAULT_LLM_API_KEY=
DEFAULT_LLM_MODEL=gpt-4o
```

---

## 8. 보안 고려사항 (원본 PRD에 누락 — 추가)

| 항목          | 대책                                                                  |
| ------------- | --------------------------------------------------------------------- |
| API 키 저장   | Fernet 대칭 암호화 후 DB 저장, ENCRYPTION_KEY는 환경변수로만 관리     |
| 인증          | JWT Access Token (15분) + Refresh Token (7일), HttpOnly Cookie        |
| CORS          | 프론트엔드 도메인만 허용                                              |
| 입력 검증     | Pydantic 모델로 모든 API 입력 검증                                    |
| SQL Injection | SQLAlchemy ORM 사용으로 방지                                          |
| Rate Limiting | FastAPI 미들웨어로 API 호출 제한                                      |
| 금융 데이터   | 투자 조언이 아닌 정보 제공 목적임을 UI와 챗봇 응답에 명시 (면책 조항) |
