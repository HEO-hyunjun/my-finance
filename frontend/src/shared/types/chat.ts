export type ChatMessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  last_message_at: string | null;
  message_count: number;
}

export interface ConversationDetailResponse {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
  agent_state: Record<string, unknown> | null;
  summary: string | null;
  total_tokens: number;
}

export interface ChatTokenEvent { type: 'token'; content: string; }
export interface ChatDoneEvent { type: 'done'; conversation_id: string; message_id: string; }
export interface ChatAgentEvent { type: 'agent'; name: string; status: 'started' | 'done'; }
export interface ChatToolEvent { type: 'tool'; agent: string; name: string; status: 'calling' | 'done' | 'error'; }
export interface ChatGeneratingEvent { type: 'generating'; }
export interface ChatErrorEvent { type: 'error'; message: string; }

export type ChatSSEEvent =
  | ChatTokenEvent | ChatDoneEvent | ChatAgentEvent
  | ChatToolEvent | ChatGeneratingEvent | ChatErrorEvent;

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}
