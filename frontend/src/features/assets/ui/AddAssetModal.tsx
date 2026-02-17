import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';
import { cn } from '@/shared/lib/utils';
import { apiClient } from '@/shared/api/client';
import type { AssetType, AssetCreateRequest, InterestType } from '@/shared/types';
import { ASSET_TYPE_LABELS } from '@/shared/types';

interface SearchResult {
  symbol: string;
  name: string;
  exchange: string | null;
}

function useSymbolSearch(query: string, enabled: boolean) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (!enabled || query.length < 2) {
      setResults([]);
      return;
    }

    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setIsSearching(true);
      try {
        const { data } = await apiClient.get('/v1/market/search', { params: { query } });
        setResults(data.results ?? []);
      } catch {
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 400);

    return () => clearTimeout(timerRef.current);
  }, [query, enabled]);

  return { results, isSearching };
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: AssetCreateRequest) => void;
  isLoading?: boolean;
}

const ASSET_TYPES: AssetType[] = [
  'stock_kr', 'stock_us', 'gold', 'cash_krw', 'cash_usd',
  'deposit', 'savings', 'parking',
];

export function AddAssetModal({ isOpen, onClose, onSubmit, isLoading }: Props) {
  const [assetType, setAssetType] = useState<AssetType>('stock_kr');
  const [symbol, setSymbol] = useState('');
  const [name, setName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [bankName, setBankName] = useState('');
  const [principal, setPrincipal] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [interestType, setInterestType] = useState<InterestType>('simple');
  const [monthlyAmount, setMonthlyAmount] = useState('');
  const [startDate, setStartDate] = useState('');
  const [maturityDate, setMaturityDate] = useState('');
  const [taxRate, setTaxRate] = useState('15.4');
  const searchRef = useRef<HTMLDivElement>(null);

  const needsSymbol = ['stock_kr', 'stock_us', 'gold'].includes(assetType);
  const isDeposit = assetType === 'deposit';
  const isSavings = assetType === 'savings';
  const isParking = assetType === 'parking';
  const isInterestBased = isDeposit || isSavings || isParking;

  const { results: searchResults, isSearching } = useSymbolSearch(searchQuery, needsSymbol && showResults);

  const resetFields = () => {
    setSymbol(''); setName(''); setSearchQuery(''); setShowResults(false);
    setBankName(''); setPrincipal('');
    setInterestRate(''); setInterestType('simple'); setMonthlyAmount('');
    setStartDate(''); setMaturityDate(''); setTaxRate('15.4');
  };

  const handleTypeChange = (type: AssetType) => {
    setAssetType(type);
    resetFields();
  };

  const handleSelectResult = useCallback((result: SearchResult) => {
    setSymbol(result.symbol);
    setName(result.name);
    setSearchQuery('');
    setShowResults(false);
  }, []);

  // 검색 결과 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: AssetCreateRequest = { asset_type: assetType, name };
    if (needsSymbol) data.symbol = symbol;
    if (isInterestBased) {
      data.bank_name = bankName || undefined;
      data.interest_rate = interestRate ? Number(interestRate) : undefined;
      data.tax_rate = taxRate ? Number(taxRate) : undefined;
    }
    if (isDeposit) {
      data.principal = principal ? Number(principal) : undefined;
      data.interest_type = interestType;
      data.start_date = startDate || undefined;
      data.maturity_date = maturityDate || undefined;
    }
    if (isSavings) {
      data.monthly_amount = monthlyAmount ? Number(monthlyAmount) : undefined;
      data.interest_rate = interestRate ? Number(interestRate) : undefined;
      data.start_date = startDate || undefined;
      data.maturity_date = maturityDate || undefined;
    }
    if (isParking) {
      data.principal = principal ? Number(principal) : undefined;
    }
    onSubmit(data);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
        <DialogHeader>
          <DialogTitle>자산 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>자산 유형</Label>
            <div className="mt-1.5 grid grid-cols-4 gap-2">
              {ASSET_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  className={cn(
                    'rounded-lg border px-2 py-1.5 text-xs font-medium transition-colors',
                    assetType === type
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:bg-accent'
                  )}
                  onClick={() => handleTypeChange(type)}
                >
                  {ASSET_TYPE_LABELS[type]}
                </button>
              ))}
            </div>
          </div>

          {needsSymbol && (
            <div className="space-y-1.5" ref={searchRef}>
              <Label>종목 검색</Label>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={assetType === 'stock_kr' ? '삼성전자 또는 005930' : assetType === 'gold' ? 'GLD 또는 gold' : 'TSLA 또는 Tesla'}
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setShowResults(true);
                  }}
                  onFocus={() => searchQuery.length >= 2 && setShowResults(true)}
                  className="pl-9"
                />
                {isSearching && <Loader2 className="absolute right-2.5 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />}
              </div>
              {showResults && searchResults.length > 0 && (
                <div className="max-h-40 overflow-y-auto rounded-lg border border-border bg-popover shadow-md">
                  {searchResults.map((r) => (
                    <button
                      key={r.symbol}
                      type="button"
                      className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-accent transition-colors"
                      onClick={() => handleSelectResult(r)}
                    >
                      <span className="truncate">{r.name}</span>
                      <span className="ml-2 shrink-0 text-xs text-muted-foreground">
                        {r.symbol}{r.exchange ? ` · ${r.exchange}` : ''}
                      </span>
                    </button>
                  ))}
                </div>
              )}
              {symbol && (
                <p className="text-xs text-muted-foreground">
                  선택됨: <span className="font-medium text-foreground">{symbol}</span> — {name}
                </p>
              )}
            </div>
          )}

          <div className="space-y-1.5">
            <Label>{isInterestBased ? '상품명' : needsSymbol ? '자산명 (자동입력)' : '자산명'}</Label>
            <Input
              placeholder={isDeposit ? '신한 정기예금 1년' : isSavings ? '카카오뱅크 26주적금' : isParking ? '토스 파킹통장' : '삼성전자'}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          {isInterestBased && (
            <>
              <div className="space-y-1.5">
                <Label>은행/증권사명</Label>
                <Input placeholder="신한은행" value={bankName} onChange={(e) => setBankName(e.target.value)} />
              </div>

              {(isDeposit || isParking) && (
                <div className="space-y-1.5">
                  <Label>{isParking ? '현재 잔액 (원)' : '원금 (원)'}</Label>
                  <Input type="number" placeholder="10000000" value={principal} onChange={(e) => setPrincipal(e.target.value)} min="0" required />
                </div>
              )}

              {isSavings && (
                <div className="space-y-1.5">
                  <Label>월 납입액 (원)</Label>
                  <Input type="number" placeholder="300000" value={monthlyAmount} onChange={(e) => setMonthlyAmount(e.target.value)} min="1" required />
                </div>
              )}

              <div className="space-y-1.5">
                <Label>연이율 (%)</Label>
                <Input type="number" placeholder="3.5" value={interestRate} onChange={(e) => setInterestRate(e.target.value)} step="0.001" min="0.001" max="100" required />
              </div>

              {isDeposit && (
                <div>
                  <Label>이자 유형</Label>
                  <div className="mt-1.5 grid grid-cols-2 gap-2">
                    {(['simple', 'compound'] as const).map((type) => (
                      <button
                        key={type}
                        type="button"
                        className={cn(
                          'rounded-lg border px-3 py-2 text-sm transition-colors',
                          interestType === type
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border hover:bg-accent'
                        )}
                        onClick={() => setInterestType(type)}
                      >
                        {type === 'simple' ? '단리' : '복리 (월복리)'}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {(isDeposit || isSavings) && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>가입일</Label>
                    <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
                  </div>
                  <div className="space-y-1.5">
                    <Label>만기일</Label>
                    <Input type="date" value={maturityDate} onChange={(e) => setMaturityDate(e.target.value)} required />
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                <Label>이자소득세율 (%)</Label>
                <Input type="number" placeholder="15.4" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} step="0.1" min="0" max="100" />
              </div>
            </>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? '추가 중...' : '추가'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
