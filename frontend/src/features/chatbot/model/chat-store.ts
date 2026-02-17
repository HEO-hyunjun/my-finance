import { create } from 'zustand';
import type { ChatMessage } from '@/shared/types';

interface ChatState {
  conversationId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;

  setConversationId: (id: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addUserMessage: (content: string) => void;
  startStreaming: () => void;
  appendStreamToken: (token: string) => void;
  finishStreaming: (messageId: string) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',

  setConversationId: (id) => set({ conversationId: id }),

  setMessages: (messages) => set({ messages }),

  addUserMessage: (content) => {
    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    set((state) => ({ messages: [...state.messages, userMsg] }));
  },

  startStreaming: () => set({ isStreaming: true, streamingContent: '' }),

  appendStreamToken: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),

  finishStreaming: (messageId) => {
    const { streamingContent, messages } = get();
    const aiMsg: ChatMessage = {
      id: messageId,
      role: 'assistant',
      content: streamingContent,
      created_at: new Date().toISOString(),
    };
    set({
      messages: [...messages, aiMsg],
      isStreaming: false,
      streamingContent: '',
    });
  },

  clearChat: () =>
    set({
      conversationId: null,
      messages: [],
      isStreaming: false,
      streamingContent: '',
    }),
}));
