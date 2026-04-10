import { useState, useEffect, useCallback } from 'react';
import { useCreateEntry, useTransfer, useTrade } from '@/features/entries/api';
import { useAccounts } from '@/features/accounts/api';
import { useCategories } from '@/features/categories/api';
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/shared/ui/dialog';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/ui/select';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

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

export function GlobalCreateEntryDialog({ isOpen, onClose }: Props) {
  const [mode, setMode] = useState<Mode>('general');

  // general
  const [gAccount, setGAccount] = useState('');
  const [gType, setGType] = useState<'income' | 'expense'>('expense');
  const [gAmount, setGAmount] = useState('');
  const [gCategory, setGCategory] = useState('');
  const [gMemo, setGMemo] = useState('');
  const [gDate, setGDate] = useState(now());

  // transfer
  const [tSource, setTSource] = useState('');
  const [tTarget, setTTarget] = useState('');
  const [tAmount, setTAmount] = useState('');
  const [tMemo, setTMemo] = useState('');

  // trade
  const [trAccount, setTrAccount] = useState('');
  const [trSecurity, setTrSecurity] = useState('');
  const [trType, setTrType] = useState<'buy' | 'sell'>('buy');
  const [trQty, setTrQty] = useState('');
  const [trPrice, setTrPrice] = useState('');
  const [trFee, setTrFee] = useState('0');
  const [trMemo, setTrMemo] = useState('');
  const [trDate, setTrDate] = useState(now());

  const { data: accounts = [] } = useAccounts();
  const { data: categories = [] } = useCategories(gType);
  const investmentAccounts = accounts.filter((a) => a.account_type === 'investment');

  const createEntry = useCreateEntry();
  const transfer = useTransfer();
  const trade = useTrade();
  const isPending = createEntry.isPending || transfer.isPending || trade.isPending;

  useEffect(() => {
    if (isOpen) {
      setMode('general');
      setGAccount(''); setGType('expense'); setGAmount(''); setGCategory(''); setGMemo(''); setGDate(now());
      setTSource(''); setTTarget(''); setTAmount(''); setTMemo('');
      setTrAccount(''); setTrSecurity(''); setTrType('buy'); setTrQty(''); setTrPrice(''); setTrFee('0'); setTrMemo(''); setTrDate(now());
    }
  }, [isOpen]);

  const handleClose = useCallback(() => { onClose(); }, [onClose]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'general') {
      if (!gAccount || !gAmount) return;
      createEntry.mutate({
        account_id: gAccount, type: gType, amount: Number(gAmount),
        category_id: gCategory || null, memo: gMemo || null,
        transacted_at: new Date(gDate).toISOString(),
      }, { onSuccess: handleClose });
    } else if (mode === 'transfer') {
      if (!tSource || !tTarget || !tAmount) return;
      transfer.mutate({
        source_account_id: tSource, target_account_id: tTarget,
        amount: Number(tAmount), memo: tMemo || null,
      }, { onSuccess: handleClose });
    } else {
      if (!trAccount || !trSecurity || !trQty || !trPrice) return;
      trade.mutate({
        account_id: trAccount, security_id: trSecurity, trade_type: trType,
        quantity: Number(trQty), unit_price: Number(trPrice),
        fee: trFee ? Number(trFee) : 0, memo: trMemo || null,
        transacted_at: trDate ? new Date(trDate).toISOString() : null,
      }, { onSuccess: handleClose });
    }
  }, [mode, gAccount, gAmount, gType, gCategory, gMemo, gDate, tSource, tTarget, tAmount, tMemo,
      trAccount, trSecurity, trType, trQty, trPrice, trFee, trMemo, trDate,
      createEntry, transfer, trade, handleClose]);

  const tradeTotal = (parseFloat(trQty) || 0) * (parseFloat(trPrice) || 0);

  const isDisabled = () => {
    if (isPending) return true;
    if (mode === 'general') return !gAccount || !gAmount;
    if (mode === 'transfer') return !tSource || !tTarget || !tAmount;
    return !trAccount || !trSecurity || !trQty || !trPrice;
  };

  const submitLabel = () => {
    if (isPending) return '처리 중...';
    if (mode === 'transfer') return '이체';
    if (mode === 'trade') return trType === 'buy' ? '매수' : '매도';
    return '추가';
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>거래 추가</DialogTitle>
        </DialogHeader>

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
                <Select value={gType} onValueChange={(v) => setGType(v as 'income' | 'expense')}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">수입</SelectItem>
                    <SelectItem value="expense">지출</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>금액 *</Label>
                <Input type="number" min="0" placeholder="0" value={gAmount} onChange={(e) => setGAmount(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>카테고리</Label>
                <Select value={gCategory} onValueChange={setGCategory}>
                  <SelectTrigger><SelectValue placeholder="카테고리 선택" /></SelectTrigger>
                  <SelectContent>{categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.icon ? `${c.icon} ` : ''}{c.name}</SelectItem>)}</SelectContent>
                </Select>
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
                <Label>금액 *</Label>
                <Input type="number" min="0" placeholder="0" value={tAmount} onChange={(e) => setTAmount(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>메모</Label>
                <Input placeholder="메모 입력" value={tMemo} onChange={(e) => setTMemo(e.target.value)} />
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
                <Label>종목 ID *</Label>
                <Input value={trSecurity} onChange={(e) => setTrSecurity(e.target.value)} placeholder="종목 UUID" />
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
                  <Input type="number" min="0" step="any" value={trPrice} onChange={(e) => setTrPrice(e.target.value)} placeholder="0" />
                </div>
              </div>
              {tradeTotal > 0 && (
                <p className="text-sm text-muted-foreground">
                  예상 금액: <span className="font-medium text-foreground">{tradeTotal.toLocaleString('ko-KR')}원</span>
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
            <Button type="button" variant="outline" onClick={handleClose}>취소</Button>
            <Button type="submit" disabled={isDisabled()}>{submitLabel()}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
