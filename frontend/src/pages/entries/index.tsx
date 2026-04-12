import { useState, useCallback } from 'react';
import { Plus, AlertCircle, Trash2, Pencil, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  useEntries,
  useCreateEntry,
  useUpdateEntry,
  useDeleteEntry,
  useTransfer,
  useTrade,
} from '@/features/entries/api';
import { useAccounts } from '@/features/accounts/api';
import { CategorySelect } from '@/features/categories/ui/CategorySelect';
import type { EntryFilters, Entry, EntryType } from '@/entities/entry/model/types';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/ui/dialog';
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

const INCOME_TYPES: EntryType[] = ['income', 'dividend', 'interest'];
const EXPENSE_TYPES: EntryType[] = ['expense', 'fee'];

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

function toLocalDatetimeString(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// ─── General Entry Form ────────────────────────────────────────────────────────

interface GeneralFormState {
  account_id: string;
  type: 'income' | 'expense';
  amount: string;
  category_id: string | null;
  memo: string;
  transacted_at: string;
}

function emptyGeneralForm(): GeneralFormState {
  return {
    account_id: '',
    type: 'expense',
    amount: '',
    category_id: null,
    memo: '',
    transacted_at: toLocalDatetimeString(),
  };
}

interface GeneralEntryFormProps {
  form: GeneralFormState;
  accountOptions: Array<{ id: string; name: string }>;
  onChange: (field: keyof GeneralFormState, value: string | null) => void;
}

function GeneralEntryForm({ form, accountOptions, onChange }: GeneralEntryFormProps) {
  const categoryDirection = form.type === 'income' ? 'income' : 'expense';

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="ge-account">계좌 *</Label>
        <Select value={form.account_id} onValueChange={(v) => onChange('account_id', v)}>
          <SelectTrigger id="ge-account" className="w-full">
            <SelectValue placeholder="계좌 선택" />
          </SelectTrigger>
          <SelectContent>
            {accountOptions.map((a) => (
              <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ge-type">유형 *</Label>
        <Select value={form.type} onValueChange={(v) => onChange('type', v)}>
          <SelectTrigger id="ge-type" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="income">수입</SelectItem>
            <SelectItem value="expense">지출</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ge-amount">금액 *</Label>
        <Input
          id="ge-amount"
          type="number"
          min="0"
          step="1"
          value={form.amount}
          onChange={(e) => onChange('amount', e.target.value)}
          placeholder="0"
        />
      </div>

      <div className="space-y-1.5">
        <Label>카테고리</Label>
        <CategorySelect
          direction={categoryDirection}
          value={form.category_id}
          onChange={(v) => onChange('category_id', v)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ge-memo">메모</Label>
        <Input
          id="ge-memo"
          value={form.memo}
          onChange={(e) => onChange('memo', e.target.value)}
          placeholder="메모 입력"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ge-date">날짜/시간 *</Label>
        <Input
          id="ge-date"
          type="datetime-local"
          value={form.transacted_at}
          onChange={(e) => onChange('transacted_at', e.target.value)}
        />
      </div>
    </div>
  );
}

// ─── Transfer Form ─────────────────────────────────────────────────────────────

interface TransferFormState {
  source_account_id: string;
  target_account_id: string;
  amount: string;
  memo: string;
  transacted_at: string;
}

function emptyTransferForm(): TransferFormState {
  return {
    source_account_id: '',
    target_account_id: '',
    amount: '',
    memo: '',
    transacted_at: toLocalDatetimeString(),
  };
}

interface TransferFormProps {
  form: TransferFormState;
  accountOptions: Array<{ id: string; name: string }>;
  onChange: (field: keyof TransferFormState, value: string) => void;
}

function TransferForm({ form, accountOptions, onChange }: TransferFormProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="tf-source">출금 계좌 *</Label>
        <Select value={form.source_account_id} onValueChange={(v) => onChange('source_account_id', v)}>
          <SelectTrigger id="tf-source" className="w-full">
            <SelectValue placeholder="출금 계좌 선택" />
          </SelectTrigger>
          <SelectContent>
            {accountOptions.map((a) => (
              <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="tf-target">입금 계좌 *</Label>
        <Select value={form.target_account_id} onValueChange={(v) => onChange('target_account_id', v)}>
          <SelectTrigger id="tf-target" className="w-full">
            <SelectValue placeholder="입금 계좌 선택" />
          </SelectTrigger>
          <SelectContent>
            {accountOptions.map((a) => (
              <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="tf-amount">금액 *</Label>
        <Input
          id="tf-amount"
          type="number"
          min="0"
          step="1"
          value={form.amount}
          onChange={(e) => onChange('amount', e.target.value)}
          placeholder="0"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="tf-memo">메모</Label>
        <Input
          id="tf-memo"
          value={form.memo}
          onChange={(e) => onChange('memo', e.target.value)}
          placeholder="메모 입력"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="tf-date">날짜/시간 *</Label>
        <Input
          id="tf-date"
          type="datetime-local"
          value={form.transacted_at}
          onChange={(e) => onChange('transacted_at', e.target.value)}
        />
      </div>
    </div>
  );
}

// ─── Trade Form ────────────────────────────────────────────────────────────────

interface TradeFormState {
  account_id: string;
  security_id: string;
  trade_type: 'buy' | 'sell';
  quantity: string;
  unit_price: string;
  fee: string;
  memo: string;
  transacted_at: string;
}

function emptyTradeForm(): TradeFormState {
  return {
    account_id: '',
    security_id: '',
    trade_type: 'buy',
    quantity: '',
    unit_price: '',
    fee: '0',
    memo: '',
    transacted_at: toLocalDatetimeString(),
  };
}

interface TradeFormProps {
  form: TradeFormState;
  accountOptions: Array<{ id: string; name: string }>;
  onChange: (field: keyof TradeFormState, value: string) => void;
}

function TradeForm({ form, accountOptions, onChange }: TradeFormProps) {
  const qty = parseFloat(form.quantity) || 0;
  const price = parseFloat(form.unit_price) || 0;
  const total = qty * price;

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="trade-account">투자 계좌 *</Label>
        <Select value={form.account_id} onValueChange={(v) => onChange('account_id', v)}>
          <SelectTrigger id="trade-account" className="w-full">
            <SelectValue placeholder="계좌 선택" />
          </SelectTrigger>
          <SelectContent>
            {accountOptions.map((a) => (
              <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="trade-security">종목 코드 / ID *</Label>
        <Input
          id="trade-security"
          value={form.security_id}
          onChange={(e) => onChange('security_id', e.target.value)}
          placeholder="예: 005930 (삼성전자)"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="trade-type">매매 구분 *</Label>
        <Select value={form.trade_type} onValueChange={(v) => onChange('trade_type', v)}>
          <SelectTrigger id="trade-type" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="buy">매수</SelectItem>
            <SelectItem value="sell">매도</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="trade-qty">수량 *</Label>
          <Input
            id="trade-qty"
            type="number"
            min="0"
            step="any"
            value={form.quantity}
            onChange={(e) => onChange('quantity', e.target.value)}
            placeholder="0"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="trade-price">단가 *</Label>
          <Input
            id="trade-price"
            type="number"
            min="0"
            step="any"
            value={form.unit_price}
            onChange={(e) => onChange('unit_price', e.target.value)}
            placeholder="0"
          />
        </div>
      </div>

      {total > 0 && (
        <p className="text-sm text-muted-foreground">
          예상 금액: <span className="font-medium text-foreground">{total.toLocaleString('ko-KR')}원</span>
        </p>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="trade-fee">수수료</Label>
        <Input
          id="trade-fee"
          type="number"
          min="0"
          step="any"
          value={form.fee}
          onChange={(e) => onChange('fee', e.target.value)}
          placeholder="0"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="trade-memo">메모</Label>
        <Input
          id="trade-memo"
          value={form.memo}
          onChange={(e) => onChange('memo', e.target.value)}
          placeholder="메모 입력"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="trade-date">날짜/시간 *</Label>
        <Input
          id="trade-date"
          type="datetime-local"
          value={form.transacted_at}
          onChange={(e) => onChange('transacted_at', e.target.value)}
        />
      </div>
    </div>
  );
}

// ─── Create Entry Dialog ───────────────────────────────────────────────────────

type CreateMode = 'general' | 'transfer' | 'trade';

const CREATE_MODE_LABELS: Record<CreateMode, string> = {
  general: '수입/지출',
  transfer: '이체',
  trade: '매매',
};

interface CreateEntryDialogProps {
  isOpen: boolean;
  onClose: () => void;
  accountOptions: Array<{ id: string; name: string }>;
  investmentAccountOptions: Array<{ id: string; name: string }>;
}

function CreateEntryDialog({
  isOpen,
  onClose,
  accountOptions,
  investmentAccountOptions,
}: CreateEntryDialogProps) {
  const [mode, setMode] = useState<CreateMode>('general');
  const [generalForm, setGeneralForm] = useState<GeneralFormState>(emptyGeneralForm);
  const [transferForm, setTransferForm] = useState<TransferFormState>(emptyTransferForm);
  const [tradeForm, setTradeForm] = useState<TradeFormState>(emptyTradeForm);

  const createEntry = useCreateEntry();
  const transfer = useTransfer();
  const trade = useTrade();

  const isPending = createEntry.isPending || transfer.isPending || trade.isPending;

  const handleGeneralChange = useCallback((field: keyof GeneralFormState, value: string | null) => {
    setGeneralForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleTransferChange = useCallback((field: keyof TransferFormState, value: string) => {
    setTransferForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleTradeChange = useCallback((field: keyof TradeFormState, value: string) => {
    setTradeForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const resetForms = () => {
    setGeneralForm(emptyGeneralForm());
    setTransferForm(emptyTransferForm());
    setTradeForm(emptyTradeForm());
  };

  const handleClose = () => {
    resetForms();
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === 'general') {
      if (!generalForm.account_id || !generalForm.amount) return;
      createEntry.mutate(
        {
          account_id: generalForm.account_id,
          type: generalForm.type,
          amount: Number(generalForm.amount),
          category_id: generalForm.category_id || null,
          memo: generalForm.memo || null,
          transacted_at: new Date(generalForm.transacted_at).toISOString(),
        },
        { onSuccess: handleClose },
      );
    } else if (mode === 'transfer') {
      if (!transferForm.source_account_id || !transferForm.target_account_id || !transferForm.amount) return;
      transfer.mutate(
        {
          source_account_id: transferForm.source_account_id,
          target_account_id: transferForm.target_account_id,
          amount: Number(transferForm.amount),
          memo: transferForm.memo || null,
          transacted_at: transferForm.transacted_at ? new Date(transferForm.transacted_at).toISOString() : null,
        },
        { onSuccess: handleClose },
      );
    } else {
      if (!tradeForm.account_id || !tradeForm.security_id || !tradeForm.quantity || !tradeForm.unit_price) return;
      trade.mutate(
        {
          account_id: tradeForm.account_id,
          security_id: tradeForm.security_id,
          trade_type: tradeForm.trade_type,
          quantity: Number(tradeForm.quantity),
          unit_price: Number(tradeForm.unit_price),
          fee: tradeForm.fee ? Number(tradeForm.fee) : 0,
          memo: tradeForm.memo || null,
          transacted_at: tradeForm.transacted_at ? new Date(tradeForm.transacted_at).toISOString() : null,
        },
        { onSuccess: handleClose },
      );
    }
  };

  const isSubmitDisabled = () => {
    if (isPending) return true;
    if (mode === 'general') return !generalForm.account_id || !generalForm.amount;
    if (mode === 'transfer') return !transferForm.source_account_id || !transferForm.target_account_id || !transferForm.amount;
    return !tradeForm.account_id || !tradeForm.security_id || !tradeForm.quantity || !tradeForm.unit_price;
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>거래 추가</DialogTitle>
        </DialogHeader>

        {/* 모드 탭 */}
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          {(Object.keys(CREATE_MODE_LABELS) as CreateMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-all ${
                mode === m
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {CREATE_MODE_LABELS[m]}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          {mode === 'general' && (
            <GeneralEntryForm
              form={generalForm}
              accountOptions={accountOptions}
              onChange={handleGeneralChange}
            />
          )}
          {mode === 'transfer' && (
            <TransferForm
              form={transferForm}
              accountOptions={accountOptions}
              onChange={handleTransferChange}
            />
          )}
          {mode === 'trade' && (
            <TradeForm
              form={tradeForm}
              accountOptions={investmentAccountOptions.length > 0 ? investmentAccountOptions : accountOptions}
              onChange={handleTradeChange}
            />
          )}

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={handleClose}>
              취소
            </Button>
            <Button type="submit" disabled={isSubmitDisabled()}>
              {isPending ? '처리 중...' : '추가'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Entry Dialog ─────────────────────────────────────────────────────────

interface EditEntryDialogProps {
  entry: Entry;
  isOpen: boolean;
  onClose: () => void;
}

function EditEntryDialog({ entry, isOpen, onClose }: EditEntryDialogProps) {
  const [amount, setAmount] = useState(String(entry.amount));
  const [memo, setMemo] = useState(entry.memo ?? '');
  const [categoryId, setCategoryId] = useState<string | null>(entry.category_id);
  const [transactedAt, setTransactedAt] = useState(
    toLocalDatetimeString(new Date(entry.transacted_at))
  );

  const updateEntry = useUpdateEntry();

  const isIncomeType = INCOME_TYPES.includes(entry.type);
  const isExpenseType = EXPENSE_TYPES.includes(entry.type);
  const showCategory = isIncomeType || isExpenseType;
  const categoryDirection = isIncomeType ? 'income' : 'expense';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateEntry.mutate(
      {
        id: entry.id,
        amount: amount ? Number(amount) : undefined,
        memo: memo || null,
        category_id: categoryId,
        transacted_at: transactedAt ? new Date(transactedAt).toISOString() : undefined,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>거래 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="edit-amount">금액</Label>
            <Input
              id="edit-amount"
              type="number"
              min="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>

          {showCategory && (
            <div className="space-y-1.5">
              <Label>카테고리</Label>
              <CategorySelect
                direction={categoryDirection}
                value={categoryId}
                onChange={setCategoryId}
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="edit-memo">메모</Label>
            <Input
              id="edit-memo"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="edit-date">날짜/시간</Label>
            <Input
              id="edit-date"
              type="datetime-local"
              value={transactedAt}
              onChange={(e) => setTransactedAt(e.target.value)}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={updateEntry.isPending}>
              {updateEntry.isPending ? '수정 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Entry Row ─────────────────────────────────────────────────────────────────

interface EntryRowProps {
  entry: Entry;
  accountName?: string;
  onEdit: (entry: Entry) => void;
  onDelete: (id: string) => void;
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
      <div className="min-w-0 flex-1">
        {entry.memo && (
          <p className="truncate text-sm">{entry.memo}</p>
        )}
        {accountName && (
          <p className="truncate text-xs text-muted-foreground">{accountName}</p>
        )}
        {entry.security_id && (
          <p className="truncate text-xs text-muted-foreground">종목: {entry.security_id}</p>
        )}
      </div>

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
          onClick={() => onDelete(entry.id)}
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
  const [editEntry, setEditEntry] = useState<Entry | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const deleteEntry = useDeleteEntry();

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
  const investmentAccountOptions = accounts
    .filter((a) => a.account_type === 'investment')
    .map((a) => ({ id: a.id, name: a.name }));

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
    if (deleteId) {
      deleteEntry.mutate(deleteId);
      setDeleteId(null);
    }
  };

  const entries = data?.data ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-6">
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
                    onEdit={setEditEntry}
                    onDelete={setDeleteId}
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
        accountOptions={accountOptions}
        investmentAccountOptions={investmentAccountOptions}
      />

      {/* 거래 수정 다이얼로그 */}
      {editEntry && (
        <EditEntryDialog
          entry={editEntry}
          isOpen={!!editEntry}
          onClose={() => setEditEntry(null)}
        />
      )}

      {/* 삭제 확인 다이얼로그 */}
      <ConfirmDialog
        open={deleteId !== null}
        onOpenChange={(open) => { if (!open) setDeleteId(null); }}
        title="거래를 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={handleConfirmDelete}
        variant="destructive"
      />
    </div>
  );
}
