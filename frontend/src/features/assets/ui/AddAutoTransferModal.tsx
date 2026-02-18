import { useState } from 'react';
import type { Asset, AutoTransferCreateRequest } from '@/shared/types';
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
  onSubmit: (data: AutoTransferCreateRequest) => void;
  assets: Asset[];
  isLoading?: boolean;
}

export function AddAutoTransferModal({ isOpen, onClose, onSubmit, assets, isLoading }: Props) {
  const [name, setName] = useState('');
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [amount, setAmount] = useState('');
  const [transferDay, setTransferDay] = useState(1);

  const resetForm = () => {
    setName('');
    setSourceId('');
    setTargetId('');
    setAmount('');
    setTransferDay(1);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      source_asset_id: sourceId,
      target_asset_id: targetId,
      amount: parseFloat(amount),
      transfer_day: transferDay,
    });
    resetForm();
  };

  const targetAssets = assets.filter((a) => a.id !== sourceId);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>자동이체 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>이름</Label>
            <Input
              type="text"
              placeholder="예: 적금 자동이체"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
            />
          </div>

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

          <div className="grid grid-cols-2 gap-3">
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
              <Label>이체일</Label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                value={transferDay}
                onChange={(e) => setTransferDay(Number(e.target.value))}
              >
                {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
                  <option key={d} value={d}>
                    매월 {d}일
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={isLoading || !sourceId || !targetId || !name}>
              {isLoading ? '저장 중...' : '등록'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
