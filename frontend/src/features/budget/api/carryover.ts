import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  CarryoverSetting,
  CarryoverSettingRequest,
  CarryoverPreview,
  CarryoverLog,
} from '@/shared/types';
import { budgetKeys } from './index';

// Query Keys

export const carryoverKeys = {
  all: ['carryover'] as const,
  settings: () => [...carryoverKeys.all, 'settings'] as const,
  preview: (periodStart?: string, periodEnd?: string) =>
    [...carryoverKeys.all, 'preview', periodStart, periodEnd] as const,
  logs: () => [...carryoverKeys.all, 'logs'] as const,
};

// --- Settings Hooks ---

export function useCarryoverSettings() {
  return useQuery({
    queryKey: carryoverKeys.settings(),
    queryFn: async () => {
      const { data } = await apiClient.get<CarryoverSetting[]>(
        '/v1/budget/carryover/settings',
      );
      return data;
    },
  });
}

export function useUpsertCarryoverSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CarryoverSettingRequest) => {
      const { data: result } = await apiClient.post<CarryoverSetting>(
        '/v1/budget/carryover/settings',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: carryoverKeys.settings() });
      queryClient.invalidateQueries({ queryKey: carryoverKeys.all });
    },
  });
}

// --- Preview Hook ---

export interface CarryoverPreviewFilters {
  periodStart?: string;
  periodEnd?: string;
}

export function useCarryoverPreview(filters: CarryoverPreviewFilters = {}) {
  return useQuery({
    queryKey: carryoverKeys.preview(filters.periodStart, filters.periodEnd),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.periodStart)
        params.append('period_start', filters.periodStart);
      if (filters.periodEnd) params.append('period_end', filters.periodEnd);
      const { data } = await apiClient.get<CarryoverPreview[]>(
        `/v1/budget/carryover/preview?${params.toString()}`,
      );
      return data;
    },
    enabled: !!filters.periodStart && !!filters.periodEnd,
  });
}

// --- Execute Hook ---

export function useExecuteCarryover() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post('/v1/budget/carryover/execute');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: carryoverKeys.all });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
    },
  });
}

// --- Logs Hook ---

export function useCarryoverLogs() {
  return useQuery({
    queryKey: carryoverKeys.logs(),
    queryFn: async () => {
      const { data } = await apiClient.get<CarryoverLog[]>(
        '/v1/budget/carryover/logs',
      );
      return data;
    },
  });
}
