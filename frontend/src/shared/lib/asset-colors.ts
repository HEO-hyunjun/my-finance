import type { AssetType } from '@/shared/types/common';

export const DEFAULT_ASSET_TYPE_COLORS: Partial<Record<AssetType, string>> & Record<string, string> = {
  stock_kr: '#3B82F6',
  stock_us: '#8B5CF6',
  gold: '#F59E0B',
  cash_krw: '#10B981',
  cash_usd: '#06B6D4',
  deposit: '#6366F1',
  savings: '#EC4899',
  parking: '#84CC16',
};

export function getAssetTypeColors(
  userColors?: Record<string, string>,
): Record<string, string> {
  if (!userColors) return { ...DEFAULT_ASSET_TYPE_COLORS };
  return { ...DEFAULT_ASSET_TYPE_COLORS, ...userColors };
}
