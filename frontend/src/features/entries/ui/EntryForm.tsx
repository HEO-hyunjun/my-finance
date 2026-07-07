import { useState, useCallback, useRef } from 'react';
import { useCreateEntry, useTransfer, useTrade } from '@/features/entries/api';
import { useAccounts } from '@/features/accounts/api';
import { CategorySelect } from '@/features/categories/ui/CategorySelect';
import {
  SecuritySearchInput,
  type SelectedSecurity,
} from '@/features/securities/ui/SecuritySearchInput';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { DialogFooter } from '@/shared/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/ui/select';

const CURRENCIES = ['KRW', 'USD', 'JPY', 'EUR', 'GBP'] as const;

type Mode = 'general' | 'transfer' | 'trade';

const MODE_LABELS: Record<Mode, string> = {
  general: '수입/지출',
  transfer: '이체',
  trade: '매매',
};

function now() {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

interface Props {
  onSuccess: () => void;
  onCancel: () => void;
}

export function EntryForm({ onSuccess, onCancel }: Props) {
  const [mode, setMode] = useState<Mode>('general');

  // general
  const [gAccount, setGAccount] = useState('');
  const [gType, setGType] = useState<'income' | 'expense' | 'dividend' | 'fee'>('expense');
  const [gAmount, setGAmount] = useState('');
  const [gCategory, setGCategory] = useState<string | null>(null);
  const [gMemo, setGMemo] = useState('');
  const [gDate, setGDate] = useState(now());

  // transfer
  const [tSource, setTSource] = useState('');
  const [tTarget, setTTarget] = useState('');
  const [tAmount, setTAmount] = useState('');
  const [tTargetAmount, setTTargetAmount] = useState('');
  const [tMemo, setTMemo] = useState('');
  const [tDate, setTDate] = useState(now());

  // trade
  const [trAccount, setTrAccount] = useState('');
  const [trSelected, setTrSelected] = useState<SelectedSecurity | null>(null);
  const [trCurrency, setTrCurrency] = useState<string>('KRW');
  const [trType, setTrType] = useState<'buy' | 'sell'>('buy');
  const [trQty, setTrQty] = useState('');
  const [trPrice, setTrPrice] = useState('');
  const [trFee, setTrFee] = useState('0');
  const [trMemo, setTrMemo] = useState('');
  const [trDate, setTrDate] = useState(now());
  const priceDirtyRef = useRef(false);

  const { data: accounts = [] } = useAccounts();
  const investmentAccounts = accounts.filter((a) => a.account_type === 'investment');

  const createEntry = useCreateEntry();
  const transfer = useTransfer();
  const trade = useTrade();
  const isPending = createEntry.isPending || transfer.isPending || trade.isPending;

  const sourceAccount = accounts.find((a) => a.id === tSource);
  const targetAccount = accounts.find((a) => a.id === tTarget);
  const isCrossCurrency =
    !!sourceAccount && !!targetAccount && sourceAccount.currency !== targetAccount.currency;

  const handleSecuritySelect = useCallback((sec: SelectedSecurity) => {
    setTrSelected(sec);
    setTrCurrency(sec.currency);
    if (!priceDirtyRef.current && sec.current_price != null) {
      setTrPrice(String(sec.current_price));
    }
  }, []);

  const handleSecurityClear = useCallback(() => {
    setTrSelected(null);
  }, []);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'general') {
      if (!gAccount || !gAmount) return;
      createEntry.mutate({
        account_id: gAccount, type: gType, amount: Number(gAmount),
        category_id: gCategory || null, memo: gMemo || null,
        transacted_at: new Date(gDate).toISOString(),
      }, { onSuccess });
    } else if (mode === 'transfer') {
      if (!tSource || !tTarget || !tAmount) return;
      if (isCrossCurrency && !tTargetAmount) return;
      transfer.mutate({
        source_account_id: tSource, target_account_id: tTarget,
        amount: Number(tAmount),
        target_amount: isCrossCurrency ? Number(tTargetAmount) : null,
        memo: tMemo || null,
        transacted_at: tDate ? new Date(tDate).toISOString() : null,
      }, { onSuccess });
    } else {
      if (!trAccount || !trSelected || !trQty || !trPrice) return;
      trade.mutate({
        account_id: trAccount, security_id: trSelected.id, trade_type: trType,
        quantity: Number(trQty), unit_price: Number(trPrice),
        currency: trCurrency,
        fee: trFee ? Number(trFee) : 0, memo: trMemo || null,
        transacted_at: trDate ? new Date(trDate).toISOString() : null,
      }, { onSuccess });
    }
  }, [mode, gAccount, gAmount, gType, gCategory, gMemo, gDate,
      tSource, tTarget, tAmount, tTargetAmount, tMemo, tDate, isCrossCurrency,
      trAccount, trSelected, trCurrency, trType, trQty, trPrice, trFee, trMemo, trDate,
      createEntry, transfer, trade, onSuccess]);

  const tradeTotal = (parseFloat(trQty) || 0) * (parseFloat(trPrice) || 0);

  const isDisabled = () => {
    if (isPending) return true;
    if (mode === 'general') return !gAccount || !gAmount;
    if (mode === 'transfer') return !tSource || !tTarget || !tAmount || (isCrossCurrency && !tTargetAmount);
    return !trAccount || !trSelected || !trQty || !trPrice;
  };

  const submitLabel = () => {
    if (isPending) return '처리 중...';
    if (mode === 'transfer') return '이체';
    if (mode === 'trade') return trType === 'buy' ? '매수' : '매도';
    return '추가';
  };

  return (
    <>
      {/* 모드 탭 */}
      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {(Object.keys(MODE_LABELS) as Mode[]).map((m) => (
          <button key={m} type="button" onClick={() => setMode(m)}
            className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-all ${
              mode === m ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}>
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        {mode === 'general' && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>계좌 *</Label>
              <Select value={gAccount} onValueChange={setGAccount}>
                <SelectTrigger><SelectValue placeholder="계좌 선택" /></SelectTrigger>
                <SelectContent>{accounts.map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>유형 *</Label>
              <Select value={gType} onValueChange={(v) => { setGType(v as 'income' | 'expense' | 'dividend' | 'fee'); setGCategory(null); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="income">수입</SelectItem>
                  <SelectItem value="expense">지출</SelectItem>
                  <SelectItem value="dividend">배당</SelectItem>
                  <SelectItem value="fee">수수료</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>금액 *</Label>
              <Input type="number" min="0" placeholder="0" value={gAmount} onChange={(e) => setGAmount(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>카테고리</Label>
              <CategorySelect
                direction={gType === 'income' || gType === 'dividend' ? 'income' : 'expense'}
                value={gCategory}
                onChange={setGCategory}
              />
            </div>
            <div className="space-y-1.5">
              <Label>메모</Label>
              <Input placeholder="메모 입력" value={gMemo} onChange={(e) => setGMemo(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>날짜/시간 *</Label>
              <Input type="datetime-local" value={gDate} onChange={(e) => setGDate(e.target.value)} />
            </div>
          </div>
        )}

        {mode === 'transfer' && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>출금 계좌 *</Label>
              <Select value={tSource} onValueChange={setTSource}>
                <SelectTrigger><SelectValue placeholder="계좌 선택" /></SelectTrigger>
                <SelectContent>{accounts.map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>입금 계좌 *</Label>
              <Select value={tTarget} onValueChange={setTTarget}>
                <SelectTrigger><SelectValue placeholder="계좌 선택" /></SelectTrigger>
                <SelectContent>{accounts.filter((a) => a.id !== tSource).map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>보내는 금액 *{sourceAccount ? ` (${sourceAccount.currency})` : ''}</Label>
              <Input type="number" min="0" placeholder="0" value={tAmount} onChange={(e) => setTAmount(e.target.value)} />
            </div>
            {isCrossCurrency && (
              <div className="space-y-1.5">
                <Label>받는 금액 * ({targetAccount!.currency})</Label>
                <Input type="number" min="0" placeholder="0" value={tTargetAmount} onChange={(e) => setTTargetAmount(e.target.value)} />
                <p className="text-xs text-muted-foreground">출금/입금 계좌의 통화가 달라 받는 금액이 필요합니다.</p>
              </div>
            )}
            <div className="space-y-1.5">
              <Label>메모</Label>
              <Input placeholder="메모 입력" value={tMemo} onChange={(e) => setTMemo(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>날짜/시간 *</Label>
              <Input type="datetime-local" value={tDate} onChange={(e) => setTDate(e.target.value)} />
            </div>
          </div>
        )}

        {mode === 'trade' && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>투자 계좌 *</Label>
              <Select value={trAccount} onValueChange={setTrAccount}>
                <SelectTrigger><SelectValue placeholder="계좌 선택" /></SelectTrigger>
                <SelectContent>{(investmentAccounts.length > 0 ? investmentAccounts : accounts).map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>종목 *</Label>
              <SecuritySearchInput
                value={trSelected}
                onSelect={handleSecuritySelect}
                onClear={handleSecurityClear}
              />
            </div>
            <div className="space-y-1.5">
              <Label>매매 구분 *</Label>
              <Select value={trType} onValueChange={(v) => setTrType(v as 'buy' | 'sell')}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="buy">매수</SelectItem>
                  <SelectItem value="sell">매도</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>수량 *</Label>
                <Input type="number" min="0" step="any" value={trQty} onChange={(e) => setTrQty(e.target.value)} placeholder="0" />
              </div>
              <div className="space-y-1.5">
                <Label>단가 *</Label>
                <Input
                  type="number" min="0" step="any" value={trPrice}
                  onChange={(e) => { priceDirtyRef.current = true; setTrPrice(e.target.value); }}
                  placeholder="0"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>통화 *</Label>
              <Select value={trCurrency} onValueChange={setTrCurrency}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            {tradeTotal > 0 && (
              <p className="text-sm text-muted-foreground">
                예상 금액: <span className="font-medium text-foreground">
                  {tradeTotal.toLocaleString('ko-KR')} {trCurrency}
                </span>
              </p>
            )}
            <div className="space-y-1.5">
              <Label>수수료</Label>
              <Input type="number" min="0" step="any" value={trFee} onChange={(e) => setTrFee(e.target.value)} placeholder="0" />
            </div>
            <div className="space-y-1.5">
              <Label>메모</Label>
              <Input value={trMemo} onChange={(e) => setTrMemo(e.target.value)} placeholder="메모 입력" />
            </div>
            <div className="space-y-1.5">
              <Label>날짜/시간 *</Label>
              <Input type="datetime-local" value={trDate} onChange={(e) => setTrDate(e.target.value)} />
            </div>
          </div>
        )}

        <DialogFooter className="mt-6">
          <Button type="button" variant="outline" onClick={onCancel}>취소</Button>
          <Button type="submit" disabled={isDisabled()}>{submitLabel()}</Button>
        </DialogFooter>
      </form>
    </>
  );
}
