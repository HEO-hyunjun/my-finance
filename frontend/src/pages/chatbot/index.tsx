import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Bot, Menu } from 'lucide-react';
import {
  useConversations,
  useConversationDetail,
  useDeleteConversation,
  chatbotKeys,
} from '@/features/chatbot/api';
import { useChatStore } from '@/features/chatbot/model/chat-store';
import { streamChat } from '@/features/chatbot/lib/sse-client';
import { ChatMessage } from '@/features/chatbot/ui/ChatMessage';
import { ChatInput } from '@/features/chatbot/ui/ChatInput';
import { SuggestedQuestions } from '@/features/chatbot/ui/SuggestedQuestions';
import { StreamingText } from '@/features/chatbot/ui/StreamingText';
import { ConversationList } from '@/features/chatbot/ui/ConversationList';
import { Button } from '@/shared/ui/button';
import { ScrollArea } from '@/shared/ui/scroll-area';

export function Component() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: convData } = useConversations();
  const deleteConversation = useDeleteConversation();

  const {
    conversationId,
    messages,
    isStreaming,
    isGenerating,
    streamingContent,
    activeAgents,
    setConversationId,
    setMessages,
    addUserMessage,
    startStreaming,
    appendStreamToken,
    finishStreaming,
    updateAgent,
    updateTool,
    setGenerating,
    clearChat,
  } = useChatStore();

  // 대화 선택 시 메시지 로드
  const { data: convDetail } = useConversationDetail(conversationId);
  useEffect(() => {
    if (convDetail) {
      setMessages(convDetail.messages);
    }
  }, [convDetail, setMessages]);

  // 메시지 추가 시 스크롤 (ScrollArea 내부 viewport 직접 제어)
  useEffect(() => {
    const scrollToBottom = () => {
      const viewport = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    };

    // 약간의 지연을 주어 DOM 업데이트 후 스크롤
    const timer = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timer);
  }, [messages.length, streamingContent]);

  const handleSend = async (text: string) => {
    if (isStreaming) return;
    addUserMessage(text);
    startStreaming();

    await streamChat(text, conversationId, {
      onToken: appendStreamToken,
      onDone: (convId, msgId) => {
        setConversationId(convId);
        finishStreaming(msgId);
        queryClient.invalidateQueries({ queryKey: chatbotKeys.conversations() });
      },
      onError: () => {
        finishStreaming(`error-${Date.now()}`);
      },
      onAgent: updateAgent,
      onTool: updateTool,
      onGenerating: setGenerating,
    });
  };

  const handleNewChat = () => {
    clearChat();
    setSidebarOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    if (id === conversationId) return;
    clearChat();
    setConversationId(id);
    setSidebarOpen(false);
  };

  const handleDeleteConversation = (id: string) => {
    deleteConversation.mutate(id);
    if (id === conversationId) {
      clearChat();
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } fixed left-0 top-16 z-50 h-[calc(100vh-4rem)] w-64 border-r border-border bg-muted/50 transition-transform lg:static lg:z-auto lg:translate-x-0 lg:flex lg:flex-col`}
      >
        <ConversationList
          conversations={convData?.conversations || []}
          activeId={conversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewChat}
          onDelete={handleDeleteConversation}
        />
      </aside>

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center border-b border-border px-4 py-3 lg:justify-center">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="대화 목록 열기"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <h1 className="hidden text-sm font-medium text-muted-foreground lg:block">
            AI 재무 상담
          </h1>
        </header>

        {/* Messages */}
        <ScrollArea ref={scrollAreaRef} className="min-h-0 flex-1 p-4">
          <div className="mx-auto max-w-4xl space-y-4">
            {messages.length === 0 && !isStreaming && (
              <>
                <div className="mt-12 text-center text-muted-foreground sm:mt-20">
                  <Bot className="mx-auto mb-4 h-12 w-12 text-muted-foreground" aria-hidden="true" />
                  <p className="text-lg font-medium">
                    AI 재무 상담에 오신 것을 환영합니다
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground/70">
                    자산, 예산, 투자에 대해 무엇이든 물어보세요
                  </p>
                </div>
                <div className="mt-6 sm:mt-8">
                  <SuggestedQuestions onSelect={handleSend} />
                </div>
              </>
            )}

            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {isStreaming && (
              <StreamingText
                content={streamingContent}
                activeAgents={activeAgents}
                isGenerating={isGenerating}
              />
            )}

            <div ref={messagesEndRef} aria-live="polite" aria-atomic="true" className="sr-only">
              {isStreaming ? '메시지를 작성하고 있습니다' : ''}
            </div>
          </div>
        </ScrollArea>

        {/* Disclaimer */}
        <div className="border-t border-border/50 px-4 py-2">
          <p className="text-center text-xs text-muted-foreground/70">
            AI 응답은 참고 목적이며, 투자 결정에 대한 책임은 사용자에게 있습니다.
          </p>
        </div>

        {/* Input */}
        <div className="border-t border-border p-4">
          <div className="mx-auto max-w-4xl">
            <ChatInput onSend={handleSend} disabled={isStreaming} />
          </div>
        </div>
      </main>
    </div>
  );
}
