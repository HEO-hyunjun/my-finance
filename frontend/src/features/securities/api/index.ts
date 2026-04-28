import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  SecuritySearchResult,
  SecurityEnsureResult,
} from '@/entities/security/model/types';

const securityKeys = {
  all: ['securities'] as const,
  search: (q: string) => [...securityKeys.all, 'search', q] as const,
};

export function useSearchSecurities(query: string) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: securityKeys.search(trimmed),
    queryFn: async () => {
      const { data } = await apiClient.get<SecuritySearchResult[]>(
        '/v1/securities/search',
        { params: { q: trimmed, limit: 20 } },
      );
      return data;
    },
    enabled: trimmed.length >= 1,
    staleTime: 30 * 1000,
  });
}

export function useEnsureSecurity() {
  return useMutation({
    mutationFn: async (symbol: string) => {
      const { data } = await apiClient.post<SecurityEnsureResult>(
        '/v1/securities/ensure',
        { symbol },
      );
      return data;
    },
  });
}

export { securityKeys };
