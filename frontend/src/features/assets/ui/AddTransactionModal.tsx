import { useState, useCallback, useMemo } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import type { Asset, TransactionType, CurrencyType, TransactionCreateRequest, TransferRequest } from '@/shared/types';
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
  onTransfer?: (data: TransferRequest) => void;
  assets: Asset[];
  isLoading?: boolean;
}

const CASH_LIKE_TYPES = new Set(['cash_krw', 'cash_usd', 'parking']);
const DEPOSIT_TYPES = new Set(['cash_krw', 'cash_usd', 'parking', 'deposit', 'savings']);

const USD_TYPES = new Set(['cash_usd']);

function getCurrency(asset: Asset): 'USD' | 'KRW' {
  return USD_TYPES.has(asset.asset_type) ? 'USD' : 'KRW';
}

function getTxTypesForAsset(assetType?: string): TransactionType[] {
  if (!assetType) return ['buy', 'sell', 'exchange', 'deposit', 'withdraw', 'transfer'];
  if (CASH_LIKE_TYPES.has(assetType)) return ['deposit', 'withdraw', 'transfer'];
  if (assetType === 'deposit' || assetType === 'savings') return ['deposit', 'withdraw'];
  return ['buy', 'sell', 'exchange'];
}

function getTxTypeColor(t: TransactionType, selected: boolean) {
  if (!selected) return 'border-border hover:bg-accent';
  switch (t) {
    case 'buy': case 'deposit': return 'border-green-500 bg-green-500/10 text-green-700 dark:text-green-400';
    case 'sell': case 'withdraw': return 'border-red-500 bg-red-500/10 text-red-700 dark:text-red-400';
    default: return 'border-primary bg-primary/10 text-primary';
  }
}

