import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { NewsListResponse, MyAssetNewsResponse, NewsCategory, NewsClustersResponse } from '@/shared/types';

export const newsKeys = {
  all: ['news'] as const,
  list: (category: NewsCategory, q: string) => [...newsKeys.all, 'list', category, q] as const,
  myAssets: () => [...newsKeys.all, 'my-assets'] as const,
  clusters: (category?: string) => [...newsKeys.all, 'clusters', category ?? 'all'] as const,
};

export function useNewsFeed(category: NewsCategory, q: string = '') {
  return useInfiniteQuery({
    queryKey: newsKeys.list(category, q),
    queryFn: async ({ pageParam = 1 }): Promise<NewsListResponse> => {
      const params = new URLSearchParams({
        category,
        page: String(pageParam),
        per_page: '20',
      });
      if (q) params.set('q', q);
      const { data } = await apiClient.get(`/v1/news?${params.toString()}`);
      return data;
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.has_next ? lastPage.page + 1 : undefined,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMyAssetNews() {
  return useQuery({
    queryKey: newsKeys.myAssets(),
    queryFn: async (): Promise<MyAssetNewsResponse> => {
      const { data } = await apiClient.get('/v1/news/my-assets');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useNewsClusters(category?: string) {
  return useQuery({
    queryKey: newsKeys.clusters(category),
    queryFn: async (): Promise<NewsClustersResponse> => {
      const params = new URLSearchParams();
      if (category && category !== 'all') params.set('category', category);
      const { data } = await apiClient.get(`/v1/news/clusters?${params.toString()}`);
      return data;
    },
    staleTime: 10 * 60 * 1000,
  });
}

export function useTriggerClustering() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (category?: string) => {
      const params = new URLSearchParams();
      if (category && category !== 'all') params.set('category', category);
      const { data } = await apiClient.post(`/v1/news/clusters?${params.toString()}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsKeys.all });
    },
  });
}
