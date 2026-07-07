import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import { invalidateEntryRelated } from '@/features/entries/api';
import type {
  ImportBatch, ImportDetail, StagedEntry, StagedEntryUpdate, ImportCommitResponse,
} from '@/entities/import/model/types';

function getErrorMsg(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const resp = (error as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return fallback;
}

const IN_PROGRESS = new Set(['uploaded', 'parsing']);

export const importKeys = {
  all: ['imports'] as const,
  list: () => [...importKeys.all, 'list'] as const,
  detail: (id: string) => [...importKeys.all, 'detail', id] as const,
};

export function useImports() {
  return useQuery({
    queryKey: importKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<ImportBatch[]>('/v1/imports');
      return data;
    },
    // 분석 중인 배치가 있으면 자동 폴링
    refetchInterval: (query) => {
      const batches = query.state.data as ImportBatch[] | undefined;
      return batches?.some((b) => IN_PROGRESS.has(b.status)) ? 3000 : false;
    },
  });
}

export function useImportDetail(id: string | null) {
  return useQuery({
    queryKey: importKeys.detail(id ?? ''),
    queryFn: async () => {
      const { data } = await apiClient.get<ImportDetail>(`/v1/imports/${id}`);
      return data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const detail = query.state.data as ImportDetail | undefined;
      return detail && IN_PROGRESS.has(detail.batch.status) ? 2500 : false;
    },
  });
}

export function useCreateImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { file: File; accountId?: string; password?: string }) => {
      const form = new FormData();
      form.append('file', payload.file);
      if (payload.accountId) form.append('account_id', payload.accountId);
      if (payload.password) form.append('password', payload.password);
      const { data } = await apiClient.post<ImportBatch>('/v1/imports', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: importKeys.list() });
      toast.success('파일이 업로드되었습니다. 분석을 시작합니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '업로드 실패')); },
  });
}

export function useUpdateRow(batchId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ rowId, ...payload }: StagedEntryUpdate & { rowId: string }) => {
      const { data } = await apiClient.patch<StagedEntry>(
        `/v1/imports/${batchId}/rows/${rowId}`, payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: importKeys.detail(batchId) });
    },
    onError: (e) => { toast.error(getErrorMsg(e, '행 수정 실패')); },
  });
}

export function useCommitImport(batchId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (createAdjustment: boolean) => {
      const { data } = await apiClient.post<ImportCommitResponse>(
        `/v1/imports/${batchId}/commit`,
        null,
        { params: { create_adjustment: createAdjustment } },
      );
      return data;
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: importKeys.all });
      invalidateEntryRelated(qc);
      toast.success(
        `${res.committed_count}건이 반영되었습니다${res.adjustment_created ? ' (보정 거래 포함)' : ''}`,
      );
    },
    onError: (e) => { toast.error(getErrorMsg(e, '커밋 실패')); },
  });
}

export function useDeleteImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => { await apiClient.delete(`/v1/imports/${id}`); },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: importKeys.list() });
      toast.success('배치가 삭제되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '삭제 실패')); },
  });
}
