import { useState } from 'react';
import { ENTRY_TYPE_LABELS, ENTRY_TYPE_BG } from '@/shared/lib/entry-labels';
import { EditEntryDialog } from '@/features/entries/ui/EditEntryDialog';
import { useDashboardSummary } from '@/features/dashboard/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW, formatDate } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

export function RecentTransactionsWidget() {
  const { data, isLoading, isError } = useDashboardSummary();
  const entries = data?.recent_entries ?? [];
  const [editEntryId, setEditEntryId] = useState<string | null>(null);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">최근 내역</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : entries.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">최근 내역이 없습니다</p>
        ) : (
          <ul className="divide-y">
            {entries.map((entry) => (
              <li key={entry.id}>
                <button
                  type="button"
                  onClick={() => setEditEntryId(entry.id)}
                  className="flex w-full items-center justify-between py-2.5 text-left transition-colors hover:bg-muted/30"
                >
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${ENTRY_TYPE_BG[entry.type] ?? 'bg-gray-100 text-gray-600'}`}>
                      {ENTRY_TYPE_LABELS[entry.type] ?? entry.type}
                    </span>
                    <span className="max-w-[120px] truncate text-sm text-muted-foreground">
                      {entry.memo ?? '메모 없음'}
                    </span>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-sm font-semibold ${
                        entry.amount < 0 ? 'text-destructive' : 'text-green-600'
                      }`}
                    >
                      {formatKRW(entry.amount)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(entry.transacted_at)}
                    </p>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      {editEntryId && (
        <EditEntryDialog
          entryId={editEntryId}
          open={!!editEntryId}
          onClose={() => setEditEntryId(null)}
        />
      )}
    </Card>
  );
}
