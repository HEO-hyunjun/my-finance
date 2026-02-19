import { useState, useEffect } from 'react';
import type { Transaction, TransactionUpdateRequest, TransactionType } from '@/shared/types';
import { TRANSACTION_TYPE_LABELS } from '@/shared/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';

interface Props {
  transaction: Transaction;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { id: string; data: TransactionUpdateRequest }) => void;
  isLoading?: boolean;
}

export function EditTransactionModal({ transaction, isOpen, onClose, onSubmit, isLoading }: Props) {
  const [type, setType] = useState<TransactionType>(transaction.type);
  const [quantity, setQuantity] = useState(String(transaction.quantity));
  const [unitPrice, setUnitPrice] = useState(String(transaction.unit_price));
  const [memo, setMemo] = useState(transaction.memo ?? '');
  const [transactedAt, setTransactedAt] = useState(transaction.transacted_at.slice(0, 10));

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setType(transaction.type);
    setQuantity(String(transaction.quantity));
    setUnitPrice(String(transaction.unit_price));
    setMemo(transaction.memo ?? '');
    setTransactedAt(transaction.transacted_at.slice(0, 10));
  }, [transaction]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quantity || !unitPrice || !transactedAt) return;

    onSubmit({
      id: transaction.id,
      data: {
        type,
        quantity: Number(quantity),
        unit_price: Number(unitPrice),
        memo: memo || undefined,
        transacted_at: transactedAt,
      },
    });
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>거래 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>자산</Label>
            <p className="text-sm text-muted-foreground">{transaction.asset_name}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-tx-type">유형</Label>
            <select
              id="edit-tx-type"
              value={type}
              onChange={(e) => setType(e.target.value as TransactionType)}
              required
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              {(
                Object.entries(TRANSACTION_TYPE_LABELS) as [TransactionType, string][]
              ).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-tx-quantity">수량</Label>
            <Input
              id="edit-tx-quantity"
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="0"
              required
              min={0}
              step="any"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-tx-unit-price">단가</Label>
            <Input
              id="edit-tx-unit-price"
              type="number"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
              placeholder="0"
              required
              min={0}
              step="any"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-tx-memo">메모</Label>
            <Input
              id="edit-tx-memo"
              type="text"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="메모 (선택)"
              maxLength={500}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-tx-date">일시</Label>
            <Input
              id="edit-tx-date"
              type="date"
              value={transactedAt}
              onChange={(e) => setTransactedAt(e.target.value)}
              required
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              취소
            </Button>
            <Button
              type="submit"
              disabled={isLoading || !quantity || !unitPrice}
              className="flex-1"
            >
              {isLoading ? '저장 중...' : '수정'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
