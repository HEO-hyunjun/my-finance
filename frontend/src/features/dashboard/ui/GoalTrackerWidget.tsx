import { useState, memo, useCallback, useMemo } from 'react';
import { useGoal, useSetGoal } from '../api/portfolio';
import { formatKRW, formatPercent } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Target, Calendar, Wallet } from 'lucide-react';

const SetGoalModal = memo(function SetGoalModal({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
  defaultAmount,
  defaultDate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { target_amount: number; target_date?: string }) => void;
  isSubmitting: boolean;
  defaultAmount?: number;
  defaultDate?: string;
}) {
  const [amount, setAmount] = useState(defaultAmount?.toString() ?? '');
  const [date, setDate] = useState(defaultDate ?? '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount) return;
    onSubmit({
      target_amount: Number(amount),
      target_date: date || undefined,
    });
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>목표 자산 설정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="goal-amount">목표 금액 (원)</Label>
            <Input
              id="goal-amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="100,000,000"
              min="0"
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="goal-date">목표 일자 (선택)</Label>
            <Input
              id="goal-date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-1"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" onClick={onClose} variant="outline" size="sm">
              취소
            </Button>
            <Button type="submit" disabled={!amount || isSubmitting} size="sm">
              {isSubmitting ? '저장 중...' : '저장'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
});

function GoalTrackerWidgetInner() {
  const [modalOpen, setModalOpen] = useState(false);
  const { data: goal, isLoading } = useGoal();
  const setGoal = useSetGoal();

  const handleOpenModal = useCallback(() => setModalOpen(true), []);
  const handleCloseModal = useCallback(() => setModalOpen(false), []);
  const handleSubmit = useCallback((data: { target_amount: number; target_date?: string }) => {
    setGoal.mutate(data);
  }, [setGoal]);

  const clampedRate = useMemo(
    () => goal ? Math.min(goal.achievement_rate, 100) : 0,
    [goal]
  );

  if (isLoading) {
    return <Skeleton className="h-44 rounded-xl" />;
  }

  // No goal set yet
  if (!goal) {
    return (
      <Card>
        <CardContent className="text-center pt-6">
          <Target className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">목표 자산이 설정되지 않았습니다.</p>
          <Button onClick={handleOpenModal} className="mt-3" size="sm">
            목표 설정
          </Button>
          <SetGoalModal
            isOpen={modalOpen}
            onClose={handleCloseModal}
            onSubmit={handleSubmit}
            isSubmitting={setGoal.isPending}
          />
        </CardContent>
      </Card>
    );
  }

  const {
    target_amount,
    current_amount,
    achievement_rate,
    remaining_amount,
    monthly_required,
    estimated_date,
  } = goal;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            <CardTitle className="text-sm">목표 자산</CardTitle>
          </div>
          <Button onClick={handleOpenModal} variant="ghost" size="sm" className="h-auto p-0 text-xs">
            수정
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{formatKRW(target_amount)}</p>

        {/* Progress bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>달성률</span>
            <span className="font-medium text-primary">{formatPercent(achievement_rate).replace('+', '')}</span>
          </div>
          <div className="h-3 w-full rounded-full bg-muted">
            <div
              className="h-3 rounded-full bg-primary transition-[width] duration-500"
              style={{ width: `${clampedRate}%` }}
            />
          </div>
        </div>

        {/* Details */}
        <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="flex items-center gap-1 text-muted-foreground">
              <Wallet className="h-3 w-3" />
              현재 자산
            </span>
            <p className="font-medium">{formatKRW(current_amount)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">남은 금액</span>
            <p className="font-medium">{formatKRW(remaining_amount)}</p>
          </div>
          {monthly_required != null && (
            <div>
              <span className="text-muted-foreground">월 필요 저축</span>
              <p className="font-medium">{formatKRW(monthly_required)}</p>
            </div>
          )}
          {estimated_date && (
            <div>
              <span className="flex items-center gap-1 text-muted-foreground">
                <Calendar className="h-3 w-3" />
                예상 달성일
              </span>
              <p className="font-medium">{estimated_date}</p>
            </div>
          )}
        </div>

        <SetGoalModal
          isOpen={modalOpen}
          onClose={handleCloseModal}
          onSubmit={handleSubmit}
          isSubmitting={setGoal.isPending}
          defaultAmount={target_amount}
          defaultDate={goal.target_date}
        />
      </CardContent>
    </Card>
  );
}

export const GoalTrackerWidget = memo(GoalTrackerWidgetInner);
