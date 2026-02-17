import { useState } from 'react';
import { INCOME_TYPE_LABELS } from '@/shared/types';
import type { IncomeType } from '@/shared/types';
import { useIncomes, useDeleteIncome } from '../api';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';

function formatKRW(value: number): string {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    maximumFractionDigits: 0,
  }).format(value);
}

interface Props {
  incomeType?: string;
  startDate?: string;
  endDate?: string;
}

export function IncomeList({ incomeType, startDate, endDate }: Props) {
  const [page, setPage] = useState(1);
  const [confirmState, setConfirmState] = useState<{ action: () => void } | null>(null);
  const perPage = 20;

  const { data, isLoading } = useIncomes({
    income_type: incomeType,
    start_date: startDate,
    end_date: endDate,
    page,
    per_page: perPage,
  });

  const deleteIncome = useDeleteIncome();

  const handleDelete = (id: string) => {
    setConfirmState({ action: () => deleteIncome.mutate(id) });
  };

  // 로딩 스켈레톤
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3"
          >
            <div className="flex items-center gap-3">
              <div className="h-6 w-16 animate-pulse rounded bg-gray-200" />
              <div className="space-y-1">
                <div className="h-4 w-32 animate-pulse rounded bg-gray-200" />
                <div className="h-3 w-24 animate-pulse rounded bg-gray-100" />
              </div>
            </div>
            <div className="h-5 w-20 animate-pulse rounded bg-gray-200" />
          </div>
        ))}
      </div>
    );
  }

  const incomes = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / perPage);

  // 빈 상태
  if (incomes.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-400">
        수입 내역이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {incomes.map((income) => (
        <div
          key={income.id}
          className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3"
        >
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600">
              {INCOME_TYPE_LABELS[income.type as IncomeType] || income.type}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{income.description}</span>
                {income.is_recurring && (
                  <span className="rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-500">
                    정기
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span>{income.received_at}</span>
                {income.is_recurring && income.recurring_day && (
                  <span>매월 {income.recurring_day}일</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-medium text-emerald-600">+{formatKRW(income.amount)}</span>
            <button
              onClick={() => handleDelete(income.id)}
              disabled={deleteIncome.isPending}
              className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-50"
            >
              삭제
            </button>
          </div>
        </div>
      ))}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 pt-2">
          <button
            onClick={() => setPage((p) => p - 1)}
            disabled={page <= 1}
            className="rounded border px-3 py-1 text-sm disabled:opacity-30"
          >
            이전
          </button>
          <span className="px-3 py-1 text-sm text-gray-500">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            className="rounded border px-3 py-1 text-sm disabled:opacity-30"
          >
            다음
          </button>
        </div>
      )}

      <ConfirmDialog
        open={confirmState !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmState(null);
        }}
        title="이 수입을 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={() => confirmState?.action()}
        variant="destructive"
      />
    </div>
  );
}
