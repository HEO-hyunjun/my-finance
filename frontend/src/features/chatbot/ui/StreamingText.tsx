import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
}

export function StreamingText({ content }: Props) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] sm:max-w-[80%] rounded-2xl bg-muted px-4 py-3 text-foreground">
        {content ? (
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-muted-foreground">
            <span className="animate-pulse">생각 중</span>
            <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
            <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
            <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
          </div>
        )}
        {content && (
          <span className="inline-block h-4 w-1 animate-pulse bg-foreground/40" aria-hidden="true" />
        )}
      </div>
    </div>
  );
}
