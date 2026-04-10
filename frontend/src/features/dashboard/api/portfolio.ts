import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  AssetTimeline,
  GoalAsset,
  GoalAssetRequest,
} from '@/shared/types/portfolio';

export const portfolioKeys = {
  all: ['portfolio'] as const,
  timeline: (period: string) =>
    [...portfolioKeys.all, 'timeline', period] as const,
  goal: () => [...portfolioKeys.all, 'goal'] as const,
};

export function useAssetTimeline(period: string = '1M') {
  return useQuery({
    queryKey: portfolioKeys.timeline(period),
    queryFn: async () => {
      const { data } = await apiClient.get<AssetTimeline>(
        `/v1/portfolio/timeline?period=${period}`,
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useGoal() {
  return useQuery({
    queryKey: portfolioKeys.goal(),
    queryFn: async () => {
      const { data } = await apiClient.get<GoalAsset | null>(
        '/v1/portfolio/goal',
      );
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
    onSuccess: (data) => {
      queryClient.setQueryData(portfolioKeys.goal(), data);
    },
  });
}
