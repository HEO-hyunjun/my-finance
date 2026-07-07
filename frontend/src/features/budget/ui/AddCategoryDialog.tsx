import { useState, useEffect } from 'react';
import { useCreateCategory } from '@/features/categories/api';
import { useCreateAllocation } from '@/features/budget/api';
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

interface AddCategoryDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AddCategoryDialog({ isOpen, onClose }: AddCategoryDialogProps) {
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('');
  const [color, setColor] = useState('#6366f1');
  const [budgetAmount, setBudgetAmount] = useState('');

  const createCategory = useCreateCategory();
  const createAllocation = useCreateAllocation();

  useEffect(() => {
    if (isOpen) {
      setName('');
      setIcon('');
      setColor('#6366f1');
      setBudgetAmount('');
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      const newCat = await createCategory.mutateAsync({
        direction: 'expense',
        name: name.trim(),
        icon: icon || null,
        color: color || null,
      });

      const amount = Number(budgetAmount);
      if (!isNaN(amount) && amount > 0) {
        await createAllocation.mutateAsync({ category_id: newCat.id, amount });
      }

      onClose();
    } catch {
      // error handled by mutation
    }
  };

  const isPending = createCategory.isPending || createAllocation.isPending;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>카테고리 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="add_name">카테고리 이름 *</Label>
            <Input
              id="add_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 식비"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="add_icon">아이콘</Label>
              <Input
                id="add_icon"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="🍽️"
                className="text-center"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="add_color">색상</Label>
              <div className="flex items-center gap-2">
                <input
                  id="add_color"
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="h-9 w-12 cursor-pointer rounded border"
                  title="색상 선택"
                />
                <span className="text-xs text-muted-foreground font-mono">{color}</span>
              </div>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="add_budget">예산 금액 (선택)</Label>
            <Input
              id="add_budget"
              type="number"
              min="0"
              value={budgetAmount}
              onChange={(e) => setBudgetAmount(e.target.value)}
              placeholder="0"
            />
            <p className="text-xs text-muted-foreground">비워두면 미배분 상태로 생성됩니다.</p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>취소</Button>
            <Button type="submit" disabled={isPending || !name.trim()}>
              {isPending ? '추가 중...' : '추가'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
