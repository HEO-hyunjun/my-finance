import { useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import {
  useExpenses,
  useCategories,
  useUpdateExpense,
  useDeleteExpense,
} from "@/features/budget/api";
import { ExpenseFilter } from "@/features/budget/ui/ExpenseFilter";
import type { ExpenseFilterValues } from "@/features/budget/ui/ExpenseFilter";
import { ExpenseList } from "@/features/budget/ui/ExpenseList";
import { EditExpenseModal } from "@/features/budget/ui/EditExpenseModal";
import { Card, CardContent } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/skeleton";
import { ConfirmDialog } from "@/shared/ui/confirm-dialog";
import type { Expense } from "@/shared/types";

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<ExpenseFilterValues>({});
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [confirmState, setConfirmState] = useState<{ action: () => void } | null>(null);

  const page = Number(searchParams.get("page")) || 1;
  const perPage = 20;

  const { data: categories = [] } = useCategories();
  const {
    data: expenseData,
    isLoading,
    isError,
    refetch,
  } = useExpenses({
    ...filters,
    page,
    per_page: perPage,
  });
  const updateExpense = useUpdateExpense();
  const deleteExpense = useDeleteExpense();

  const handleFilterChange = useCallback(
    (newFilters: ExpenseFilterValues) => {
      setFilters(newFilters);
      setSearchParams((prev) => {
        prev.delete("page");
        return prev;
      });
    },
    [setSearchParams],
  );

  const handlePageChange = useCallback(
    (p: number) => {
      setSearchParams((prev) => {
        prev.set("page", String(p));
        return prev;
      });
    },
    [setSearchParams],
  );

  const handleEditExpense = useCallback((exp: Expense) => setEditingExpense(exp), []);

  const handleDeleteExpense = useCallback(
    (id: string) => {
      setConfirmState({ action: () => deleteExpense.mutate(id) });
    },
    [deleteExpense],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:space-y-6 sm:p-6">
      {/* 필터 */}
      <ExpenseFilter categories={categories} onFilterChange={handleFilterChange} />

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {/* 에러 */}
      {isError && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-12 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" aria-hidden="true" />
            <p className="text-muted-foreground mb-4">지출 내역을 불러올 수 없습니다.</p>
            <Button onClick={() => refetch()}>다시 시도</Button>
          </CardContent>
        </Card>
      )}

      {/* 결과 */}
      {expenseData && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              총{" "}
              <span className="font-semibold text-foreground">
                {expenseData.total.toLocaleString()}
              </span>
              건
            </p>
          </div>

          <ExpenseList
            expenses={expenseData.data}
            total={expenseData.total}
            page={page}
            perPage={perPage}
            onPageChange={handlePageChange}
            onEdit={handleEditExpense}
            onDelete={handleDeleteExpense}
          />
        </>
      )}

      {editingExpense && (
        <EditExpenseModal
          expense={editingExpense}
          categories={categories}
          isOpen={!!editingExpense}
          onClose={() => setEditingExpense(null)}
          onSubmit={(data) => updateExpense.mutate(data)}
          isLoading={updateExpense.isPending}
        />
      )}

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
