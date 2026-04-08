import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import type {
  Account,
  AccountCreate,
  AccountUpdate,
  AccountSummary,
  AdjustBalanceRequest,
} from '@/entities/account/model/types';
import type { Entry } from '@/entities/entry/model/types';

function getErrorMsg(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const resp = (error as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return fallback;
}

const accountKeys = {
  all: ['accounts'] as const,
  list: () => [...accountKeys.all, 'list'] as const,
  detail: (id: string) => [...accountKeys.all, 'detail', id] as const,
  summary: (id: string) => [...accountKeys.all, 'summary', id] as const,
};

export function useAccounts() {
  return useQuery({
    queryKey: accountKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<Account[]>('/v1/accounts');
      return data;
    },
  });
}

export function useAccountDetail(id: string) {
  return useQuery({
    queryKey: accountKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<Account>(`/v1/accounts/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useAccountSummary(id: string) {
  return useQuery({
    queryKey: accountKeys.summary(id),
    queryFn: async () => {
      const { data } = await apiClient.get<AccountSummary>(`/v1/accounts/${id}/summary`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AccountCreate) => {
      const { data } = await apiClient.post<Account>('/v1/accounts', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
      toast.success('계좌가 생성되었습니다');
    },
    onError: (e) => {
      toast.error(getErrorMsg(e, '계좌 생성 실패'));
    },
  });
}

export function useUpdateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: AccountUpdate & { id: string }) => {
      const { data } = await apiClient.patch<Account>(`/v1/accounts/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
      toast.success('계좌가 수정되었습니다');
    },
    onError: (e) => {
      toast.error(getErrorMsg(e, '계좌 수정 실패'));
    },
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/accounts/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
      toast.success('계좌가 삭제되었습니다');
    },
    onError: (e) => {
      toast.error(getErrorMsg(e, '계좌 삭제 실패'));
    },
  });
}

export function useAdjustBalance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: AdjustBalanceRequest & { id: string }) => {
      const { data } = await apiClient.post<Entry>(`/v1/accounts/${id}/adjust`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountKeys.all });
      qc.invalidateQueries({ queryKey: ['entries'] });
      toast.success('잔액이 조정되었습니다');
    },
    onError: (e) => {
      toast.error(getErrorMsg(e, '잔액 조정 실패'));
    },
  });
}

export { accountKeys };
