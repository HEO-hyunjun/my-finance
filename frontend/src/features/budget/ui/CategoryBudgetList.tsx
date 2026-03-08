import { useState, memo, useCallback } from 'react';
import { Check, X, Trash2, Pencil, GripVertical } from 'lucide-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { CategoryBudgetSummary } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Input } from '@/shared/ui/input';

interface Props {
  categories: CategoryBudgetSummary[];
  onUpdateBudget?: (categoryId: string, monthlyBudget: number) => void;
  onUpdateName?: (categoryId: string, name: string) => void;
  onDelete?: (categoryId: string) => void;
  onReorder?: (orderedIds: { id: string; sort_order: number }[]) => void;
  isUpdating?: boolean;
}

function getBarColor(usageRate: number, color?: string): string {
  if (usageRate > 100) return '#EF4444';
  if (usageRate > 80) return '#F59E0B';
  return color || '#3B82F6';
}

type EditMode = 'budget' | 'name';

interface SortableItemProps {
  cat: CategoryBudgetSummary;
  isEditing: boolean;
  isEditingBudget: boolean;
  isEditingName: boolean;
  editValue: string;
  isUpdating?: boolean;
  onUpdateBudget?: Props['onUpdateBudget'];
  onUpdateName?: Props['onUpdateName'];
  onDelete?: Props['onDelete'];
  onStartEditBudget: (cat: CategoryBudgetSummary) => void;
  onStartEditName: (e: React.MouseEvent, cat: CategoryBudgetSummary) => void;
  onSave: () => void;
  onCancel: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onEditValueChange: (value: string) => void;
  onDeleteClick: (e: React.MouseEvent, id: string) => void;
}

