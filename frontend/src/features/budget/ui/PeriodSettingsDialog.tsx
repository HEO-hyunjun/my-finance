import { useState } from 'react';
import { useUpdateBudgetPeriod } from '@/features/budget/api';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/ui/dialog';

interface PeriodSettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  currentDay: number;
}

export function PeriodSettingsDialog({ isOpen, onClose, currentDay }: PeriodSettingsDialogProps) {
  const [day, setDay] = useState(String(currentDay));
  const updatePeriod = useUpdateBudgetPeriod();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const num = Number(day);
    if (isNaN(num) || num < 1 || num > 28) return;
    updatePeriod.mutate({ period_start_day: num }, { onSuccess: onClose });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>예산 기간 설정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="period_day">월 시작일 (1~28)</Label>
            <Input
              id="period_day"
              type="number"
              min="1"
              max="28"
              value={day}
              onChange={(e) => setDay(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              예산 집계가 시작되는 날짜입니다.
            </p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>취소</Button>
            <Button type="submit" disabled={updatePeriod.isPending}>
              {updatePeriod.isPending ? '저장 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
