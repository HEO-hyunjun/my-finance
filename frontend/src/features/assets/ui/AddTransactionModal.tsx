import { useState, useCallback } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import type { Asset, TransactionType, CurrencyType, TransactionCreateRequest } from '@/shared/types';
import { TRANSACTION_TYPE_LABELS } from '@/shared/types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import { cn } from '@/shared/lib/utils';
import { apiClient } from '@/shared/api/client';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: TransactionCreateRequest) => void;
  assets: Asset[];
  isLoading?: boolean;
}

const TX_TYPES: TransactionType[] = ['buy', 'sell', 'exchange'];

export function AddTransactionModal({ isOpen, onClose, onSubmit, assets, isLoading }: Props) {
  const [assetId, setAssetId] = useState('');
  const [type, setType] = useState<TransactionType>('buy');
  const [quantity, setQuantity] = useState('');
  const [unitPrice, setUnitPrice] = useState('');
  const [currency, setCurrency] = useState<CurrencyType>('KRW');
  const [exchangeRate, setExchangeRate] = useState('');
  const [fee, setFee] = useState('');
  const [memo, setMemo] = useState('');
  const [transactedAt, setTransactedAt] = useState(
    new Date().toISOString().slice(0, 16),
  );

  const [isFetchingPrice, setIsFetchingPrice] = useState(false);

  const selectedAsset = assets.find((a) => a.id === assetId);
  const isForeign = selectedAsset?.asset_type === 'stock_us' || selectedAsset?.asset_type === 'cash_usd';
  const hasSymbol = !!selectedAsset?.symbol;

  const handleFetchPrice = useCallback(async () => {
    if (!selectedAsset?.symbol) return;
    setIsFetchingPrice(true);
    try {
      const [priceRes, ...rest] = await Promise.all([
        apiClient.get('/v1/market/price', { params: { symbol: selectedAsset.symbol } }),
        ...(isForeign ? [apiClient.get('/v1/market/exchange-rate')] : []),
      ]);
      setUnitPrice(String(priceRes.data.price));
      if (isForeign && rest[0]) {
        setExchangeRate(String(rest[0].data.rate));
      }
    } catch {
      // silently fail — user can still enter manually
    } finally {
      setIsFetchingPrice(false);
    }
  }, [selectedAsset?.symbol, isForeign]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      asset_id: assetId,
      type,
      quantity: parseFloat(quantity),
      unit_price: parseFloat(unitPrice),
      currency,
      exchange_rate: isForeign && exchangeRate ? parseFloat(exchangeRate) : undefined,
      fee: fee ? parseFloat(fee) : undefined,
      memo: memo || undefined,
      transacted_at: new Date(transactedAt).toISOString(),
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>거래 기록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>자산</Label>
            <select
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={assetId}
              onChange={(e) => {
                setAssetId(e.target.value);
                const asset = assets.find((a) => a.id === e.target.value);
                if (asset?.asset_type === 'stock_us' || asset?.asset_type === 'cash_usd') {
                  setCurrency('USD');
                } else {
                  setCurrency('KRW');
                }
              }}
              required
            >
              <option value="">자산을 선택하세요</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} {a.symbol ? `(${a.symbol})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label>거래 유형</Label>
            <div className="flex gap-2">
              {TX_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={cn(
                    'flex-1 rounded-lg border px-3 py-2 text-sm transition',
                    type === t
                      ? t === 'buy'
                        ? 'border-green-500 bg-green-500/10 text-green-700 dark:text-green-400'
                        : t === 'sell'
                          ? 'border-red-500 bg-red-500/10 text-red-700 dark:text-red-400'
                          : 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:bg-accent',
                  )}
                  onClick={() => setType(t)}
                >
                  {TRANSACTION_TYPE_LABELS[t]}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>수량</Label>
              <Input
                type="number"
                step="any"
                min="0"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                required
              />
            </div>
            <div>
              <div className="flex items-center justify-between">
                <Label>단가 ({currency})</Label>
                {hasSymbol && (
                  <button
                    type="button"
                    className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                    onClick={handleFetchPrice}
                    disabled={isFetchingPrice}
                  >
                    {isFetchingPrice ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3" />
                    )}
                    현재가 불러오기
                  </button>
                )}
              </div>
              <Input
                type="number"
                step="any"
                min="0"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
                required
              />
            </div>
          </div>

          {isForeign && (
            <div>
              <Label>환율 (USD/KRW)</Label>
              <Input
                type="number"
                step="any"
                min="0"
                placeholder="1380"
                value={exchangeRate}
                onChange={(e) => setExchangeRate(e.target.value)}
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>수수료</Label>
              <Input
                type="number"
                step="any"
                min="0"
                placeholder="0"
                value={fee}
                onChange={(e) => setFee(e.target.value)}
              />
            </div>
            <div>
              <Label>거래일시</Label>
              <Input
                type="datetime-local"
                value={transactedAt}
                onChange={(e) => setTransactedAt(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
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
            <Button type="submit" disabled={isLoading || !assetId}>
              {isLoading ? '저장 중...' : '저장'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
