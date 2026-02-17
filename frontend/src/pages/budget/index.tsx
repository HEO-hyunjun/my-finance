import { useState, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Plus, Settings } from 'lucide-react';
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
  useBudgetSummary,
  useFixedExpenses,
  useCreateFixedExpense,
  useDeleteFixedExpense,
  useToggleFixedExpense,
  useInstallments,
  useCreateInstallment,
  useDeleteInstallment,
} from '@/features/budget/api';
import { BudgetSummaryCard } from '@/features/budget/ui/BudgetSummaryCard';
import { CategoryBudgetList } from '@/features/budget/ui/CategoryBudgetList';
import { CategoryManager } from '@/features/budget/ui/CategoryManager';
import { FixedExpenseList } from '@/features/budget/ui/FixedExpenseList';
import { AddFixedExpenseModal } from '@/features/budget/ui/AddFixedExpenseModal';
import { InstallmentList } from '@/features/budget/ui/InstallmentList';
import { AddInstallmentModal } from '@/features/budget/ui/AddInstallmentModal';
import { BudgetAnalysisWidget } from '@/features/budget/ui/BudgetAnalysisWidget';
import { FixedDeductionWidget } from '@/features/budget/ui/FixedDeductionWidget';
import { Button } from '@/shared/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/ui/tabs';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';

type Tab = 'fixed' | 'installments' | 'analysis';

