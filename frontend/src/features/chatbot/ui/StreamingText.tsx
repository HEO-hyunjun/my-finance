import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, CheckCircle2, Loader2, Search, TrendingUp, Wallet, XCircle } from 'lucide-react';

interface ToolStatus {
  name: string;
  status: 'calling' | 'done' | 'error';
}

interface AgentStatus {
  name: string;
  status: 'started' | 'done';
  tools: ToolStatus[];
}

interface Props {
  content: string;
  activeAgents?: AgentStatus[];
  isGenerating?: boolean;
}

const AGENT_ICONS: Record<string, typeof Bot> = {
  '자산 분석': TrendingUp,
  '뉴스 분석': Search,
  '가계부 분석': Wallet,
};

export function StreamingText({ content, activeAgents = [], isGenerating = false }: Props) {
  const hasAgents = activeAgents.length > 0;
  const isAnalyzing = hasAgents && activeAgents.some((a) => a.status === 'started');

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] sm:max-w-[80%] rounded-2xl bg-muted px-4 py-3 text-foreground">
        {/* 에이전트 상태 표시 */}
        {hasAgents && (
          <div className="mb-2 space-y-2">
            {activeAgents.map((agent) => {
              const Icon = AGENT_ICONS[agent.name] || Bot;
              const isDone = agent.status === 'done';
              return (
                <div
                  key={agent.name}
                  className={`rounded-lg border ${
                    isDone
                      ? 'border-emerald-500/20 bg-emerald-500/5'
                      : 'border-blue-500/20 bg-blue-500/5'
                  }`}
                >
                  {/* 에이전트 헤더 */}
                  <div
                    className={`flex items-center gap-2 px-2.5 py-1.5 text-xs ${
                      isDone
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-blue-600 dark:text-blue-400'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="font-medium">{agent.name}</span>
                    {isDone ? (
                      <span className="ml-auto text-[10px]">완료</span>
                    ) : (
                      <span className="ml-auto flex items-center gap-1 text-[10px]">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        분석 중
                      </span>
                    )}
                  </div>

                  {/* 도구 호출 목록 */}
                  {agent.tools.length > 0 && (
                    <div className="border-t border-current/5 px-2.5 py-1.5 space-y-0.5">
                      {agent.tools.map((tool) => (
                        <div
                          key={tool.name}
                          className="flex items-center gap-1.5 text-[11px] text-muted-foreground"
                        >
                          {tool.status === 'calling' && (
                            <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                          )}
                          {tool.status === 'done' && (
                            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                          )}
                          {tool.status === 'error' && (
                            <XCircle className="h-3 w-3 text-red-500" />
                          )}
                          <span className={tool.status === 'calling' ? 'text-foreground/80' : ''}>
                            {tool.name}
                          </span>
                          {tool.status === 'calling' && (
                            <span className="text-[10px] text-muted-foreground/60">조회 중...</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 답변 생성중 표시 */}
        {isGenerating && (
          <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>답변 생성중...</span>
          </div>
        )}

        {/* 응답 콘텐츠 */}
        {content ? (
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        ) : !isAnalyzing && !isGenerating ? (
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
