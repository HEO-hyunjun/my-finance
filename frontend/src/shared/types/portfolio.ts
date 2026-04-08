export interface AssetSnapshotResponse {
  id: string;
  snapshot_date: string;
  total_krw: number;
  breakdown: Record<string, number>;
  created_at: string;
}

export interface AssetTimelineResponse {
  snapshots: AssetSnapshotResponse[];
  period: string;
  start_date: string;
  end_date: string;
}

export interface GoalAssetCreate { target_amount: number; target_date?: string | null; }
export interface GoalAssetUpdate { target_amount?: number | null; target_date?: string | null; }

export interface GoalAssetResponse {
  id: string;
  target_amount: number;
  target_date: string | null;
  current_amount: number;
  achievement_rate: number;
  remaining_amount: number;
  monthly_required: number | null;
  estimated_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PortfolioTargetCreate { asset_type: string; target_ratio: number; }
export interface PortfolioTargetBulkCreate { targets: PortfolioTargetCreate[]; }

export interface PortfolioTargetResponse {
  id: string;
  asset_type: string;
  target_ratio: number;
  current_ratio: number;
  deviation: number;
  created_at: string;
  updated_at: string;
}

export interface RebalancingAnalysisResponse {
  targets: PortfolioTargetResponse[];
  total_deviation: number;
  needs_rebalancing: boolean;
  threshold: number;
  suggestions: Record<string, unknown>[];
}

export interface RebalancingAlertResponse {
  id: string;
  snapshot_date: string;
  deviations: Record<string, number>;
  suggestion: Record<string, unknown>;
  threshold: number;
  is_read: boolean;
  created_at: string;
}

// Backwards-compatible aliases (legacy names)
export type AssetTimeline = AssetTimelineResponse;
export type GoalAsset = GoalAssetResponse;
export type GoalAssetRequest = GoalAssetCreate;
export type PortfolioTarget = PortfolioTargetResponse;
export type PortfolioTargetRequest = PortfolioTargetCreate;
export type RebalancingAnalysis = RebalancingAnalysisResponse;
export type RebalancingAlert = RebalancingAlertResponse;
