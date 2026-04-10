import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  CarryoverSettingResponse as CarryoverSetting,
  CarryoverSettingCreate as CarryoverSettingRequest,
} from '@/shared/types/carryover';

export const carryoverKeys = {
  all: ['carryover'] as const,
  settings: () => [...carryoverKeys.all, 'settings'] as const,
};

export function useCarryoverSettings() {
  return useQuery({
    queryKey: carryoverKeys.settings(),
    queryFn: async () => {
      const { data } = await apiClient.get<CarryoverSetting[]>(
        '/v1/carryover/settings',
      );
      return data;
    },
  });
}

export function useUpsertCarryoverSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CarryoverSettingRequest) => {
      const { data: result } = await apiClient.put<CarryoverSetting>(
        '/v1/carryover/settings',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: carryoverKeys.settings() });
    },
  });
}
