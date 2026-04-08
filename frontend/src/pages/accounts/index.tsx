import { useState, useCallback } from 'react';
import {
  Plus,
  ChevronDown,
  ChevronUp,
  Pencil,
  Trash2,
  SlidersHorizontal,
  AlertCircle,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import {
  useAccounts,
  useAccountSummary,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
  useAdjustBalance,
} from '@/features/accounts/api';
import type { Account, AccountType, InterestType } from '@/entities/account/model/types';
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

// ─── 상수 ────────────────────────────────────────────────────────────────────

const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  cash: '현금',
  deposit: '예금',
  savings: '적금',
  parking: '파킹',
  investment: '투자',
};

const ACCOUNT_TYPE_ORDER: AccountType[] = ['cash', 'deposit', 'savings', 'parking', 'investment'];

const ACCOUNT_TYPE_COLORS: Record<AccountType, string> = {
  cash: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  deposit: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  savings: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
  parking: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  investment: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
};

const INTEREST_TYPE_LABELS: Record<InterestType, string> = {
  simple: '단리',
  compound: '복리',
};

const NEEDS_INTEREST = new Set<AccountType>(['deposit', 'savings', 'parking']);

// ─── 유틸 ─────────────────────────────────────────────────────────────────────

function formatCurrency(amount: number, currency: string): string {
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

function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

// ─── 초기 폼 상태 ─────────────────────────────────────────────────────────────

interface AccountFormState {
  account_type: AccountType;
  name: string;
  currency: string;
  institution: string;
  interest_rate: string;
  interest_type: InterestType | '';
  start_date: string;
  maturity_date: string;
  tax_rate: string;
  monthly_amount: string;
}

function emptyForm(): AccountFormState {
  return {
    account_type: 'cash',
    name: '',
    currency: 'KRW',
    institution: '',
    interest_rate: '',
    interest_type: '',
    start_date: '',
    maturity_date: '',
    tax_rate: '',
    monthly_amount: '',
  };
}

function accountToForm(account: Account): AccountFormState {
  return {
    account_type: account.account_type,
    name: account.name,
    currency: account.currency,
    institution: account.institution ?? '',
    interest_rate: account.interest_rate != null ? String(account.interest_rate) : '',
    interest_type: account.interest_type ?? '',
    start_date: account.start_date ?? '',
    maturity_date: account.maturity_date ?? '',
    tax_rate: account.tax_rate != null ? String(account.tax_rate) : '',
    monthly_amount: account.monthly_amount != null ? String(account.monthly_amount) : '',
  };
}

// ─── AccountFormFields ────────────────────────────────────────────────────────

interface AccountFormFieldsProps {
  form: AccountFormState;
  isCreate: boolean;
  onChange: (field: keyof AccountFormState, value: string) => void;
}

function AccountFormFields({ form, isCreate, onChange }: AccountFormFieldsProps) {
  const needsInterest = NEEDS_INTEREST.has(form.account_type);
  const isSavings = form.account_type === 'savings';

  return (
    <div className="space-y-4">
      {isCreate && (
        <div className="space-y-1.5">
          <Label htmlFor="account_type">계좌 유형 *</Label>
          <Select
            value={form.account_type}
            onValueChange={(v) => onChange('account_type', v)}
          >
            <SelectTrigger id="account_type" className="w-full">
              <SelectValue placeholder="유형 선택" />
            </SelectTrigger>
            <SelectContent>
              {ACCOUNT_TYPE_ORDER.map((type) => (
                <SelectItem key={type} value={type}>
                  {ACCOUNT_TYPE_LABELS[type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="name">계좌명 *</Label>
        <Input
          id="name"
          value={form.name}
          onChange={(e) => onChange('name', e.target.value)}
          placeholder="예: 국민은행 보통예금"
        />
      </div>

      {isCreate && (
        <div className="space-y-1.5">
          <Label htmlFor="currency">통화</Label>
          <Input
            id="currency"
            value={form.currency}
            onChange={(e) => onChange('currency', e.target.value.toUpperCase())}
            placeholder="KRW"
          />
        </div>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="institution">금융기관</Label>
        <Input
          id="institution"
          value={form.institution}
          onChange={(e) => onChange('institution', e.target.value)}
          placeholder="예: 국민은행"
        />
      </div>

      {needsInterest && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="interest_rate">금리 (%)</Label>
              <Input
                id="interest_rate"
                type="number"
                min="0"
                step="0.01"
                value={form.interest_rate}
                onChange={(e) => onChange('interest_rate', e.target.value)}
                placeholder="3.5"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="interest_type">이자 방식</Label>
              <Select
                value={form.interest_type}
                onValueChange={(v) => onChange('interest_type', v)}
              >
                <SelectTrigger id="interest_type" className="w-full">
                  <SelectValue placeholder="선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="simple">단리</SelectItem>
                  <SelectItem value="compound">복리</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="start_date">시작일</Label>
              <Input
                id="start_date"
                type="date"
                value={form.start_date}
                onChange={(e) => onChange('start_date', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="maturity_date">만기일</Label>
              <Input
                id="maturity_date"
                type="date"
                value={form.maturity_date}
                onChange={(e) => onChange('maturity_date', e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="tax_rate">세율 (%)</Label>
            <Input
              id="tax_rate"
              type="number"
              min="0"
              step="0.1"
              value={form.tax_rate}
              onChange={(e) => onChange('tax_rate', e.target.value)}
              placeholder="15.4"
            />
          </div>

          {isSavings && (
            <div className="space-y-1.5">
              <Label htmlFor="monthly_amount">월 납입액</Label>
              <Input
                id="monthly_amount"
                type="number"
                min="0"
                value={form.monthly_amount}
                onChange={(e) => onChange('monthly_amount', e.target.value)}
                placeholder="300000"
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── CreateAccountDialog ──────────────────────────────────────────────────────

interface CreateAccountDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

function CreateAccountDialog({ isOpen, onClose }: CreateAccountDialogProps) {
  const [form, setForm] = useState<AccountFormState>(emptyForm);
  const createAccount = useCreateAccount();

  const handleChange = useCallback((field: keyof AccountFormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;

    createAccount.mutate(
      {
        account_type: form.account_type,
        name: form.name.trim(),
        currency: form.currency || 'KRW',
        institution: form.institution || null,
        interest_rate: form.interest_rate ? Number(form.interest_rate) : null,
        interest_type: (form.interest_type as InterestType) || null,
        start_date: form.start_date || null,
        maturity_date: form.maturity_date || null,
        tax_rate: form.tax_rate ? Number(form.tax_rate) : null,
        monthly_amount: form.monthly_amount ? Number(form.monthly_amount) : null,
      },
      {
        onSuccess: () => {
          setForm(emptyForm());
          onClose();
        },
      },
    );
  };

  const handleClose = () => {
    setForm(emptyForm());
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>계좌 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <AccountFormFields form={form} isCreate onChange={handleChange} />
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={handleClose}>
              취소
            </Button>
            <Button type="submit" disabled={createAccount.isPending || !form.name.trim()}>
              {createAccount.isPending ? '추가 중...' : '추가'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── EditAccountDialog ────────────────────────────────────────────────────────

interface EditAccountDialogProps {
  account: Account;
  isOpen: boolean;
  onClose: () => void;
}

function EditAccountDialog({ account, isOpen, onClose }: EditAccountDialogProps) {
  const [form, setForm] = useState<AccountFormState>(() => accountToForm(account));
  const updateAccount = useUpdateAccount();

  const handleChange = useCallback((field: keyof AccountFormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;

    updateAccount.mutate(
      {
        id: account.id,
        name: form.name.trim(),
        institution: form.institution || null,
        interest_rate: form.interest_rate ? Number(form.interest_rate) : null,
        interest_type: (form.interest_type as InterestType) || null,
        start_date: form.start_date || null,
        maturity_date: form.maturity_date || null,
        tax_rate: form.tax_rate ? Number(form.tax_rate) : null,
        monthly_amount: form.monthly_amount ? Number(form.monthly_amount) : null,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>계좌 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <AccountFormFields form={form} isCreate={false} onChange={handleChange} />
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={updateAccount.isPending || !form.name.trim()}>
              {updateAccount.isPending ? '수정 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── AdjustBalanceDialog ──────────────────────────────────────────────────────

interface AdjustBalanceDialogProps {
  account: Account;
  currentBalance: number;
  isOpen: boolean;
  onClose: () => void;
}

function AdjustBalanceDialog({ account, currentBalance, isOpen, onClose }: AdjustBalanceDialogProps) {
  const [targetBalance, setTargetBalance] = useState(String(currentBalance));
  const [memo, setMemo] = useState('');
  const adjustBalance = useAdjustBalance();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const target = Number(targetBalance);
    if (isNaN(target)) return;

    adjustBalance.mutate(
      { id: account.id, target_balance: target, memo: memo || null },
      {
        onSuccess: () => {
          setTargetBalance('');
          setMemo('');
          onClose();
        },
      },
    );
  };

  const handleClose = () => {
    setTargetBalance(String(currentBalance));
    setMemo('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>잔액 조정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>현재 잔액</Label>
            <p className="text-sm text-muted-foreground">
              {formatCurrency(currentBalance, account.currency)}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="target_balance">목표 잔액 *</Label>
            <Input
              id="target_balance"
              type="number"
              value={targetBalance}
              onChange={(e) => setTargetBalance(e.target.value)}
              placeholder="0"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="memo">메모</Label>
            <Input
              id="memo"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="잔액 조정 사유"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              취소
            </Button>
            <Button type="submit" disabled={adjustBalance.isPending || !targetBalance}>
              {adjustBalance.isPending ? '조정 중...' : '조정'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── AccountDetailPanel ───────────────────────────────────────────────────────

interface AccountDetailPanelProps {
  account: Account;
  onEdit: () => void;
  onDelete: () => void;
}

function AccountDetailPanel({ account, onEdit, onDelete }: AccountDetailPanelProps) {
  const [showAdjust, setShowAdjust] = useState(false);
  const { data: summary, isLoading } = useAccountSummary(account.id);

  return (
    <div className="mt-3 border-t pt-3 space-y-4">
      {/* 잔액 섹션 */}
      {isLoading ? (
        <Skeleton className="h-12 w-full" />
      ) : summary ? (
        <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
          <div>
            <p className="text-xs text-muted-foreground">잔액</p>
            <p className="text-xl font-bold">
              {formatCurrency(summary.balance, summary.currency)}
            </p>
            {summary.cash_balance != null && summary.cash_balance !== summary.balance && (
              <p className="text-xs text-muted-foreground">
                현금: {formatCurrency(summary.cash_balance, summary.currency)}
              </p>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAdjust(true)}
          >
            <SlidersHorizontal className="mr-1.5 h-3.5 w-3.5" />
            잔액 조정
          </Button>
        </div>
      ) : null}

      {/* 계좌 상세 정보 */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        {account.institution && (
          <>
            <span className="text-muted-foreground">금융기관</span>
            <span>{account.institution}</span>
          </>
        )}
        {account.interest_rate != null && (
          <>
            <span className="text-muted-foreground">금리</span>
            <span>
              {account.interest_rate}%
              {account.interest_type && (
                <span className="ml-1 text-xs text-muted-foreground">
                  ({INTEREST_TYPE_LABELS[account.interest_type]})
                </span>
              )}
            </span>
          </>
        )}
        {account.tax_rate != null && (
          <>
            <span className="text-muted-foreground">세율</span>
            <span>{account.tax_rate}%</span>
          </>
        )}
        {account.start_date && (
          <>
            <span className="text-muted-foreground">시작일</span>
            <span>{account.start_date}</span>
          </>
        )}
        {account.maturity_date && (
          <>
            <span className="text-muted-foreground">만기일</span>
            <span>{account.maturity_date}</span>
          </>
        )}
        {account.monthly_amount != null && (
          <>
            <span className="text-muted-foreground">월 납입액</span>
            <span>{formatCurrency(account.monthly_amount, account.currency)}</span>
          </>
        )}
      </div>

      {/* 보유 종목 (투자 계좌) */}
      {account.account_type === 'investment' && summary?.holdings && summary.holdings.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">보유 종목</p>
          <div className="space-y-1.5">
            {summary.holdings.map((h) => (
              <div
                key={h.security_id}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium">{h.name}</span>
                  <span className="ml-1.5 text-xs text-muted-foreground">{h.symbol}</span>
                  <p className="text-xs text-muted-foreground">
                    {h.quantity.toLocaleString('ko-KR')}주 · 평균 {formatCurrency(h.avg_price, h.currency)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{formatCurrency(h.value, h.currency)}</p>
                  <p
                    className={`flex items-center justify-end gap-0.5 text-xs ${
                      h.profit_loss >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {h.profit_loss >= 0 ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    {formatPercent(h.profit_loss_rate)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 액션 버튼 */}
      <div className="flex gap-2 pt-1">
        <Button variant="outline" size="sm" onClick={onEdit}>
          <Pencil className="mr-1.5 h-3.5 w-3.5" />
          수정
        </Button>
        <Button variant="outline" size="sm" className="text-destructive hover:text-destructive" onClick={onDelete}>
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
          삭제
        </Button>
      </div>

      {summary && (
        <AdjustBalanceDialog
          account={account}
          currentBalance={summary.balance}
          isOpen={showAdjust}
          onClose={() => setShowAdjust(false)}
        />
      )}
    </div>
  );
}

// ─── AccountCard ──────────────────────────────────────────────────────────────

interface AccountCardProps {
  account: Account;
  onDelete: (id: string) => void;
}

function AccountCard({ account, onDelete }: AccountCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showEdit, setShowEdit] = useState(false);

  return (
    <div className="rounded-lg border bg-card">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${ACCOUNT_TYPE_COLORS[account.account_type]}`}
          >
            {ACCOUNT_TYPE_LABELS[account.account_type]}
          </span>
          <div>
            <p className="font-medium leading-tight">{account.name}</p>
            {account.institution && (
              <p className="text-xs text-muted-foreground">{account.institution}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded border px-1.5 py-0.5 text-xs text-muted-foreground">
            {account.currency}
          </span>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          <AccountDetailPanel
            account={account}
            onEdit={() => setShowEdit(true)}
            onDelete={() => onDelete(account.id)}
          />
        </div>
      )}

      <EditAccountDialog
        account={account}
        isOpen={showEdit}
        onClose={() => setShowEdit(false)}
      />
    </div>
  );
}

// ─── AccountTypeSection ───────────────────────────────────────────────────────

interface AccountTypeSectionProps {
  type: AccountType;
  accounts: Account[];
  onDelete: (id: string) => void;
}

function AccountTypeSection({ type, accounts, onDelete }: AccountTypeSectionProps) {
  if (accounts.length === 0) return null;

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <h2 className="text-base font-semibold">{ACCOUNT_TYPE_LABELS[type]}</h2>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {accounts.length}
        </span>
      </div>
      <div className="space-y-2">
        {accounts.map((account) => (
          <AccountCard key={account.id} account={account} onDelete={onDelete} />
        ))}
      </div>
    </section>
  );
}

// ─── Page Component ───────────────────────────────────────────────────────────

export function Component() {
  const { data: accounts = [], isLoading, isError, refetch } = useAccounts();
  const deleteAccount = useDeleteAccount();

  const [showCreate, setShowCreate] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleOpenCreate = useCallback(() => setShowCreate(true), []);
  const handleCloseCreate = useCallback(() => setShowCreate(false), []);

  const handleDeleteRequest = useCallback((id: string) => {
    setConfirmDelete(id);
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (confirmDelete) {
      deleteAccount.mutate(confirmDelete);
      setConfirmDelete(null);
    }
  }, [confirmDelete, deleteAccount]);

  // 계좌 유형별 그룹화
  const grouped = ACCOUNT_TYPE_ORDER.reduce<Record<AccountType, Account[]>>(
    (acc, type) => {
      acc[type] = accounts.filter((a) => a.account_type === type);
      return acc;
    },
    { cash: [], deposit: [], savings: [], parking: [], investment: [] },
  );

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">계좌 관리</h1>
        <Button onClick={handleOpenCreate}>
          <Plus className="mr-2 h-4 w-4" />
          계좌 추가
        </Button>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ))}
        </div>
      )}

      {/* 에러 */}
      {isError && (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <AlertCircle className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">계좌 정보를 불러올 수 없습니다.</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
              다시 시도
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 계좌 목록 */}
      {!isLoading && !isError && (
        <>
          {accounts.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center py-16">
                <p className="text-muted-foreground">등록된 계좌가 없습니다.</p>
                <Button className="mt-4" onClick={handleOpenCreate}>
                  <Plus className="mr-2 h-4 w-4" />
                  첫 계좌 추가하기
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              {ACCOUNT_TYPE_ORDER.map((type) => (
                <AccountTypeSection
                  key={type}
                  type={type}
                  accounts={grouped[type]}
                  onDelete={handleDeleteRequest}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* 계좌 추가 모달 */}
      <CreateAccountDialog isOpen={showCreate} onClose={handleCloseCreate} />

      {/* 삭제 확인 모달 */}
      <ConfirmDialog
        open={confirmDelete !== null}
        onOpenChange={(open) => { if (!open) setConfirmDelete(null); }}
        title="계좌를 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다. 관련된 거래 내역도 함께 삭제될 수 있습니다."
        confirmLabel="삭제"
        onConfirm={handleConfirmDelete}
        variant="destructive"
      />
    </div>
  );
}
