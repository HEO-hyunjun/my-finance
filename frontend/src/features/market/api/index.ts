import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import type {
  PriceResponse, ExchangeRateResponse, MarketTrendsResponse,
  MarketSearchResponse, RefreshPriceRequest,
} from '@/shared/types/market';

function getErrorMsg(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const resp = (error as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return fallback;
}

const marketKeys = {
  all: ['market'] as const,
  price: (symbol: string, exchange?: string) => [...marketKeys.all, 'price', symbol, exchange] as const,
  exchangeRate: () => [...marketKeys.all, 'exchangeRate'] as const,
  trends: () => [...marketKeys.all, 'trends'] as const,
  search: (query: string) => [...marketKeys.all, 'search', query] as const,
};

export function useMarketPrice(symbol: string, exchange?: string) {
  return useQuery({
    queryKey: marketKeys.price(symbol, exchange),
    queryFn: async () => {
      const { data } = await apiClient.get<PriceResponse>('/v1/market/price', { params: { symbol, exchange } });
      return data;
    },
    enabled: !!symbol,
    staleTime: 60 * 1000,
  });
}

export function useExchangeRate() {
  return useQuery({
    queryKey: marketKeys.exchangeRate(),
    queryFn: async () => {
      const { data } = await apiClient.get<ExchangeRateResponse>('/v1/market/exchange-rate');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useMarketTrends() {
  return useQuery({
    queryKey: marketKeys.trends(),
    queryFn: async () => {
      const { data } = await apiClient.get<MarketTrendsResponse>('/v1/market/trends');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useSearchSecurity(query: string) {
  return useQuery({
    queryKey: marketKeys.search(query),
    queryFn: async () => {
      const { data } = await apiClient.get<MarketSearchResponse>('/v1/market/search', { params: { query } });
      return data;
    },
    enabled: query.length >= 2,
  });
}

export function useRefreshPrice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RefreshPriceRequest) => {
      const { data } = await apiClient.post<PriceResponse>('/v1/market/refresh-price', payload);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: marketKeys.all }); toast.success('시세가 갱신되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '시세 갱신 실패')); },
  });
}

export function useRefreshExchangeRate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => { const { data } = await apiClient.post('/v1/market/refresh-exchange-rate'); return data; },
    onSuccess: () => { qc.invalidateQueries({ queryKey: marketKeys.exchangeRate() }); },
  });
}

export function useRefreshAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => { const { data } = await apiClient.post('/v1/market/refresh-all'); return data; },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketKeys.all });
      qc.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('전체 시세가 갱신되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '시세 갱신 실패')); },
  });
}

export { marketKeys };
