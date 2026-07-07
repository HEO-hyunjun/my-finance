import { useState } from 'react';
import {
  useEntryDetail,
  useEntryGroup,
  useUpdateEntry,
  useUpdateEntryGroup,
  useDeleteEntry,
  useDeleteEntryGroup,
} from '@/features/entries/api';
import { useAccounts } from '@/features/accounts/api';
import { CategorySelect } from '@/features/categories/ui/CategorySelect';
import type { Entry, EntryGroup, EntryType } from '@/entities/entry/model/types';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/shared/ui/dialog';

const INCOME_TYPES: EntryType[] = ['income', 'dividend', 'interest'];
const EXPENSE_TYPES: EntryType[] = ['expense', 'fee'];

function toLocalDatetimeString(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

interface Props {
  entryId: string;
  open: boolean;
  onClose: () => void;
}

export function EditEntryDialog({ entryId, open, onClose }: Props) {
  const { data: entry, isLoading } = useEntryDetail(entryId);
  const groupId = entry?.entry_group_id ?? null;
  const { data: group, isLoading: groupLoading } = useEntryGroup(groupId);

  const loading = isLoading || (!!groupId && groupLoading);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>거래 수정</DialogTitle>
        </DialogHeader>
        {loading || !entry ? (
          <div className="space-y-3">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : groupId && group ? (
          group.group_type === 'transfer' ? (
            <TransferEditBody group={group} onClose={onClose} />
          ) : (
            <TradeEditBody group={group} onClose={onClose} />
          )
        ) : (
          <GeneralEditBody entry={entry} onClose={onClose} />
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── 일반 수입/지출 ────────────────────────────────────────────────────────────

function GeneralEditBody({ entry, onClose }: { entry: Entry; onClose: () => void }) {
  const [amount, setAmount] = useState(String(Math.abs(Number(entry.amount))));
  const [memo, setMemo] = useState(entry.memo ?? '');
  const [categoryId, setCategoryId] = useState<string | null>(entry.category_id);
  const [transactedAt, setTransactedAt] = useState(toLocalDatetimeString(new Date(entry.transacted_at)));
  const [confirmDelete, setConfirmDelete] = useState(false);

  const updateEntry = useUpdateEntry();
  const deleteEntry = useDeleteEntry();

  const isIncomeType = INCOME_TYPES.includes(entry.type);
  const isExpenseType = EXPENSE_TYPES.includes(entry.type);
  const showCategory = isIncomeType || isExpenseType;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let signedAmount: number | undefined;
    if (amount) {
      const abs = Math.abs(Number(amount));
      signedAmount = isExpenseType ? -abs : abs;
    }
    updateEntry.mutate(
      {
        id: entry.id,
        amount: signedAmount,
        memo: memo || null,
        category_id: categoryId,
        transacted_at: transactedAt ? new Date(transactedAt).toISOString() : undefined,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label>금액</Label>
        <Input type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} />
      </div>
      {showCategory && (
        <div className="space-y-1.5">
          <Label>카테고리</Label>
          <CategorySelect
            direction={isIncomeType ? 'income' : 'expense'}
            value={categoryId}
            onChange={setCategoryId}
          />
        </div>
      )}
      <div className="space-y-1.5">
        <Label>메모</Label>
        <Input value={memo} onChange={(e) => setMemo(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label>날짜/시간</Label>
        <Input type="datetime-local" value={transactedAt} onChange={(e) => setTransactedAt(e.target.value)} />
      </div>
      <DialogFooter className="flex-col-reverse gap-2 sm:flex-row sm:justify-between">
        <Button type="button" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => setConfirmDelete(true)}>
          삭제
        </Button>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onClose}>취소</Button>
          <Button type="submit" disabled={updateEntry.isPending}>
            {updateEntry.isPending ? '저장 중...' : '저장'}
          </Button>
        </div>
      </DialogFooter>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="거래를 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={() => deleteEntry.mutate(entry.id, { onSuccess: onClose })}
        variant="destructive"
      />
    </form>
  );
}

// ─── 이체 그룹 ─────────────────────────────────────────────────────────────────

function TransferEditBody({ group, onClose }: { group: EntryGroup; onClose: () => void }) {
  const outEntry = group.entries.find((e) => e.type === 'transfer_out') ?? group.entries[0];
  const inEntry = group.entries.find((e) => e.type === 'transfer_in') ?? group.entries[1];
  const isCrossCurrency = !!outEntry && !!inEntry && outEntry.currency !== inEntry.currency;

  const [amount, setAmount] = useState(outEntry ? String(Math.abs(Number(outEntry.amount))) : '');
  const [targetAmount, setTargetAmount] = useState(inEntry ? String(Math.abs(Number(inEntry.amount))) : '');
  const [memo, setMemo] = useState(outEntry?.memo ?? '');
  const [transactedAt, setTransactedAt] = useState(
    outEntry ? toLocalDatetimeString(new Date(outEntry.transacted_at)) : '',
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: accounts = [] } = useAccounts();
  const updateGroup = useUpdateEntryGroup();
  const deleteGroup = useDeleteEntryGroup();

  const sourceName = accounts.find((a) => a.id === outEntry?.account_id)?.name;
  const targetName = accounts.find((a) => a.id === inEntry?.account_id)?.name;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount) return;
    if (isCrossCurrency && !targetAmount) return;
    updateGroup.mutate(
      {
        id: group.id,
        amount: Number(amount),
        target_amount: isCrossCurrency ? Number(targetAmount) : undefined,
        memo: memo || null,
        transacted_at: transactedAt ? new Date(transactedAt).toISOString() : undefined,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {(sourceName || targetName) && (
        <p className="text-sm text-muted-foreground">
          {sourceName ?? '출금 계좌'} → {targetName ?? '입금 계좌'}
        </p>
      )}
      <div className="space-y-1.5">
        <Label>보내는 금액{outEntry ? ` (${outEntry.currency})` : ''}</Label>
        <Input type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} />
      </div>
      {isCrossCurrency && (
        <div className="space-y-1.5">
          <Label>받는 금액 ({inEntry!.currency})</Label>
          <Input type="number" min="0" value={targetAmount} onChange={(e) => setTargetAmount(e.target.value)} />
        </div>
      )}
      <div className="space-y-1.5">
        <Label>메모</Label>
        <Input value={memo} onChange={(e) => setMemo(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label>날짜/시간</Label>
        <Input type="datetime-local" value={transactedAt} onChange={(e) => setTransactedAt(e.target.value)} />
      </div>
      <DialogFooter className="flex-col-reverse gap-2 sm:flex-row sm:justify-between">
        <Button type="button" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => setConfirmDelete(true)}>
          삭제
        </Button>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onClose}>취소</Button>
          <Button type="submit" disabled={updateGroup.isPending}>
            {updateGroup.isPending ? '저장 중...' : '저장'}
          </Button>
        </div>
      </DialogFooter>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="이체를 삭제하시겠습니까?"
        description="이체 양쪽 기록이 함께 삭제됩니다. 이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={() => deleteGroup.mutate(group.id, { onSuccess: onClose })}
        variant="destructive"
      />
    </form>
  );
}

// ─── 매매 그룹 ─────────────────────────────────────────────────────────────────

function TradeEditBody({ group, onClose }: { group: EntryGroup; onClose: () => void }) {
  const primary = group.entries.find((e) => e.quantity != null) ?? group.entries[0];
  const tradeLabel = primary?.type === 'sell' ? '매도' : '매수';

  const [quantity, setQuantity] = useState(primary?.quantity != null ? String(Math.abs(Number(primary.quantity))) : '');
  const [unitPrice, setUnitPrice] = useState(primary?.unit_price != null ? String(primary.unit_price) : '');
  const [fee, setFee] = useState(String(primary?.fee ?? 0));
  const [memo, setMemo] = useState(primary?.memo ?? '');
  const [transactedAt, setTransactedAt] = useState(
    primary ? toLocalDatetimeString(new Date(primary.transacted_at)) : '',
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  const updateGroup = useUpdateEntryGroup();
  const deleteGroup = useDeleteEntryGroup();

  const total = (parseFloat(quantity) || 0) * (parseFloat(unitPrice) || 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quantity || !unitPrice) return;
    updateGroup.mutate(
      {
        id: group.id,
        quantity: Number(quantity),
        unit_price: Number(unitPrice),
        fee: fee ? Number(fee) : 0,
        memo: memo || null,
        transacted_at: transactedAt ? new Date(transactedAt).toISOString() : undefined,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-muted-foreground">{tradeLabel}{primary ? ` · ${primary.currency}` : ''}</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>수량</Label>
          <Input type="number" min="0" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>단가</Label>
          <Input type="number" min="0" step="any" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} />
        </div>
      </div>
      {total > 0 && (
        <p className="text-sm text-muted-foreground">
          예상 금액: <span className="font-medium text-foreground">{total.toLocaleString('ko-KR')} {primary?.currency ?? ''}</span>
        </p>
      )}
      <div className="space-y-1.5">
        <Label>수수료</Label>
        <Input type="number" min="0" step="any" value={fee} onChange={(e) => setFee(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label>메모</Label>
        <Input value={memo} onChange={(e) => setMemo(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label>날짜/시간</Label>
        <Input type="datetime-local" value={transactedAt} onChange={(e) => setTransactedAt(e.target.value)} />
      </div>
      <DialogFooter className="flex-col-reverse gap-2 sm:flex-row sm:justify-between">
        <Button type="button" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => setConfirmDelete(true)}>
          삭제
        </Button>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onClose}>취소</Button>
          <Button type="submit" disabled={updateGroup.isPending}>
            {updateGroup.isPending ? '저장 중...' : '저장'}
          </Button>
        </div>
      </DialogFooter>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="매매를 삭제하시겠습니까?"
        description="매매 기록이 삭제됩니다. 이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={() => deleteGroup.mutate(group.id, { onSuccess: onClose })}
        variant="destructive"
      />
    </form>
  );
}
