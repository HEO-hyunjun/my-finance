import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  ConversationListResponse,
  ConversationDetailResponse,
} from '@/shared/types/chat';

export const chatbotKeys = {
  all: ['chatbot'] as const,
  conversations: () => [...chatbotKeys.all, 'conversations'] as const,
  conversation: (id: string) => [...chatbotKeys.all, 'conversation', id] as const,
};

export function useConversations() {
  return useQuery({
    queryKey: chatbotKeys.conversations(),
    queryFn: async (): Promise<ConversationListResponse> => {
      const { data } = await apiClient.get('/v1/chatbot/conversations');
      return data;
    },
  });
}

export function useConversationDetail(id: string | null) {
  return useQuery({
    queryKey: chatbotKeys.conversation(id || ''),
    queryFn: async (): Promise<ConversationDetailResponse> => {
      const { data } = await apiClient.get(`/v1/chatbot/conversations/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/chatbot/conversations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chatbotKeys.conversations() });
    },
  });
}
