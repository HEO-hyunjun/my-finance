import { useState } from 'react';
import type { Asset, TransferRequest } from '@/shared/types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: TransferRequest) => void;
  assets: Asset[];
  isLoading?: boolean;
}

export function TransferModal({ isOpen, onClose, onSubmit, assets, isLoading }: Props) {
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [amount, setAmount] = useState('');
  const [memo, setMemo] = useState('');
  const [transactedAt, setTransactedAt] = useState(
    new Date().toISOString().slice(0, 16),
  );

  const resetForm = () => {
    setSourceId('');
    setTargetId('');
    setAmount('');
    setMemo('');
    setTransactedAt(new Date().toISOString().slice(0, 16));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      source_asset_id: sourceId,
      target_asset_id: targetId,
      amount: parseFloat(amount),
      memo: memo || undefined,
      transacted_at: new Date(transactedAt).toISOString(),
    });
    resetForm();
  };

  const targetAssets = assets.filter((a) => a.id !== sourceId);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>이체</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>출금 계좌</Label>
            <select
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              required
            >
              <option value="">계좌를 선택하세요</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label>입금 계좌</Label>
            <select
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              required
            >
              <option value="">계좌를 선택하세요</option>
              {targetAssets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label>금액</Label>
            <Input
              type="number"
              step="any"
              min="0"
              placeholder="이체 금액"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label>이체일시</Label>
            <Input
              type="datetime-local"
              value={transactedAt}
              onChange={(e) => setTransactedAt(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label>메모</Label>
            <Input
              type="text"
              placeholder="메모 (선택)"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={isLoading || !sourceId || !targetId}>
              {isLoading ? '이체 중...' : '이체'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
