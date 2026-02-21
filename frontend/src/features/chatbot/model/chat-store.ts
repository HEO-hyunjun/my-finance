import { create } from 'zustand';
import type { ChatMessage } from '@/shared/types';

interface AgentStatus {
  name: string;
  status: 'started' | 'done';
}

interface ChatState {
  conversationId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  activeAgents: AgentStatus[];

  setConversationId: (id: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addUserMessage: (content: string) => void;
  startStreaming: () => void;
  appendStreamToken: (token: string) => void;
  finishStreaming: (messageId: string) => void;
  updateAgent: (name: string, status: 'started' | 'done') => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  activeAgents: [],

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

  startStreaming: () =>
    set({ isStreaming: true, streamingContent: '', activeAgents: [] }),

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
      activeAgents: [],
    });
  },

  updateAgent: (name, status) =>
    set((state) => {
      if (status === 'started') {
        return {
          activeAgents: [...state.activeAgents, { name, status }],
        };
      }
      // done → 해당 에이전트 상태 업데이트
      return {
        activeAgents: state.activeAgents.map((a) =>
          a.name === name ? { ...a, status: 'done' } : a,
        ),
      };
    }),

  clearChat: () =>
    set({
      conversationId: null,
      messages: [],
      isStreaming: false,
      streamingContent: '',
      activeAgents: [],
    }),
}));