function SortableItem({
  cat,
  isEditing,
  isEditingBudget,
  isEditingName,
  editValue,
  isUpdating,
  onUpdateBudget,
  onUpdateName,
  onDelete,
  onStartEditBudget,
  onStartEditName,
  onSave,
  onCancel,
  onKeyDown,
  onEditValueChange,
  onDeleteClick,
}: SortableItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: cat.category_id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const barColor = getBarColor(cat.usage_rate, cat.category_color ?? undefined);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent/30 ${
        isDragging ? 'z-50 shadow-lg opacity-90' : ''
      }`}
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab touch-none rounded p-0.5 text-muted-foreground/50 hover:text-muted-foreground active:cursor-grabbing"
            tabIndex={-1}
          >
            <GripVertical className="h-4 w-4" />
          </button>
          <span>{cat.category_icon || ''}</span>
          {isEditingName ? (
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              <Input
                type="text"
                value={editValue}
                onChange={(e) => onEditValueChange(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="카테고리 이름"
                className="h-7 w-32 text-sm"
                autoFocus
              />
              <button
                onClick={onSave}
                disabled={isUpdating || !editValue.trim()}
                className="rounded p-1 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
              >
                <Check className="h-4 w-4" />
              </button>
              <button
                onClick={onCancel}
                className="rounded p-1 text-muted-foreground hover:bg-accent transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <span
                className="font-medium cursor-pointer"
                onClick={() => !isEditing && onUpdateBudget && onStartEditBudget(cat)}
              >
                {cat.category_name}
              </span>
              {onUpdateName && (
                <button
                  onClick={(e) => onStartEditName(e, cat)}
                  className="rounded p-0.5 text-muted-foreground/0 group-hover:text-muted-foreground hover:bg-accent transition-colors"
                >
                  <Pencil className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isEditingBudget ? (
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              <Input
                type="number"
                value={editValue}
                onChange={(e) => onEditValueChange(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="월 예산"
                className="h-7 w-28 text-right text-sm"
                min={0}
                autoFocus
              />
              <button
                onClick={onSave}
                disabled={isUpdating}
                className="rounded p-1 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
              >
                <Check className="h-4 w-4" />
              </button>
              <button
                onClick={onCancel}
                className="rounded p-1 text-muted-foreground hover:bg-accent transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div
              className="text-right text-sm cursor-pointer"
              onClick={() => !isEditing && onUpdateBudget && onStartEditBudget(cat)}
            >
              <span className="text-foreground">{formatKRW(cat.spent)}</span>
              <span className="text-muted-foreground"> / {formatKRW(cat.monthly_budget)}</span>
            </div>
          )}
          {!isEditing && onDelete && (
            <button
              onClick={(e) => onDeleteClick(e, cat.category_id)}
              disabled={isUpdating}
              className="rounded p-1 text-muted-foreground/0 group-hover:text-destructive/70 hover:bg-destructive/10 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-[width]"
          style={{
            width: `${Math.min(cat.usage_rate, 100)}%`,
            backgroundColor: barColor,
          }}
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted-foreground">
        <span>잔여 {formatKRW(cat.remaining)}</span>
        <span>{cat.usage_rate.toFixed(1)}%</span>
      </div>
    </div>
  );
}

function UncategorizedItem({ cat }: { cat: CategoryBudgetSummary }) {
  const barColor = getBarColor(0, cat.category_color ?? undefined);
  return (
    <div className="rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent/30">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span>{cat.category_icon || ''}</span>
          <span className="font-medium">{cat.category_name}</span>
        </div>
        <div className="text-right text-sm">
          <span className="text-foreground">{formatKRW(cat.spent)}</span>
        </div>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-[width]"
          style={{
            width: '0%',
            backgroundColor: barColor,
          }}
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted-foreground">
        <span>예산 미지정</span>
        <span>{formatKRW(cat.spent)} 지출</span>
      </div>
    </div>
  );
}

function CategoryBudgetListInner({ categories, onUpdateBudget, onUpdateName, onDelete, onReorder, isUpdating }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<EditMode>('budget');
  const [editValue, setEditValue] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  // 미분류 항목 분리
  const sortableCategories = categories.filter((c) => c.category_id !== null);
  const uncategorized = categories.find((c) => c.category_id === null);

  const handleStartEditBudget = useCallback((cat: CategoryBudgetSummary) => {
    setEditingId(cat.category_id);
    setEditMode('budget');
    setEditValue(cat.monthly_budget > 0 ? String(cat.monthly_budget) : '');
  }, []);

  const handleStartEditName = useCallback((e: React.MouseEvent, cat: CategoryBudgetSummary) => {
    e.stopPropagation();
    setEditingId(cat.category_id);
    setEditMode('name');
    setEditValue(cat.category_name);
  }, []);

  const handleSave = useCallback(() => {
    if (!editingId) return;
    if (editMode === 'budget' && onUpdateBudget) {
      onUpdateBudget(editingId, editValue ? Number(editValue) : 0);
    } else if (editMode === 'name' && onUpdateName && editValue.trim()) {
      onUpdateName(editingId, editValue.trim());
    }
    setEditingId(null);
    setEditValue('');
  }, [editingId, editMode, editValue, onUpdateBudget, onUpdateName]);

  const handleCancel = useCallback(() => {
    setEditingId(null);
    setEditValue('');
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') handleCancel();
  }, [handleSave, handleCancel]);

  const handleDelete = useCallback((e: React.MouseEvent, categoryId: string) => {
    e.stopPropagation();
    onDelete?.(categoryId);
  }, [onDelete]);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !onReorder) return;

    const oldIndex = sortableCategories.findIndex((c) => c.category_id === active.id);
    const newIndex = sortableCategories.findIndex((c) => c.category_id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const reordered = arrayMove(sortableCategories, oldIndex, newIndex);
    onReorder(reordered.map((c, i) => ({ id: c.category_id!, sort_order: i })));
  }, [sortableCategories, onReorder]);

  if (categories.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-5 text-center text-muted-foreground">
        카테고리가 없습니다.
      </div>
    );
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={sortableCategories.map((c) => c.category_id!)} strategy={verticalListSortingStrategy}>
        <div className="space-y-3">
          {sortableCategories.map((cat) => {
            const isEditing = editingId === cat.category_id;
            return (
              <SortableItem
                key={cat.category_id}
                cat={cat}
                isEditing={isEditing}
                isEditingBudget={isEditing && editMode === 'budget'}
                isEditingName={isEditing && editMode === 'name'}
                editValue={isEditing ? editValue : ''}
                isUpdating={isUpdating}
                onUpdateBudget={onUpdateBudget}
                onUpdateName={onUpdateName}
                onDelete={onDelete}
                onStartEditBudget={handleStartEditBudget}
                onStartEditName={handleStartEditName}
                onSave={handleSave}
                onCancel={handleCancel}
                onKeyDown={handleKeyDown}
                onEditValueChange={setEditValue}
                onDeleteClick={handleDelete}
              />
            );
          })}
          {uncategorized && uncategorized.spent > 0 && (
            <UncategorizedItem cat={uncategorized} />
          )}
        </div>
      </SortableContext>
    </DndContext>
  );
}

export const CategoryBudgetList = memo(CategoryBudgetListInner);
