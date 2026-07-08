import { useState } from 'react';
import { Plus, AlertCircle, Trash2, Pencil, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEntries, useDeleteEntry, useDeleteEntryGroup } from '@/features/entries/api';
import { useAccounts } from '@/features/accounts/api';
import { CategorySelect } from '@/features/categories/ui/CategorySelect';
import { CreateEntryDialog } from '@/features/entries/ui/CreateEntryDialog';
import { EditEntryDialog } from '@/features/entries/ui/EditEntryDialog';
import type { EntryFilters, Entry } from '@/entities/entry/model/types';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select';
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '@/shared/ui/tabs';
import { ENTRY_TYPE_LABELS, ENTRY_TYPE_BG } from '@/shared/lib/entry-labels';

// ─── 상수 ─────────────────────────────────────────────────────────────────────

type EntryTab = 'all' | 'income' | 'expense' | 'transfer' | 'trade';

const TAB_TYPE_MAP: Record<EntryTab, string | undefined> = {
  all: undefined,
  income: 'income,dividend,interest',
  expense: 'expense,fee',
  transfer: 'transfer_in,transfer_out',
  trade: 'buy,sell',
};

const TAB_LABELS: Record<EntryTab, string> = {
  all: '전체',
  income: '수입',
  expense: '지출',
  transfer: '이체',
  trade: '매매',
};

const PER_PAGE_OPTIONS = [10, 20, 50];

// ─── 유틸 ─────────────────────────────────────────────────────────────────────

function formatCurrency(amount: number, currency = 'KRW'): string {
  try {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString('ko-KR')} ${currency}`;
  }
}

function formatDate(dateStr: string): string {
  try {
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

// ─── Entry Row ─────────────────────────────────────────────────────────────────

interface EntryRowProps {
  entry: Entry;
  accountName?: string;
  onEdit: (entry: Entry) => void;
  onDelete: (entry: Entry) => void;
}

function EntryRow({ entry, accountName, onEdit, onDelete }: EntryRowProps) {
  const typeLabel = ENTRY_TYPE_LABELS[entry.type] ?? entry.type;
  const typeBg = ENTRY_TYPE_BG[entry.type] ?? 'bg-gray-100 text-gray-600';
  const amountColor = entry.amount >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3 hover:bg-muted/30 transition-colors">
      {/* 날짜 */}
      <div className="w-20 shrink-0 text-xs text-muted-foreground">
        {formatDate(entry.transacted_at)}
      </div>

      {/* 타입 뱃지 */}
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${typeBg}`}>
        {typeLabel}
      </span>

      {/* 메모 / 계좌 */}
      <button
        type="button"
        onClick={() => onEdit(entry)}
        className="min-w-0 flex-1 text-left"
      >
        {entry.memo && (
          <p className="truncate text-sm">{entry.memo}</p>
        )}
        {accountName && (
          <p className="truncate text-xs text-muted-foreground">{accountName}</p>
        )}
        {entry.security_id && (
          <p className="truncate text-xs text-muted-foreground">종목: {entry.security_id}</p>
        )}
      </button>

      {/* 금액 */}
      <div className={`shrink-0 text-right font-semibold tabular-nums ${amountColor}`}>
        {entry.amount >= 0 ? '+' : '-'}{formatCurrency(Math.abs(entry.amount), entry.currency)}
      </div>

      {/* 액션 */}
      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={() => onEdit(entry)}
        >
          <Pencil className="h-3.5 w-3.5" />
          <span className="sr-only">수정</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 text-destructive hover:text-destructive"
          onClick={() => onDelete(entry)}
        >
          <Trash2 className="h-3.5 w-3.5" />
          <span className="sr-only">삭제</span>
        </Button>
      </div>
    </div>
  );
}

// ─── Pagination ────────────────────────────────────────────────────────────────

interface PaginationProps {
  page: number;
  total: number;
  perPage: number;
  onPageChange: (page: number) => void;
  onPerPageChange: (perPage: number) => void;
}

