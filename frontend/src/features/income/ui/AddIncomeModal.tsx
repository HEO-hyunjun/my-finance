import { useState } from 'react';
import type { AssetHolding, IncomeCreateRequest, IncomeType } from '@/shared/types';
import { INCOME_TYPE_LABELS } from '@/shared/types';
import { useAssetSummary } from '@/features/assets/api';
import { useCreateIncome } from '../api';

const ALLOWED_TARGET_TYPES = new Set(['cash_krw', 'deposit', 'parking']);

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function AddIncomeModal({ isOpen, onClose }: Props) {
  const [type, setType] = useState<IncomeType>('salary');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurringDay, setRecurringDay] = useState('');
  const [receivedAt, setReceivedAt] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [targetAssetId, setTargetAssetId] = useState('');

  const createIncome = useCreateIncome();
  const { data: assetSummary } = useAssetSummary();
  const targetAssets = (assetSummary?.holdings ?? []).filter(
    (h: AssetHolding) => ALLOWED_TARGET_TYPES.has(h.asset_type),
  );

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !description || !receivedAt) return;

    const payload: IncomeCreateRequest = {
      type,
      amount: Number(amount),
      description,
      is_recurring: isRecurring,
      recurring_day: isRecurring && recurringDay ? Number(recurringDay) : undefined,
      received_at: receivedAt,
      target_asset_id: targetAssetId || undefined,
    };

    createIncome.mutate(payload, {
      onSuccess: () => {
        // 리셋
        setType('salary');
        setAmount('');
        setDescription('');
        setIsRecurring(false);
        setRecurringDay('');
        setReceivedAt(new Date().toISOString().slice(0, 10));
        setTargetAssetId('');
        onClose();
      },
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6">
        <h2 className="mb-4 text-lg font-bold">수입 추가</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 수입 유형 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              유형
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as IncomeType)}
              required
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            >
              {(
                Object.entries(INCOME_TYPE_LABELS) as [IncomeType, string][]
              ).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* 금액 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              금액
            </label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              required
              min={1}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          {/* 설명 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              설명
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="월급, 프리랜서 수입 등"
              required
              maxLength={500}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          {/* 정기 수입 체크박스 */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is-recurring"
              checked={isRecurring}
              onChange={(e) => setIsRecurring(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-500"
            />
            <label
              htmlFor="is-recurring"
              className="text-sm font-medium text-gray-700"
            >
              정기 수입
            </label>
          </div>

          {/* 정기일 (정기 수입일 때만 표시) */}
          {isRecurring && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                매월 수입일
              </label>
              <input
                type="number"
                value={recurringDay}
                onChange={(e) => setRecurringDay(e.target.value)}
                placeholder="25"
                min={1}
                max={31}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          )}

          {/* 수입일 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              수입일
            </label>
            <input
              type="date"
              value={receivedAt}
              onChange={(e) => setReceivedAt(e.target.value)}
              required
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          {/* 입금 자산 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              입금 자산 (선택)
            </label>
            <select
              value={targetAssetId}
              onChange={(e) => setTargetAssetId(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">선택 안함</option>
              {targetAssets.map((a: AssetHolding) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({(a.principal ?? 0).toLocaleString()}원)
                </option>
              ))}
            </select>
          </div>

          {/* 버튼 */}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded border border-gray-300 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={createIncome.isPending || !amount || !description}
              className="flex-1 rounded bg-blue-500 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
            >
              {createIncome.isPending ? '저장 중...' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
