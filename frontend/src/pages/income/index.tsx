import { useState, useMemo } from "react";
import { TrendingUp, Banknote, Briefcase } from "lucide-react";
import { Card, CardContent } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { IncomeList } from "@/features/income/ui/IncomeList";
import { EditIncomeModal } from "@/features/income/ui/EditIncomeModal";
import { useIncomeSummary } from "@/features/income/api";
import { INCOME_TYPE_LABELS } from "@/shared/types";
import type { Income } from "@/shared/types";
import { formatKRW } from "@/shared/lib/format";

const TYPE_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "전체" },
  ...Object.entries(INCOME_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

function getMonthRange() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { start: fmt(start), end: fmt(end) };
}

export function Component() {
  const [editingIncome, setEditingIncome] = useState<Income | null>(null);
  const [selectedType, setSelectedType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const monthRange = useMemo(getMonthRange, []);
  const { data: summary } = useIncomeSummary({
    start: monthRange.start,
    end: monthRange.end,
  });

  const summaryCards = [
    {
      key: "total",
      label: "이번 달 총 수입",
      value: summary?.total_monthly_income ?? 0,
      icon: TrendingUp,
      color: "text-emerald-600 dark:text-emerald-400",
      bg: "bg-emerald-50 dark:bg-emerald-950",
    },
    {
      key: "salary",
      label: "급여",
      value: summary?.salary_income ?? 0,
      icon: Banknote,
      color: "text-blue-600 dark:text-blue-400",
      bg: "bg-blue-50 dark:bg-blue-950",
    },
    {
      key: "side",
      label: "부수입",
      value: summary?.side_income ?? 0,
      icon: Briefcase,
      color: "text-purple-600 dark:text-purple-400",
      bg: "bg-purple-50 dark:bg-purple-950",
    },
    {
      key: "investment",
      label: "투자수익",
      value: summary?.investment_income ?? 0,
      icon: TrendingUp,
      color: "text-amber-600 dark:text-amber-400",
      bg: "bg-amber-50 dark:bg-amber-950",
    },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* 요약 카드 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {summaryCards.map(({ key, label, value, icon: Icon, color, bg }) => (
          <Card key={key}>
            <CardContent className="flex items-center gap-3 pt-6">
              <div className={`rounded-lg p-2.5 ${bg}`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs text-muted-foreground">{label}</p>
                <p className={`text-lg font-bold ${color}`}>{formatKRW(value)}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 필터 */}
      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 pt-6">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">유형</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              {TYPE_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">시작일</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">종료일</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
          </div>
          {(selectedType || startDate || endDate) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedType("");
                setStartDate("");
                setEndDate("");
              }}
            >
              초기화
            </Button>
          )}
        </CardContent>
      </Card>

      {/* 수입 목록 */}
      <IncomeList
        incomeType={selectedType || undefined}
        startDate={startDate || undefined}
        endDate={endDate || undefined}
        onEdit={(income) => setEditingIncome(income)}
      />

      {/* 수입 수정 모달 */}
      {editingIncome && (
        <EditIncomeModal
          income={editingIncome}
          isOpen={!!editingIncome}
          onClose={() => setEditingIncome(null)}
        />
      )}
    </div>
  );
}
