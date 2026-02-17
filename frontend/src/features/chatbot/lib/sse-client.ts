import type { ChatSSEEvent } from '@/shared/types';

interface SSEOptions {
  onToken: (content: string) => void;
  onDone: (conversationId: string, messageId: string) => void;
  onError: (message: string) => void;
}

export async function streamChat(
  message: string,
  conversationId: string | null,
  options: SSEOptions,
): Promise<void> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    options.onError('로그인이 필요합니다.');
    return;
  }

  let response: Response;
  try {
    response = await fetch('/api/v1/chatbot/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
  } catch {
    options.onError('서버 연결에 실패했습니다.');
    return;
  }

  if (!response.ok) {
    options.onError('서버 연결에 실패했습니다.');
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    options.onError('스트리밍을 시작할 수 없습니다.');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: ChatSSEEvent = JSON.parse(line.slice(6));
            switch (event.type) {
              case 'token':
                options.onToken(event.content);
                break;
              case 'done':
                options.onDone(event.conversation_id, event.message_id);
                return;
              case 'error':
                options.onError(event.message);
                return;
            }
          } catch {
            // JSON 파싱 실패 무시
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