export function AddTransactionModal({ isOpen, onClose, onSubmit, onTransfer, assets, isLoading }: Props) {
  const [assetId, setAssetId] = useState('');
  const [type, setType] = useState<TransactionType>('buy');
  const [quantity, setQuantity] = useState('');
  const [unitPrice, setUnitPrice] = useState('');
  const [currency, setCurrency] = useState<CurrencyType>('KRW');
  const [exchangeRate, setExchangeRate] = useState('');
  const [fee, setFee] = useState('');
  const [memo, setMemo] = useState('');
  const [sourceAssetId, setSourceAssetId] = useState('');
  const [targetAssetId, setTargetAssetId] = useState('');
  const [depositAmount, setDepositAmount] = useState('');
  const [transactedAt, setTransactedAt] = useState(
    new Date().toISOString().slice(0, 16),
  );

  const [isFetchingPrice, setIsFetchingPrice] = useState(false);

  const selectedAsset = assets.find((a) => a.id === assetId);
  const isForeign = selectedAsset?.asset_type === 'stock_us' || selectedAsset?.asset_type === 'cash_usd';
  const hasSymbol = !!selectedAsset?.symbol;
  const isCashLike = selectedAsset ? DEPOSIT_TYPES.has(selectedAsset.asset_type) : false;
  const isTransfer = type === 'transfer';
  const txTypes = getTxTypesForAsset(selectedAsset?.asset_type);

  // 출처 계좌 후보: 현금성 자산 중 현재 선택된 자산 제외
  const sourceAssets = assets.filter(
    (a) => CASH_LIKE_TYPES.has(a.asset_type) && a.id !== assetId,
  );

  // 이체 대상 계좌: 현금성 자산 중 출금 계좌 제외
  const targetAssets = assets.filter(
    (a) => CASH_LIKE_TYPES.has(a.asset_type) && a.id !== assetId,
  );

  const targetAsset = assets.find((a) => a.id === targetAssetId);
  const isCrossCurrency = useMemo(() => {
    if (!selectedAsset || !targetAsset) return false;
    return getCurrency(selectedAsset) !== getCurrency(targetAsset);
  }, [selectedAsset, targetAsset]);
  const targetCurrency = targetAsset ? getCurrency(targetAsset) : null;

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

  const resetForm = () => {
    setAssetId('');
    setType('buy');
    setQuantity('');
    setUnitPrice('');
    setCurrency('KRW');
    setExchangeRate('');
    setFee('');
    setMemo('');
    setSourceAssetId('');
    setTargetAssetId('');
    setDepositAmount('');
    setTransactedAt(new Date().toISOString().slice(0, 16));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // 이체 처리
    if (isTransfer && onTransfer) {
      const amt = parseFloat(quantity);
      let txExchangeRate: number | undefined;
      if (isCrossCurrency && depositAmount) {
        const dep = parseFloat(depositAmount);
        const sourceCur = selectedAsset ? getCurrency(selectedAsset) : 'KRW';
        if (sourceCur === 'KRW') {
          txExchangeRate = amt / dep;
        } else {
          txExchangeRate = dep / amt;
        }
      }
      onTransfer({
        source_asset_id: assetId,
        target_asset_id: targetAssetId,
        amount: amt,
        exchange_rate: txExchangeRate,
        memo: memo || undefined,
        transacted_at: new Date(transactedAt).toISOString(),
      });
      resetForm();
      return;
    }

    const data: TransactionCreateRequest = {
      asset_id: assetId,
      type,
      quantity: parseFloat(quantity),
      unit_price: isCashLike ? 1 : parseFloat(unitPrice),
      currency,
      exchange_rate: isForeign && exchangeRate ? parseFloat(exchangeRate) : undefined,
      fee: fee ? parseFloat(fee) : undefined,
      memo: memo || undefined,
      transacted_at: new Date(transactedAt).toISOString(),
    };

    if ((type === 'buy' || type === 'deposit') && sourceAssetId) {
      data.source_asset_id = sourceAssetId;
    }

    onSubmit(data);
    resetForm();
  };

  const handleAssetChange = (newAssetId: string) => {
    setAssetId(newAssetId);
    const asset = assets.find((a) => a.id === newAssetId);
    if (!asset) return;

    if (asset.asset_type === 'stock_us' || asset.asset_type === 'cash_usd') {
      setCurrency('USD');
    } else {
      setCurrency('KRW');
    }

    // 자산 유형에 맞는 기본 거래 유형 설정
    const validTypes = getTxTypesForAsset(asset.asset_type);
    if (!validTypes.includes(type)) {
      setType(validTypes[0]);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>거래 기록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>자산</Label>
            <select
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={assetId}
              onChange={(e) => handleAssetChange(e.target.value)}
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

          <div className="space-y-1.5">
            <Label>거래 유형</Label>
            <div className="flex gap-2">
              {txTypes.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={cn(
                    'flex-1 rounded-lg border px-3 py-2 text-sm transition',
                    getTxTypeColor(t, type === t),
                  )}
                  onClick={() => setType(t)}
                >
                  {TRANSACTION_TYPE_LABELS[t]}
                </button>
              ))}
            </div>
          </div>

          {/* 현금성 자산: 금액만 입력 */}
          {isCashLike ? (
            <>
              <div className="space-y-1.5">
                <Label>금액 ({currency})</Label>
                <Input
                  type="number"
                  step="any"
                  min="0"
                  placeholder="금액을 입력하세요"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  required
                />
              </div>
              {/* 달러 현금: 매입/매도 환율 입력 */}
              {isForeign && !isTransfer && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label>환율 (USD/KRW)</Label>
                    <button
                      type="button"
                      className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                      onClick={async () => {
                        setIsFetchingPrice(true);
                        try {
                          const res = await apiClient.get('/v1/market/exchange-rate');
                          setExchangeRate(String(res.data.rate));
                        } catch { /* ignore */ } finally {
                          setIsFetchingPrice(false);
                        }
                      }}
                      disabled={isFetchingPrice}
                    >
                      {isFetchingPrice ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      현재 환율
                    </button>
                  </div>
                  <Input
                    type="number"
                    step="any"
                    min="0"
                    placeholder="1380"
                    value={exchangeRate}
                    onChange={(e) => setExchangeRate(e.target.value)}
                  />
                  {quantity && exchangeRate && (
                    <p className="text-xs text-muted-foreground">
                      ≈ {(parseFloat(quantity) * parseFloat(exchangeRate)).toLocaleString()}원
                    </p>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
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
                <div className="space-y-1.5">
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
                <div className="space-y-1.5">
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
            </>
          )}

          {/* 매수/입금 시 출처 계좌 선택 */}
          {(type === 'buy' || type === 'deposit') && sourceAssets.length > 0 && (
            <div className="space-y-1.5">
              <Label>출처 계좌 (선택)</Label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                value={sourceAssetId}
                onChange={(e) => setSourceAssetId(e.target.value)}
              >
                <option value="">출처 없음</option>
                {sourceAssets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                선택 시 해당 계좌에서 출금 처리됩니다
              </p>
            </div>
          )}

          {/* 이체 시 입금 계좌 + 입금 금액 */}
          {isTransfer && (
            <>
              <div className="space-y-1.5">
                <Label>입금 계좌</Label>
                <select
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                  value={targetAssetId}
                  onChange={(e) => setTargetAssetId(e.target.value)}
                  required
                >
                  <option value="">계좌를 선택하세요</option>
                  {targetAssets.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({getCurrency(a)})
                    </option>
                  ))}
                </select>
              </div>
              {isCrossCurrency && (
                <div className="space-y-1.5">
                  <Label>입금 금액 {targetCurrency && `(${targetCurrency})`}</Label>
                  <Input
                    type="number"
                    step="any"
                    min="0"
                    placeholder={targetCurrency === 'USD' ? '예: 100.00' : '예: 135000'}
                    value={depositAmount}
                    onChange={(e) => setDepositAmount(e.target.value)}
                    required
                  />
                </div>
              )}
            </>
          )}

          <div className="grid grid-cols-2 gap-3">
            {!isCashLike && (
              <div className="space-y-1.5">
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
            )}
            <div className={cn('space-y-1.5', isCashLike && 'col-span-2')}>
              <Label>거래일시</Label>
              <Input
                type="datetime-local"
                value={transactedAt}
                onChange={(e) => setTransactedAt(e.target.value)}
                required
              />
            </div>
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
            <Button
              type="submit"
              disabled={isLoading || !assetId || (isTransfer && (!targetAssetId || (isCrossCurrency && !depositAmount)))}
            >
              {isLoading ? '저장 중...' : isTransfer ? '이체' : '저장'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
