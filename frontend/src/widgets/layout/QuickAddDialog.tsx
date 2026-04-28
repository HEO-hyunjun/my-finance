import { useState, useCallback, useRef } from 'react';
import { useCreateEntry, useTrade } from '@/features/entries/api';
import { useAccounts } from '@/features/accounts/api';
import { useCategories } from '@/features/categories/api';
import {
  SecuritySearchInput,
  type SelectedSecurity,
} from '@/features/securities/ui/SecuritySearchInput';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select';

const CURRENCIES = ['KRW', 'USD', 'JPY', 'EUR', 'GBP'] as const;

export type QuickAddMode = 'income' | 'expense' | 'trade' | null;

interface QuickAddDialogProps {
  mode: QuickAddMode;
  onClose: () => void;
}

function toLocalDatetime(date: Date = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`;
}

export function QuickAddDialog({ mode, onClose }: QuickAddDialogProps) {
  const isOpen = mode !== null;
  const title = mode === 'income' ? '수입 추가' : mode === 'expense' ? '지출 추가' : '매매 추가';

  return (
    <Dialog open={isOpen} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-sm max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {mode && <QuickAddBody key={mode} mode={mode} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function QuickAddBody({
  mode,
  onClose,
}: {
  mode: Exclude<QuickAddMode, null>;
  onClose: () => void;
}) {
  // general form (income/expense)
  const [accountId, setAccountId] = useState('');
  const [amount, setAmount] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [memo, setMemo] = useState('');
  const [transactedAt, setTransactedAt] = useState(toLocalDatetime());

  // trade form
  const [tradeAccountId, setTradeAccountId] = useState('');
  const [tradeSelected, setTradeSelected] = useState<SelectedSecurity | null>(null);
  const [tradeCurrency, setTradeCurrency] = useState<string>('KRW');
  const [tradeType, setTradeType] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState('');
  const [unitPrice, setUnitPrice] = useState('');
  const [fee, setFee] = useState('0');
  const [tradeMemo, setTradeMemo] = useState('');
  const [tradeDate, setTradeDate] = useState(toLocalDatetime());
  const priceDirtyRef = useRef(false);

  const { data: accounts = [] } = useAccounts();
  const catDirection = mode === 'income' ? 'income' : 'expense';
  const { data: categories = [] } = useCategories(catDirection);
  const createEntry = useCreateEntry();
  const tradeApi = useTrade();

  const investmentAccounts = accounts.filter((a) => a.account_type === 'investment');
  const isPending = createEntry.isPending || tradeApi.isPending;

  const handleSecuritySelect = useCallback((sec: SelectedSecurity) => {
    setTradeSelected(sec);
    setTradeCurrency(sec.currency);
    if (!priceDirtyRef.current && sec.current_price != null) {
      setUnitPrice(String(sec.current_price));
    }
  }, []);

  const handleSecurityClear = useCallback(() => {
    setTradeSelected(null);
  }, []);

  const handleSubmitEntry = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!accountId || !amount || mode === 'trade') return;
      createEntry.mutate(
        {
          account_id: accountId,
          type: mode,
          amount: Number(amount),
          category_id: categoryId || null,
          memo: memo || null,
          transacted_at: new Date(transactedAt).toISOString(),
        },
        { onSuccess: onClose },
      );
    },
    [accountId, amount, mode, categoryId, memo, transactedAt, createEntry, onClose],
  );

  const handleSubmitTrade = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!tradeAccountId || !tradeSelected || !quantity || !unitPrice) return;
      tradeApi.mutate(
        {
          account_id: tradeAccountId,
          security_id: tradeSelected.id,
          trade_type: tradeType,
          quantity: Number(quantity),
          unit_price: Number(unitPrice),
          currency: tradeCurrency,
          fee: fee ? Number(fee) : 0,
          memo: tradeMemo || null,
          transacted_at: tradeDate ? new Date(tradeDate).toISOString() : null,
        },
        { onSuccess: onClose },
      );
    },
    [tradeAccountId, tradeSelected, tradeCurrency, tradeType, quantity, unitPrice, fee, tradeMemo, tradeDate, tradeApi, onClose],
  );

  const tradeTotal = (parseFloat(quantity) || 0) * (parseFloat(unitPrice) || 0);

  if (mode !== 'trade') {
    return (
      <form onSubmit={handleSubmitEntry} className="space-y-4">
        <div className="space-y-1.5">
          <Label>계좌 *</Label>
          <Select value={accountId} onValueChange={setAccountId}>
            <SelectTrigger><SelectValue placeholder="계좌 선택" /></SelectTrigger>
            <SelectContent>
              {accounts.map((a) => (
                <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>금액 *</Label>
          <Input type="number" min="0" placeholder="0" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>카테고리</Label>
          <Select value={categoryId} onValueChange={setCategoryId}>
            <SelectTrigger><SelectValue placeholder="카테고리 선택" /></SelectTrigger>
            <SelectContent>
              {categories.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.icon ? `${c.icon} ` : ''}{c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>메모</Label>
          <Input placeholder="메모 입력" value={memo} onChange={(e) => setMemo(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>날짜/시간 *</Label>
          <Input type="datetime-local" value={transactedAt} onChange={(e) => setTransactedAt(e.target.value)} />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>취소</Button>
          <Button type="submit" disabled={!accountId || !amount || isPending}>
            {isPending ? '처리 중...' : '추가'}
          </Button>
        </DialogFooter>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmitTrade} className="space-y-4">
      <div className="space-y-1.5">
        <Label>투자 계좌 *</Label>
        <Select value={tradeAccountId} onValueChange={setTradeAccountId}>
          <SelectTrigger><SelectValue placeholder="계좌 선택" /></SelectTrigger>
          <SelectContent>
            {(investmentAccounts.length > 0 ? investmentAccounts : accounts).map((a) => (
              <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label>종목 *</Label>
        <SecuritySearchInput
          value={tradeSelected}
          onSelect={handleSecuritySelect}
          onClear={handleSecurityClear}
        />
      </div>
      <div className="space-y-1.5">
        <Label>매매 구분 *</Label>
        <Select value={tradeType} onValueChange={(v) => setTradeType(v as 'buy' | 'sell')}>
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
          <Input type="number" min="0" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="0" />
        </div>
        <div className="space-y-1.5">
          <Label>단가 *</Label>
          <Input
            type="number" min="0" step="any" value={unitPrice}
            onChange={(e) => { priceDirtyRef.current = true; setUnitPrice(e.target.value); }}
            placeholder="0"
          />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label>통화 *</Label>
        <Select value={tradeCurrency} onValueChange={setTradeCurrency}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {CURRENCIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
          </SelectContent>
        </Select>
      </div>
      {tradeTotal > 0 && (
        <p className="text-sm text-muted-foreground">
          예상 금액: <span className="font-medium text-foreground">
            {tradeTotal.toLocaleString('ko-KR')} {tradeCurrency}
          </span>
        </p>
      )}
      <div className="space-y-1.5">
        <Label>수수료</Label>
        <Input type="number" min="0" step="any" value={fee} onChange={(e) => setFee(e.target.value)} placeholder="0" />
      </div>
      <div className="space-y-1.5">
        <Label>메모</Label>
        <Input value={tradeMemo} onChange={(e) => setTradeMemo(e.target.value)} placeholder="메모 입력" />
      </div>
      <div className="space-y-1.5">
        <Label>날짜/시간 *</Label>
        <Input type="datetime-local" value={tradeDate} onChange={(e) => setTradeDate(e.target.value)} />
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>취소</Button>
        <Button type="submit" disabled={!tradeAccountId || !tradeSelected || !quantity || !unitPrice || isPending}>
          {isPending ? '처리 중...' : tradeType === 'buy' ? '매수' : '매도'}
        </Button>
      </DialogFooter>
    </form>
  );
}
