import { useState } from 'react';
import { Loader2, AlertTriangle, Pencil } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { usePortfolioTargets } from '@/features/portfolio/api';
import { ASSET_CLASS_LABELS, NEEDS_RESET_SENTINEL } from '@/features/portfolio/lib/asset-class';
import { TargetsEditDialog } from './TargetsEditDialog';

function formatPercent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

export function TargetsEditor() {
  const { data: targets = [], isLoading } = usePortfolioTargets();
  const [showEdit, setShowEdit] = useState(false);

  const needsReset = targets.some((t) => t.asset_type === NEEDS_RESET_SENTINEL);
  const validTargets = targets.filter((t) => t.asset_type !== NEEDS_RESET_SENTINEL);
  const hasTargets = validTargets.length > 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">목표 비중</CardTitle>
          <Button variant="outline" size="sm" onClick={() => setShowEdit(true)}>
            <Pencil className="mr-1 h-3.5 w-3.5" />
            {hasTargets ? '편집' : '설정'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {needsReset && (
              <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>자산 분류 체계가 바뀌어 목표 비중 재설정이 필요합니다. [설정]에서 새 자산군으로 다시 설정해주세요.</span>
              </div>
            )}

            {!hasTargets ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                목표 비중이 설정되어 있지 않습니다. [설정]으로 자산군별 목표 비중을 정해보세요.
              </p>
            ) : (
              <div className="space-y-3">
                {validTargets.map((t) => (
                  <div key={t.id} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{ASSET_CLASS_LABELS[t.asset_type] ?? t.asset_type}</span>
                      <span className="text-muted-foreground">
                        현재 {formatPercent(t.current_ratio)} / 목표 {formatPercent(t.target_ratio)}
                      </span>
                    </div>
                    <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${Math.min(t.current_ratio * 100, 100)}%` }}
                      />
                      {/* 목표 지점 마커 */}
                      <div
                        className="absolute top-0 h-full w-0.5 bg-foreground/60"
                        style={{ left: `${Math.min(t.target_ratio * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>

      <TargetsEditDialog isOpen={showEdit} onClose={() => setShowEdit(false)} targets={targets} />
    </Card>
  );
}
