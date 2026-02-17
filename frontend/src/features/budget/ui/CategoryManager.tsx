import { useState } from 'react';
import type { BudgetCategory, BudgetCategoryCreateRequest, BudgetCategoryUpdateRequest } from '@/shared/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import { ScrollArea } from '@/shared/ui/scroll-area';
import { cn } from '@/shared/lib/utils';
import { formatKRW } from '@/shared/lib/format';

interface Props {
  categories: BudgetCategory[];
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: BudgetCategoryCreateRequest) => void;
  onUpdate: (id: string, data: BudgetCategoryUpdateRequest) => void;
  isLoading?: boolean;
}

export function CategoryManager({
  categories,
  isOpen,
  onClose,
  onCreate,
  onUpdate,
  isLoading,
}: Props) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('');
  const [color, setColor] = useState('#3B82F6');
  const [budget, setBudget] = useState('');

  const resetForm = () => {
    setName('');
    setIcon('');
    setColor('#3B82F6');
    setBudget('');
    setShowAddForm(false);
    setEditingId(null);
  };

  const handleAdd = () => {
    if (!name) return;
    onCreate({
      name,
      icon: icon || undefined,
      color: color || undefined,
      monthly_budget: budget ? Number(budget) : 0,
    });
    resetForm();
  };

  const handleStartEdit = (cat: BudgetCategory) => {
    setEditingId(cat.id);
    setBudget(cat.monthly_budget > 0 ? String(cat.monthly_budget) : '');
  };

  const handleSaveBudget = (catId: string) => {
    onUpdate(catId, {
      monthly_budget: budget ? Number(budget) : 0,
    });
    setEditingId(null);
    setBudget('');
  };

  const handleToggleActive = (cat: BudgetCategory) => {
    onUpdate(cat.id, { is_active: !cat.is_active });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>카테고리 관리</DialogTitle>
        </DialogHeader>

        {/* 카테고리 목록 */}
        <ScrollArea className="h-80">
          <div className="space-y-2 pr-4">
            {categories.map((cat) => (
              <div
                key={cat.id}
                className={cn(
                  'flex items-center justify-between rounded-lg border p-3',
                  cat.is_active ? 'border-border' : 'border-muted bg-muted opacity-60',
                )}
              >
                <div className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: cat.color || '#B2BEC3' }}
                  />
                  <span>{cat.icon}</span>
                  <span className="font-medium">{cat.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {editingId === cat.id ? (
                    <div className="flex items-center gap-1">
                      <Input
                        type="number"
                        value={budget}
                        onChange={(e) => setBudget(e.target.value)}
                        placeholder="월 예산"
                        className="w-28"
                        min={0}
                      />
                      <Button
                        onClick={() => handleSaveBudget(cat.id)}
                        disabled={isLoading}
                        size="sm"
                      >
                        저장
                      </Button>
                      <Button
                        onClick={() => { setEditingId(null); setBudget(''); }}
                        variant="ghost"
                        size="sm"
                      >
                        취소
                      </Button>
                    </div>
                  ) : (
                    <>
                      <span className="text-sm text-muted-foreground">
                        {cat.monthly_budget > 0 ? formatKRW(cat.monthly_budget) : '미설정'}
                      </span>
                      <Button
                        onClick={() => handleStartEdit(cat)}
                        variant="ghost"
                        size="sm"
                      >
                        예산
                      </Button>
                      <Button
                        onClick={() => handleToggleActive(cat)}
                        variant="ghost"
                        size="sm"
                        className={cn(
                          cat.is_active
                            ? 'text-destructive hover:bg-destructive/10'
                            : 'text-green-500 hover:bg-green-50',
                        )}
                      >
                        {cat.is_active ? '비활성' : '활성'}
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* 카테고리 추가 폼 */}
        {showAddForm ? (
          <div className="space-y-3 rounded-lg border border-primary/20 bg-primary/5 p-3">
            <div className="flex gap-2">
              <Input
                type="text"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="아이콘"
                maxLength={10}
                className="w-16"
              />
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="카테고리 이름"
                maxLength={50}
                className="flex-1"
              />
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="h-10 w-10 cursor-pointer rounded border"
              />
            </div>
            <div className="flex gap-2">
              <Input
                type="number"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="월 예산 (선택)"
                min={0}
                className="flex-1"
              />
              <Button
                onClick={handleAdd}
                disabled={isLoading || !name}
              >
                추가
              </Button>
              <Button
                onClick={resetForm}
                variant="outline"
              >
                취소
              </Button>
            </div>
          </div>
        ) : (
          <Button
            onClick={() => setShowAddForm(true)}
            variant="outline"
            className="w-full border-dashed"
          >
            + 카테고리 추가
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}
