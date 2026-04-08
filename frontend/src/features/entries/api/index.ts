import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import type {
  Entry, EntryCreate, EntryUpdate, EntryListResponse,
  TransferRequest, TradeRequest, EntryFilters,
} from '@/entities/entry/model/types';

function getErrorMsg(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const resp = (error as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return fallback;
}

const entryKeys = {
  all: ['entries'] as const,
  list: (filters?: EntryFilters) => [...entryKeys.all, 'list', filters] as const,
  detail: (id: string) => [...entryKeys.all, 'detail', id] as const,
};

export function useEntries(filters?: EntryFilters) {
  return useQuery({
    queryKey: entryKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.account_id) params.set('account_id', filters.account_id);
      if (filters?.type) params.set('type', filters.type);
      if (filters?.category_id) params.set('category_id', filters.category_id);
      if (filters?.start_date) params.set('start_date', filters.start_date);
      if (filters?.end_date) params.set('end_date', filters.end_date);
      if (filters?.page) params.set('page', String(filters.page));
      if (filters?.per_page) params.set('per_page', String(filters.per_page));
      const { data } = await apiClient.get<EntryListResponse>('/v1/entries', { params });
      return data;
    },
  });
}

export function useEntryDetail(id: string) {
  return useQuery({
    queryKey: entryKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<Entry>(`/v1/entries/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: EntryCreate) => {
      const { data } = await apiClient.post<Entry>('/v1/entries', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: entryKeys.all });
      qc.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('거래가 기록되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '거래 기록 실패')); },
  });
}

export function useUpdateEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: EntryUpdate & { id: string }) => {
      const { data } = await apiClient.patch<Entry>(`/v1/entries/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: entryKeys.all });
      qc.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('거래가 수정되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '거래 수정 실패')); },
  });
}

export function useDeleteEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => { await apiClient.delete(`/v1/entries/${id}`); },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: entryKeys.all });
      qc.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('거래가 삭제되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '거래 삭제 실패')); },
  });
}

export function useTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: TransferRequest) => {
      const { data } = await apiClient.post<Entry[]>('/v1/entries/transfer', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: entryKeys.all });
      qc.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('이체가 완료되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '이체 실패')); },
  });
}

export function useTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: TradeRequest) => {
      const { data } = await apiClient.post<Entry[]>('/v1/entries/trade', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: entryKeys.all });
      qc.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('매매가 완료되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '매매 실패')); },
  });
}

export { entryKeys };
