import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  UserProfile,
  ProfileUpdateRequest,
  PasswordChangeRequest,
  NotificationPreferences,
  AccountDeleteRequest,
} from '@/shared/types';

export const userKeys = {
  all: ['user'] as const,
  profile: () => [...userKeys.all, 'profile'] as const,
};

export function useProfile() {
  return useQuery({
    queryKey: userKeys.profile(),
    queryFn: async (): Promise<UserProfile> => {
      const { data } = await apiClient.get('/v1/users/me');
      return data;
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: ProfileUpdateRequest): Promise<UserProfile> => {
      const { data } = await apiClient.patch('/v1/users/me', body);
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(userKeys.profile(), data);
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (body: PasswordChangeRequest) => {
      const { data } = await apiClient.put('/v1/users/me/password', body);
      return data;
    },
  });
}

export function useUpdateNotifications() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      body: NotificationPreferences,
    ): Promise<NotificationPreferences> => {
      const { data } = await apiClient.patch(
        '/v1/users/me/notifications',
        body,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.profile() });
    },
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: async (body: AccountDeleteRequest) => {
      const { data } = await apiClient.delete('/v1/users/me', { data: body });
      return data;
    },
  });
}
