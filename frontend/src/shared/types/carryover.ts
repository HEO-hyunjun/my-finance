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
