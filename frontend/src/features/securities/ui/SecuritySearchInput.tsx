import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchSecurities, useEnsureSecurity } from '@/features/securities/api';
import { Input } from '@/shared/ui/input';
import type {
  SecuritySearchResult,
  SecurityEnsureResult,
} from '@/entities/security/model/types';

export interface SelectedSecurity {
  id: string;
  symbol: string;
  name: string;
  currency: string;
  exchange: string | null;
  current_price: number | null;
}

interface Props {
  value: SelectedSecurity | null;
  onSelect: (sec: SelectedSecurity) => void;
  onClear?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
}

function useDebounced<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

export function SecuritySearchInput({
  value,
  onSelect,
  onClear,
  placeholder = '심볼 또는 회사명 (예: MSFT)',
  autoFocus,
}: Props) {
  const [input, setInput] = useState(value?.symbol ?? '');
  const [open, setOpen] = useState(false);
  const debounced = useDebounced(input, 300);
  const ensure = useEnsureSecurity();
  const wrapperRef = useRef<HTMLDivElement>(null);

  // 같은 symbol에 대해 자동 ensure를 한 번만 호출하기 위한 가드
  const autoEnsuredRef = useRef<string | null>(null);

  const { data: results = [], isFetching } = useSearchSecurities(debounced);

  // input이 selected.symbol과 다르면 selected 해제
  useEffect(() => {
    if (value && input.trim().toUpperCase() !== value.symbol.toUpperCase()) {
      onClear?.();
    }
  }, [input, value, onClear]);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!wrapperRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const exactMatch = useMemo<SecuritySearchResult | null>(() => {
    const q = debounced.trim().toUpperCase();
    if (!q) return null;
    return results.find((r) => r.symbol.toUpperCase() === q) ?? null;
  }, [debounced, results]);

  function applyEnsureResult(r: SecurityEnsureResult) {
    onSelect({
      id: r.id,
      symbol: r.symbol,
      name: r.name,
      currency: r.currency,
      exchange: r.exchange,
      current_price: r.current_price,
    });
  }

  function handleChoose(hit: SecuritySearchResult) {
    setInput(hit.symbol);
    setOpen(false);
    ensure.mutate(hit.symbol, { onSuccess: applyEnsureResult });
  }

  // 정확 일치 → 자동 선택 (클릭 없이 MSFT만 입력해도 채워짐)
  useEffect(() => {
    if (!exactMatch) return;
    if (value && value.symbol.toUpperCase() === exactMatch.symbol.toUpperCase()) return;
    if (autoEnsuredRef.current === exactMatch.symbol) return;
    autoEnsuredRef.current = exactMatch.symbol;
    handleChoose(exactMatch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exactMatch?.symbol]);

  const status: { label: string; tone: 'ok' | 'warn' | 'busy' | 'idle' } = (() => {
    if (ensure.isPending) return { label: '확인 중…', tone: 'busy' };
    if (value && input.trim().toUpperCase() === value.symbol.toUpperCase()) {
      return { label: `${value.symbol} · ${value.currency}`, tone: 'ok' };
    }
    if (isFetching && debounced) return { label: '검색 중…', tone: 'busy' };
    if (debounced && results.length === 0 && !isFetching) {
      return { label: '결과 없음', tone: 'warn' };
    }
    return { label: '', tone: 'idle' };
  })();

  return (
    <div ref={wrapperRef} className="relative">
      <Input
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          autoEnsuredRef.current = null;
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
      />
      {status.label && (
        <div
          className={`mt-1 text-xs ${
            status.tone === 'ok'
              ? 'text-green-600'
              : status.tone === 'warn'
                ? 'text-amber-600'
                : 'text-muted-foreground'
          }`}
        >
          {status.label}
        </div>
      )}

      {open && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-md max-h-64 overflow-y-auto">
          {results.map((r) => (
            <button
              key={`${r.symbol}-${r.exchange ?? ''}`}
              type="button"
              onClick={() => handleChoose(r)}
              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-accent"
            >
              <span className="flex flex-col">
                <span className="font-medium">{r.symbol}</span>
                <span className="text-xs text-muted-foreground line-clamp-1">{r.name}</span>
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {r.currency}
                {r.exchange ? ` · ${r.exchange}` : ''}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
