"""자산 분석 서브에이전트.

포트폴리오, 보유 자산, 거래 내역, 시세, 리밸런싱을 분석합니다.

TODO: Phase 2 - asset_service, transaction_service를
새 스키마(Account, Entry) 기반 서비스로 교체 예정.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.sub_agent import SubAgent
from app.services.market_service import MarketService


class AssetAgent(SubAgent):
    name = "asset"
    display_name = "자산 분석"
    description = "포트폴리오, 보유 자산, 거래 내역, 시세, 리밸런싱 분석"
    system_prompt = """당신은 자산/포트폴리오 분석 전문가입니다.

## 역할
- 사용자의 보유 자산과 포트폴리오를 분석합니다.
- 거래 내역을 조회하고 패턴을 파악합니다.
- 실시간 시세와 환율 정보를 제공합니다.
- 리밸런싱 필요성을 판단합니다.

## 분석 방법
- 자산 배분 비율과 수익률을 계산합니다.
- 거래 패턴에서 투자 성향을 파악합니다.
- 시장 데이터와 보유 자산을 비교 분석합니다.

## 응답 규칙
- 금액은 ₩ 기호와 천 단위 구분자 사용
- 수익률은 소수점 2자리까지 표시
- 구체적인 수치와 데이터 기반으로 답변
- 결과를 마크다운 테이블로 정리"""

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_asset_summary",
                    "description": "전체 자산 포트폴리오 요약 (총 자산, 수익률, 자산 분포, 개별 보유 현황)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_transactions",
                    "description": "거래 내역 조회 (매수/매도/입금/출금)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset_type": {
                                "type": "string",
                                "description": "자산 유형 필터 (stock_kr, stock_us, gold, cash_krw, cash_usd, deposit, savings, parking)",
                            },
                            "tx_type": {
                                "type": "string",
                                "description": "거래 유형 필터 (buy, sell, deposit, withdraw, exchange)",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "조회 시작일 (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "조회 종료일 (YYYY-MM-DD)",
                            },
                            "per_page": {
                                "type": "integer",
                                "description": "조회 건수 (기본: 20, 최대: 50)",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_market_price",
                    "description": "종목의 실시간 시세 조회 (yfinance 기반)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "종목 심볼 (예: AAPL, 005930.KS, GLD)",
                            },
                        },
                        "required": ["symbol"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_exchange_rate",
                    "description": "USD/KRW 환율 정보 조회",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_rebalancing_analysis",
                    "description": "포트폴리오 리밸런싱 분석 (목표 비율 대비 현재 비율, 편차, 제안)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    async def execute_tool(
        self,
        tool_name: str,
        args: dict,
        db: AsyncSession,
        user_id: uuid.UUID,
        market: MarketService,
    ) -> Any:
        if tool_name == "get_asset_summary":
            # TODO: Phase 2 - rewrite for new schema (Account, Entry)
            return {
                "message": "자산 요약 기능이 새 스키마로 마이그레이션 중입니다. Phase 2에서 복원 예정입니다."
            }

        if tool_name == "get_transactions":
            # TODO: Phase 2 - rewrite for new schema (Entry)
            return {
                "message": "거래 내역 조회 기능이 새 스키마로 마이그레이션 중입니다. Phase 2에서 복원 예정입니다."
            }

        if tool_name == "get_market_price":
            price_data = await market.get_price(args["symbol"], asset_type=None)
            return {
                "symbol": price_data.symbol,
                "name": price_data.name,
                "price": price_data.price,
                "currency": price_data.currency,
                "change": price_data.change,
                "change_percent": price_data.change_percent,
            }

        if tool_name == "get_exchange_rate":
            rate_data = await market.get_exchange_rate()
            return {
                "pair": rate_data.pair,
                "rate": rate_data.rate,
                "change": rate_data.change,
                "change_percent": rate_data.change_percent,
            }

        if tool_name == "get_rebalancing_analysis":
            # TODO: Phase 2 - rewrite for new schema (Account, Entry)
            return {
                "message": "리밸런싱 분석 기능이 새 스키마로 마이그레이션 중입니다. Phase 2에서 복원 예정입니다."
            }

        return {"error": f"Unknown tool: {tool_name}"}
