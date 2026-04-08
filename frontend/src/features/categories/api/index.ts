import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import type { Category, CategoryCreate, CategoryUpdate, CategoryDirection } from '@/entities/category/model/types';

const categoryKeys = {
  all: ['categories'] as const,
  list: (direction?: CategoryDirection) => [...categoryKeys.all, 'list', direction] as const,
};

function getErrorMsg(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const resp = (error as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return fallback;
}

export function useCategories(direction?: CategoryDirection) {
  return useQuery({
    queryKey: categoryKeys.list(direction),
    queryFn: async () => {
      const params = direction ? { direction } : {};
      const { data } = await apiClient.get<Category[]>('/v1/categories', { params });
      return data;
    },
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CategoryCreate) => {
      const { data } = await apiClient.post<Category>('/v1/categories', payload);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: categoryKeys.all }); toast.success('카테고리가 생성되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '카테고리 생성 실패')); },
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: CategoryUpdate & { id: string }) => {
      const { data } = await apiClient.patch<Category>(`/v1/categories/${id}`, payload);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: categoryKeys.all }); toast.success('카테고리가 수정되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '카테고리 수정 실패')); },
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => { await apiClient.delete(`/v1/categories/${id}`); },
    onSuccess: () => { qc.invalidateQueries({ queryKey: categoryKeys.all }); toast.success('카테고리가 삭제되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '카테고리 삭제 실패')); },
  });
}

export { categoryKeys };
