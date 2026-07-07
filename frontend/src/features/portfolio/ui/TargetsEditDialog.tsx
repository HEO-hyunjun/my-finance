import { useState, useEffect, useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { cn } from '@/shared/lib/utils';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/ui/dialog';
import { useSetPortfolioTargets } from '@/features/portfolio/api';
import type { PortfolioTargetResponse, PortfolioTargetCreate } from '@/shared/types/portfolio';
import { ASSET_CLASSES, ASSET_CLASS_LABELS, NEEDS_RESET_SENTINEL } from '@/features/portfolio/lib/asset-class';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  targets: PortfolioTargetResponse[];
}

function toPercentString(ratio: number): string {
  return (ratio * 100).toFixed(1);
}

export function TargetsEditDialog({ isOpen, onClose, targets }: Props) {
  const setTargets = useSetPortfolioTargets();
  const [percents, setPercents] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!isOpen) return;
    const initial: Record<string, string> = {};
    for (const ac of ASSET_CLASSES) {
      const existing = targets.find((t) => t.asset_type === ac);
      initial[ac] = existing ? toPercentString(existing.target_ratio) : '';
    }
    setPercents(initial);
  }, [isOpen, targets]);

  const total = useMemo(
    () => ASSET_CLASSES.reduce((sum, ac) => sum + (Number(percents[ac]) || 0), 0),
    [percents],
  );

  const isValid =
    Math.abs(total - 100) < 0.01 &&
    ASSET_CLASSES.every((ac) => {
      const v = Number(percents[ac]);
      return !isNaN(v) && v >= 0 && v <= 100;
    });

  const hadSentinel = targets.some((t) => t.asset_type === NEEDS_RESET_SENTINEL);

  const handleSave = () => {
    if (!isValid) {
      toast.error('합계가 100%가 되도록 조정해주세요');
      return;
    }
    const payload: PortfolioTargetCreate[] = ASSET_CLASSES
      .filter((ac) => (Number(percents[ac]) || 0) > 0)
      .map((ac) => ({ asset_type: ac, target_ratio: Number(percents[ac]) / 100 }));
    setTargets.mutate(payload, {
      onSuccess: () => {
        toast.success('목표 비중이 저장되었습니다');
        onClose();
      },
      onError: () => toast.error('저장에 실패했습니다'),
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>목표 비중 편집</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            {hadSentinel
              ? '자산 분류 체계가 바뀌어 목표 비중 재설정이 필요합니다. 5개 자산군의 목표 비중을 입력하세요 (합계 100%).'
              : '5개 자산군의 목표 비중을 입력하세요. 합계는 반드시 100%여야 합니다.'}
          </p>

          <div className="space-y-2">
            {ASSET_CLASSES.map((ac) => (
              <div key={ac} className="flex items-center gap-3">
                <span className="flex-1 text-sm">{ASSET_CLASS_LABELS[ac]}</span>
                <div className="flex w-32 items-center gap-1.5">
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    max={100}
                    value={percents[ac] ?? ''}
                    onChange={(e) => setPercents((prev) => ({ ...prev, [ac]: e.target.value }))}
                    placeholder="0"
                    className="text-right"
                  />
                  <span className="text-sm text-muted-foreground">%</span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-end gap-2 border-t pt-3 text-sm font-medium">
            <span className="text-muted-foreground">합계</span>
            <span className={cn(Math.abs(total - 100) < 0.01 ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive')}>
              {total.toFixed(1)}%
            </span>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>취소</Button>
          <Button onClick={handleSave} disabled={!isValid || setTargets.isPending}>
            {setTargets.isPending && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
            저장
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
