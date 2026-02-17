import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  AssetTimeline,
  GoalAsset,
  GoalAssetRequest,
  PortfolioTarget,
  PortfolioTargetRequest,
  RebalancingAnalysis,
  RebalancingAlert,
} from '@/shared/types';

// Query Keys

export const portfolioKeys = {
  all: ['portfolio'] as const,
  timeline: (period?: string) =>
    [...portfolioKeys.all, 'timeline', period] as const,
  goal: () => [...portfolioKeys.all, 'goal'] as const,
  targets: () => [...portfolioKeys.all, 'targets'] as const,
  rebalancing: (threshold?: number) =>
    [...portfolioKeys.all, 'rebalancing', threshold] as const,
  alerts: (unreadOnly?: boolean) =>
    [...portfolioKeys.all, 'alerts', unreadOnly] as const,
};

// --- Timeline Hook ---

export function useAssetTimeline(period?: string) {
  return useQuery({
    queryKey: portfolioKeys.timeline(period),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (period) params.append('period', period);
      const { data } = await apiClient.get<AssetTimeline>(
        `/v1/portfolio/timeline?${params.toString()}`,
      );
      return data;
    },
  });
}

// --- Snapshot Hook ---

export function useCreateSnapshot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post('/v1/portfolio/snapshot');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.timeline() });
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all });
    },
  });
}

// --- Goal Hooks ---

export function useGoal() {
  return useQuery({
    queryKey: portfolioKeys.goal(),
    queryFn: async () => {
      const { data } = await apiClient.get<GoalAsset>('/v1/portfolio/goal');
      return data;
    },
  });
}

export function useSetGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: GoalAssetRequest) => {
      const { data: result } = await apiClient.put<GoalAsset>(
        '/v1/portfolio/goal',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.goal() });
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all });
    },
  });
}

// --- Portfolio Targets Hooks ---

export function usePortfolioTargets() {
  return useQuery({
    queryKey: portfolioKeys.targets(),
    queryFn: async () => {
      const { data } = await apiClient.get<PortfolioTarget[]>(
        '/v1/portfolio/targets',
      );
      return data;
    },
  });
}

export function useSetPortfolioTargets() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PortfolioTargetRequest[]) => {
      const { data: result } = await apiClient.put<PortfolioTarget[]>(
        '/v1/portfolio/targets',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.targets() });
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all });
    },
  });
}

// --- Rebalancing Hook ---

export function useRebalancingAnalysis(threshold?: number) {
  return useQuery({
    queryKey: portfolioKeys.rebalancing(threshold),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (threshold !== undefined) params.append('threshold', String(threshold));
      const { data } = await apiClient.get<RebalancingAnalysis>(
        `/v1/portfolio/rebalancing?${params.toString()}`,
      );
      return data;
    },
  });
}

// --- Alerts Hooks ---

export function useRebalancingAlerts(unreadOnly?: boolean) {
  return useQuery({
    queryKey: portfolioKeys.alerts(unreadOnly),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (unreadOnly !== undefined)
        params.append('unread_only', String(unreadOnly));
      const { data } = await apiClient.get<RebalancingAlert[]>(
        `/v1/portfolio/alerts?${params.toString()}`,
      );
      return data;
    },
  });
}

export function useMarkAlertRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.patch<RebalancingAlert>(
        `/v1/portfolio/alerts/${id}/read`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.alerts() });
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all });
    },
  });
}
