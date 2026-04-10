import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import type { RecurringSchedule, ScheduleCreate, ScheduleUpdate } from '@/entities/schedule/model/types';

function getErrorMsg(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const resp = (error as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return fallback;
}

const scheduleKeys = {
  all: ['schedules'] as const,
  list: () => [...scheduleKeys.all, 'list'] as const,
  detail: (id: string) => [...scheduleKeys.all, 'detail', id] as const,
};

export function useSchedules() {
  return useQuery({
    queryKey: scheduleKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<RecurringSchedule[]>('/v1/schedules');
      return data;
    },
  });
}

export function useScheduleDetail(id: string) {
  return useQuery({
    queryKey: scheduleKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<RecurringSchedule>(`/v1/schedules/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ScheduleCreate) => {
      const { data } = await apiClient.post<RecurringSchedule>('/v1/schedules', payload);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: scheduleKeys.all }); toast.success('반복 일정이 생성되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '반복 일정 생성 실패')); },
  });
}

export function useUpdateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: ScheduleUpdate & { id: string }) => {
      const { data } = await apiClient.patch<RecurringSchedule>(`/v1/schedules/${id}`, payload);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: scheduleKeys.all }); toast.success('반복 일정이 수정되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '반복 일정 수정 실패')); },
  });
}

export function useDeleteSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => { await apiClient.delete(`/v1/schedules/${id}`); },
    onSuccess: () => { qc.invalidateQueries({ queryKey: scheduleKeys.all }); toast.success('반복 일정이 삭제되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '반복 일정 삭제 실패')); },
  });
}

export function useToggleSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post<RecurringSchedule>(`/v1/schedules/${id}/toggle`);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: scheduleKeys.all }); },
    onError: (e) => { toast.error(getErrorMsg(e, '상태 변경 실패')); },
  });
}

export { scheduleKeys };
