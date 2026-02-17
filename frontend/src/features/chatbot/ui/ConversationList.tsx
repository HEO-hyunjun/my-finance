import { Plus, Trash2 } from 'lucide-react';
import type { ConversationSummary } from '@/shared/types';
import { Button } from '@/shared/ui/button';
import { ScrollArea } from '@/shared/ui/scroll-area';

interface Props {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete?: (id: string) => void;
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-sm font-medium text-foreground">대화 목록</span>
        <Button
          variant="ghost"
          size="icon"
          onClick={onNew}
          className="h-7 w-7"
          aria-label="새 대화"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        {conversations.length === 0 ? (
          <p className="px-4 py-8 text-center text-xs text-muted-foreground">
            아직 대화가 없습니다
          </p>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(conv.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelect(conv.id);
                }
              }}
              aria-current={activeId === conv.id ? 'page' : undefined}
              className={`group flex cursor-pointer items-center justify-between px-4 py-3 transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                activeId === conv.id
                  ? 'border-l-2 border-primary bg-primary/5'
                  : ''
              }`}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {conv.title}
                </p>
                <p className="text-xs text-muted-foreground">
                  {conv.message_count}개 메시지
                </p>
              </div>
              {onDelete && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(conv.id);
                  }}
                  className="ml-2 hidden h-6 w-6 shrink-0 text-muted-foreground hover:text-destructive group-hover:flex"
                  aria-label={`${conv.title} 대화 삭제`}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          ))
        )}
      </ScrollArea>
    </div>
  );
}
