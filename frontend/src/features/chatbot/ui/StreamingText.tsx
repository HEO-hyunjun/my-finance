import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, Search, TrendingUp, Wallet } from 'lucide-react';

interface AgentStatus {
  name: string;
  status: 'started' | 'done';
}

interface Props {
  content: string;
  activeAgents?: AgentStatus[];
}

const AGENT_ICONS: Record<string, typeof Bot> = {
  '자산 분석': TrendingUp,
  '뉴스 분석': Search,
  '가계부 분석': Wallet,
};

export function StreamingText({ content, activeAgents = [] }: Props) {
  const hasAgents = activeAgents.length > 0;
  const isAnalyzing = hasAgents && activeAgents.some((a) => a.status === 'started');

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] sm:max-w-[80%] rounded-2xl bg-muted px-4 py-3 text-foreground">
        {/* 에이전트 상태 표시 */}
        {hasAgents && (
          <div className="mb-2 space-y-1.5">
            {activeAgents.map((agent) => {
              const Icon = AGENT_ICONS[agent.name] || Bot;
              const isDone = agent.status === 'done';
              return (
                <div
                  key={agent.name}
                  className={`flex items-center gap-2 text-xs rounded-lg px-2.5 py-1.5 ${
                    isDone
                      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                      : 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5 flex-shrink-0" />
                  <span className="font-medium">{agent.name}</span>
                  {isDone ? (
                    <span className="ml-auto text-[10px]">완료</span>
                  ) : (
                    <span className="ml-auto flex items-center gap-0.5 text-[10px]">
                      분석 중
                      <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                      <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                      <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 응답 콘텐츠 */}
        {content ? (
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        ) : !isAnalyzing ? (
          <div className="flex items-center gap-1 text-muted-foreground">
            <span className="animate-pulse">생각 중</span>
            <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
            <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
            <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
          </div>
        ) : null}

        {content && (
          <span className="inline-block h-4 w-1 animate-pulse bg-foreground/40" aria-hidden="true" />
        )}
      </div>
    </div>
  );
}
