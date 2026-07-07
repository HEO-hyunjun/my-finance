// Phase 2 자산 분류 도메인 (백엔드 get_asset_breakdown 기준)
export const ASSET_CLASSES = ['cash', 'deposit', 'equity_kr', 'equity_us', 'commodity'] as const;

export type AssetClass = (typeof ASSET_CLASSES)[number];

export const ASSET_CLASS_LABELS: Record<string, string> = {
  cash: '현금',
  deposit: '예금',
  equity_kr: '국내주식',
  equity_us: '미국주식',
  commodity: '원자재',
};

// 마이그레이션이 구 investment 타깃을 이 센티넬로 치환 — UI에서 재설정 유도
export const NEEDS_RESET_SENTINEL = '__needs_reset__';