const TAB_LABELS: Record<Tab, string> = {
  fixed: '고정비',
  installments: '할부금',
  analysis: '분석',
};

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = (searchParams.get('tab') as Tab) || 'fixed';
  const [showAddFixed, setShowAddFixed] = useState(false);
  const [showAddInstallment, setShowAddInstallment] = useState(false);
  const [showCategoryManager, setShowCategoryManager] = useState(false);
  const [confirmState, setConfirmState] = useState<{ action: () => void } | null>(null);

  const { data: categories = [], isLoading: catLoading } = useCategories();
  const { data: summary, isLoading: summaryLoading } = useBudgetSummary();
  const { data: fixedExpenses = [], isLoading: fixedLoading } = useFixedExpenses();
  const { data: installments = [], isLoading: instLoading } = useInstallments();

  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();
  const createFixedExpense = useCreateFixedExpense();
  const deleteFixedExpense = useDeleteFixedExpense();
  const toggleFixedExpense = useToggleFixedExpense();
  const createInstallment = useCreateInstallment();
  const deleteInstallment = useDeleteInstallment();

  const isLoading = catLoading || summaryLoading || fixedLoading || instLoading;

  // Stable modal open/close callbacks
  const handleOpenAddFixed = useCallback(() => setShowAddFixed(true), []);
  const handleCloseAddFixed = useCallback(() => setShowAddFixed(false), []);
  const handleOpenAddInstallment = useCallback(() => setShowAddInstallment(true), []);
  const handleCloseAddInstallment = useCallback(() => setShowAddInstallment(false), []);
  const handleOpenCategoryManager = useCallback(() => setShowCategoryManager(true), []);
  const handleCloseCategoryManager = useCallback(() => setShowCategoryManager(false), []);

  // Stable action callbacks
  const handleToggleFixed = useCallback(
    (id: string) => toggleFixedExpense.mutate(id),
    [toggleFixedExpense],
  );
  const handleDeleteFixed = useCallback(
    (id: string) => {
      setConfirmState({ action: () => deleteFixedExpense.mutate(id) });
    },
    [deleteFixedExpense],
  );
  const handleDeleteInstallment = useCallback(
    (id: string) => {
      setConfirmState({ action: () => deleteInstallment.mutate(id) });
    },
    [deleteInstallment],
  );
  const handleSubmitFixed = useCallback(
    (data: Parameters<typeof createFixedExpense.mutate>[0]) => createFixedExpense.mutate(data),
    [createFixedExpense],
  );
  const handleSubmitInstallment = useCallback(
    (data: Parameters<typeof createInstallment.mutate>[0]) => createInstallment.mutate(data),
    [createInstallment],
  );
  const handleCreateCategory = useCallback(
    (data: Parameters<typeof createCategory.mutate>[0]) => createCategory.mutate(data),
    [createCategory],
  );
  const handleUpdateCategory = useCallback(
    (id: string, data: Parameters<typeof updateCategory.mutate>[0]['data']) =>
      updateCategory.mutate({ id, data }),
    [updateCategory],
  );
  const handleTabChange = useCallback((value: string) => {
    setSearchParams((prev) => {
      prev.set('tab', value);
      return prev;
    });
  }, [setSearchParams]);

  const addButtonConfig = useMemo<Partial<Record<Tab, { label: string; action: () => void }>>>(
    () => ({
      fixed: { label: '고정비 추가', action: handleOpenAddFixed },
      installments: { label: '할부금 추가', action: handleOpenAddInstallment },
    }),
    [handleOpenAddFixed, handleOpenAddInstallment],
  );

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-end">
        {addButtonConfig[activeTab] && (
          <Button onClick={addButtonConfig[activeTab].action}>
            <Plus className="mr-2 h-4 w-4" />
            {addButtonConfig[activeTab].label}
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <>
          {/* 예산 요약 */}
          {summary && <BudgetSummaryCard summary={summary} />}

          {/* 카테고리별 소진율 */}
          {summary && (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold">카테고리별 예산</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleOpenCategoryManager}
                >
                  <Settings className="mr-1 h-4 w-4" />
                  설정
                </Button>
              </div>
              <CategoryBudgetList
                categories={summary.categories}
                onUpdateBudget={(categoryId, monthlyBudget) =>
                  updateCategory.mutate({ id: categoryId, data: { monthly_budget: monthlyBudget } })
                }
                onUpdateName={(categoryId, name) =>
                  updateCategory.mutate({ id: categoryId, data: { name } })
                }
                onDelete={(categoryId) => deleteCategory.mutate(categoryId)}
                onReorder={(ordered) =>
                  ordered.forEach(({ id, sort_order }) =>
                    updateCategory.mutate({ id, data: { sort_order } })
                  )
                }
                isUpdating={updateCategory.isPending || deleteCategory.isPending}
              />
            </div>
          )}

          {/* 탭 네비게이션 */}
          <Tabs value={activeTab} onValueChange={handleTabChange}>
            <TabsList className="grid w-full grid-cols-3">
              {(Object.entries(TAB_LABELS) as [Tab, string][]).map(([tab, label]) => (
                <TabsTrigger key={tab} value={tab}>
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="fixed">
              <FixedExpenseList
                fixedExpenses={fixedExpenses}
                onToggle={handleToggleFixed}
                onDelete={handleDeleteFixed}
              />
            </TabsContent>

            <TabsContent value="installments">
              <InstallmentList
                installments={installments}
                onDelete={handleDeleteInstallment}
              />
            </TabsContent>

            <TabsContent value="analysis">
              <div className="space-y-4">
                <BudgetAnalysisWidget />
                <FixedDeductionWidget />
              </div>
            </TabsContent>
          </Tabs>

        </>
      )}

      {/* 모달들 */}
      <AddFixedExpenseModal
        categories={categories}
        isOpen={showAddFixed}
        onClose={handleCloseAddFixed}
        onSubmit={handleSubmitFixed}
        isLoading={createFixedExpense.isPending}
      />

      <AddInstallmentModal
        categories={categories}
        isOpen={showAddInstallment}
        onClose={handleCloseAddInstallment}
        onSubmit={handleSubmitInstallment}
        isLoading={createInstallment.isPending}
      />

      <CategoryManager
        categories={categories}
        isOpen={showCategoryManager}
        onClose={handleCloseCategoryManager}
        onCreate={handleCreateCategory}
        onUpdate={handleUpdateCategory}
        isLoading={createCategory.isPending || updateCategory.isPending}
      />

      <ConfirmDialog
        open={confirmState !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmState(null);
        }}
        title="삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={() => confirmState?.action()}
        variant="destructive"
      />
    </div>
  );
}
