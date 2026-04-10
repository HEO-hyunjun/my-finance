export type CarryoverType = 'expire' | 'next_month' | 'savings' | 'transfer' | 'deposit';

export interface CarryoverSettingCreate {
  category_id: string;
  carryover_type: CarryoverType;
  carryover_limit?: number | null;
  source_asset_id?: string | null;
  target_asset_id?: string | null;
  target_savings_name?: string | null;
  target_annual_rate?: number | null;
}

export interface CarryoverSettingResponse {
  id: string;
  category_id: string;
  category_name: string;
  carryover_type: CarryoverType;
  carryover_limit: number | null;
  source_asset_id: string | null;
  source_asset_name: string | null;
  target_asset_id: string | null;
  target_savings_name: string | null;
  target_annual_rate: number | null;
  created_at: string;
  updated_at: string;
}

export interface CarryoverPreview {
  category_id: string;
  category_name: string;
  remaining_budget: number;
  carryover_type: CarryoverType;
  carryover_limit: number | null;
  target_asset_id: string | null;
  target_savings_name: string | null;
  target_annual_rate: number | null;
  source_asset_id: string | null;
  estimated_transfer_amount: number | null;
}

export interface CarryoverLog {
  id: string;
  period_start: string;
  period_end: string;
  category_id: string;
  category_name: string;
  carryover_type: CarryoverType;
  remaining_budget: number;
  transferred_amount: number | null;
  target_asset_id: string | null;
  target_savings_name: string | null;
  status: string;
  executed_at: string;
  created_at: string;
}

// Backwards-compatible aliases (legacy names)
export type CarryoverSetting = CarryoverSettingResponse;
export type CarryoverSettingRequest = CarryoverSettingCreate;
export const CARRYOVER_TYPE_LABELS: Record<CarryoverType, string> = {
  expire: '소멸',
  next_month: '다음달 이월',
  savings: '적금 저축',
  transfer: '계좌 이체',
  deposit: '예금 저축',
};