function Pagination({ page, total, perPage, onPageChange, onPerPageChange }: PaginationProps) {
  const totalPages = Math.ceil(total / perPage);
  if (total === 0) return null;

  const pages: number[] = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>총 {total.toLocaleString('ko-KR')}건</span>
        <Select
          value={String(perPage)}
          onValueChange={(v) => onPerPageChange(Number(v))}
        >
          <SelectTrigger className="h-7 w-20 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PER_PAGE_OPTIONS.map((n) => (
              <SelectItem key={n} value={String(n)}>{n}개씩</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          className="h-7 w-7 p-0"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </Button>

        {start > 1 && (
          <>
            <Button variant="outline" size="sm" className="h-7 w-7 p-0 text-xs" onClick={() => onPageChange(1)}>1</Button>
            {start > 2 && <span className="px-1 text-muted-foreground">…</span>}
          </>
        )}

        {pages.map((p) => (
          <Button
            key={p}
            variant={p === page ? 'default' : 'outline'}
            size="sm"
            className="h-7 w-7 p-0 text-xs"
            onClick={() => onPageChange(p)}
          >
            {p}
          </Button>
        ))}

        {end < totalPages && (
          <>
            {end < totalPages - 1 && <span className="px-1 text-muted-foreground">…</span>}
            <Button variant="outline" size="sm" className="h-7 w-7 p-0 text-xs" onClick={() => onPageChange(totalPages)}>{totalPages}</Button>
          </>
        )}

        <Button
          variant="outline"
          size="sm"
          className="h-7 w-7 p-0"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

// ─── Filter Bar ────────────────────────────────────────────────────────────────

interface FilterBarProps {
  accountId: string | undefined;
  categoryId: string | null;
  startDate: string;
  endDate: string;
  accountOptions: Array<{ id: string; name: string }>;
  onAccountChange: (id: string | undefined) => void;
  onCategoryChange: (id: string | null) => void;
  onStartDateChange: (v: string) => void;
  onEndDateChange: (v: string) => void;
}

function FilterBar({
  accountId,
  categoryId,
  startDate,
  endDate,
  accountOptions,
  onAccountChange,
  onCategoryChange,
  onStartDateChange,
  onEndDateChange,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      {/* 날짜 범위 */}
      <div className="flex items-center gap-1.5">
        <Input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="h-8 w-36 text-sm"
          placeholder="시작일"
        />
        <span className="text-muted-foreground text-sm">~</span>
        <Input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="h-8 w-36 text-sm"
          placeholder="종료일"
        />
      </div>

      {/* 계좌 필터 */}
      <div className="w-40">
        <Select
          value={accountId ?? '__all__'}
          onValueChange={(v) => onAccountChange(v === '__all__' ? undefined : v)}
        >
          <SelectTrigger className="h-8 text-sm">
            <SelectValue placeholder="전체 계좌" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">전체 계좌</SelectItem>
            {accountOptions.map((a) => (
              <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 카테고리 필터 */}
      <div className="w-44">
        <CategorySelect
          value={categoryId}
          onChange={onCategoryChange}
          placeholder="전체 카테고리"
        />
      </div>
    </div>
  );
}

// ─── Page Component ────────────────────────────────────────────────────────────

export function Component() {
  const [activeTab, setActiveTab] = useState<EntryTab>('all');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [accountId, setAccountId] = useState<string | undefined>(undefined);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const [showCreate, setShowCreate] = useState(false);
  const [editEntryId, setEditEntryId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Entry | null>(null);

  const deleteEntry = useDeleteEntry();
  const deleteEntryGroup = useDeleteEntryGroup();

  const { data: accounts = [] } = useAccounts();

  const filters: EntryFilters = {
    type: TAB_TYPE_MAP[activeTab],
    account_id: accountId,
    category_id: categoryId ?? undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    page,
    per_page: perPage,
  };

  const { data, isLoading, isError, refetch } = useEntries(filters);

  const accountMap = Object.fromEntries(accounts.map((a) => [a.id, a.name]));
  const accountOptions = accounts.map((a) => ({ id: a.id, name: a.name }));

  const handleTabChange = (tab: string) => {
    setActiveTab(tab as EntryTab);
    setPage(1);
    setCategoryId(null);
  };

  const handleAccountChange = (id: string | undefined) => {
    setAccountId(id);
    setPage(1);
  };

  const handleCategoryChange = (id: string | null) => {
    setCategoryId(id);
    setPage(1);
  };

  const handleStartDateChange = (v: string) => {
    setStartDate(v);
    setPage(1);
  };

  const handleEndDateChange = (v: string) => {
    setEndDate(v);
    setPage(1);
  };

  const handlePerPageChange = (n: number) => {
    setPerPage(n);
    setPage(1);
  };

  const handleConfirmDelete = () => {
    if (!deleteTarget) return;
    if (deleteTarget.entry_group_id) {
      deleteEntryGroup.mutate(deleteTarget.entry_group_id);
    } else {
      deleteEntry.mutate(deleteTarget.id);
    }
    setDeleteTarget(null);
  };

  const entries = data?.data ?? [];
  const total = data?.total ?? 0;

  const isGroupDelete = !!deleteTarget?.entry_group_id;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">거래 내역</h1>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          거래 추가
        </Button>
      </div>

      {/* 탭 */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          {(Object.keys(TAB_LABELS) as EntryTab[]).map((tab) => (
            <TabsTrigger key={tab} value={tab}>
              {TAB_LABELS[tab]}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* 필터 바 */}
        <div className="mt-4">
          <FilterBar
            accountId={accountId}
            categoryId={categoryId}
            startDate={startDate}
            endDate={endDate}
            accountOptions={accountOptions}
            onAccountChange={handleAccountChange}
            onCategoryChange={handleCategoryChange}
            onStartDateChange={handleStartDateChange}
            onEndDateChange={handleEndDateChange}
          />
        </div>

        {/* 탭 컨텐츠 (공통 리스트) */}
        {(Object.keys(TAB_LABELS) as EntryTab[]).map((tab) => (
          <TabsContent key={tab} value={tab} className="mt-4 space-y-3">
            {/* 로딩 */}
            {isLoading && (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            )}

            {/* 에러 */}
            {isError && (
              <Card>
                <CardContent className="flex flex-col items-center py-10">
                  <AlertCircle className="mb-3 h-8 w-8 text-muted-foreground" />
                  <p className="text-muted-foreground">거래 내역을 불러올 수 없습니다.</p>
                  <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
                    다시 시도
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* 빈 상태 */}
            {!isLoading && !isError && entries.length === 0 && (
              <Card>
                <CardContent className="flex flex-col items-center py-16">
                  <p className="text-muted-foreground">거래 내역이 없습니다.</p>
                  <Button className="mt-4" onClick={() => setShowCreate(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    거래 추가하기
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* 목록 */}
            {!isLoading && !isError && entries.length > 0 && (
              <div className="space-y-2">
                {entries.map((entry) => (
                  <EntryRow
                    key={entry.id}
                    entry={entry}
                    accountName={accountMap[entry.account_id]}
                    onEdit={(e) => setEditEntryId(e.id)}
                    onDelete={setDeleteTarget}
                  />
                ))}
              </div>
            )}

            {/* 페이지네이션 */}
            {!isLoading && !isError && total > 0 && (
              <Pagination
                page={page}
                total={total}
                perPage={perPage}
                onPageChange={setPage}
                onPerPageChange={handlePerPageChange}
              />
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* 거래 추가 다이얼로그 */}
      <CreateEntryDialog
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
      />

      {/* 거래 수정 다이얼로그 */}
      {editEntryId && (
        <EditEntryDialog
          entryId={editEntryId}
          open={!!editEntryId}
          onClose={() => setEditEntryId(null)}
        />
      )}

      {/* 삭제 확인 다이얼로그 */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="거래를 삭제하시겠습니까?"
        description={isGroupDelete
          ? '이체·매매 양쪽 기록이 함께 삭제됩니다. 이 작업은 되돌릴 수 없습니다.'
          : '이 작업은 되돌릴 수 없습니다.'}
        confirmLabel="삭제"
        onConfirm={handleConfirmDelete}
        variant="destructive"
      />
    </div>
  );
}
