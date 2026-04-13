import { useEffect, useMemo, useState } from 'react';
import { Loader2, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
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
import { cn } from '@/shared/lib/utils';
import {
  usePortfolioTargets,
  useSetPortfolioTargets,
} from '@/features/portfolio/api';
import type { PortfolioTargetCreate } from '@/shared/types/portfolio';

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  cash: '현금',
  deposit: '예금',
  savings: '적금',
  parking: '파킹',
  investment: '투자',
};

const ALL_ASSET_TYPES = Object.keys(ACCOUNT_TYPE_LABELS);

type Row = { asset_type: string; percent: string };

function toPercentString(ratio: number): string {
  return (ratio * 100).toFixed(1);
}

export function TargetsEditor() {
  const { data, isLoading } = usePortfolioTargets();
  const setTargets = useSetPortfolioTargets();
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    if (!data) return;
    if (data.length === 0) {
      setRows([
        { asset_type: 'cash', percent: '' },
        { asset_type: 'parking', percent: '' },
        { asset_type: 'savings', percent: '' },
        { asset_type: 'investment', percent: '' },
      ]);
      return;
    }
    setRows(
      data.map((t) => ({
        asset_type: t.asset_type,
        percent: toPercentString(t.target_ratio),
      })),
    );
  }, [data]);

  const totalPercent = useMemo(() => {
    return rows.reduce((sum, r) => sum + (Number(r.percent) || 0), 0);
  }, [rows]);

  const availableTypes = useMemo(
    () => ALL_ASSET_TYPES.filter((t) => !rows.some((r) => r.asset_type === t)),
    [rows],
  );

  const isValid =
    rows.length > 0 &&
    Math.abs(totalPercent - 100) < 0.01 &&
    rows.every((r) => Number(r.percent) >= 0 && Number(r.percent) <= 100) &&
    new Set(rows.map((r) => r.asset_type)).size === rows.length;

  const handleAddRow = () => {
    if (availableTypes.length === 0) return;
    setRows([...rows, { asset_type: availableTypes[0], percent: '' }]);
  };

  const handleRemoveRow = (idx: number) => {
    setRows(rows.filter((_, i) => i !== idx));
  };

  const handleChange = (idx: number, key: keyof Row, value: string) => {
    setRows(rows.map((r, i) => (i === idx ? { ...r, [key]: value } : r)));
  };

  const handleSave = () => {
    if (!isValid) {
      toast.error('합계가 100%가 되도록 조정해주세요');
      return;
    }
    const payload: PortfolioTargetCreate[] = rows.map((r) => ({
      asset_type: r.asset_type,
      target_ratio: Number(r.percent) / 100,
    }));
    setTargets.mutate(payload, {
      onSuccess: () => toast.success('목표 비중이 저장되었습니다'),
      onError: () => toast.error('저장에 실패했습니다'),
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">목표 비중 설정</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">목표 비중 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          자산 유형별 목표 비중을 설정합니다. 합계는 반드시 100%여야 합니다.
        </p>

        <div className="space-y-2">
          {rows.map((row, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <div className="flex-1">
                <Select
                  value={row.asset_type}
                  onValueChange={(v) => handleChange(idx, 'asset_type', v)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ALL_ASSET_TYPES.map((t) => (
                      <SelectItem
                        key={t}
                        value={t}
                        disabled={
                          t !== row.asset_type &&
                          rows.some((r) => r.asset_type === t)
                        }
                      >
                        {ACCOUNT_TYPE_LABELS[t] ?? t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex w-36 items-center gap-1.5">
                <Input
                  type="number"
                  step="0.1"
                  min={0}
                  max={100}
                  value={row.percent}
                  onChange={(e) => handleChange(idx, 'percent', e.target.value)}
                  placeholder="0"
                  className="text-right"
                />
                <span className="text-sm text-muted-foreground">%</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleRemoveRow(idx)}
                aria-label="삭제"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleAddRow}
            disabled={availableTypes.length === 0}
          >
            <Plus className="mr-1 h-4 w-4" />
            자산 유형 추가
          </Button>
          <div className="flex items-center gap-3">
            <Label
              className={cn(
                'text-sm font-medium',
                Math.abs(totalPercent - 100) < 0.01
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-destructive',
              )}
            >
              합계 {totalPercent.toFixed(1)}%
            </Label>
            <Button
              onClick={handleSave}
              disabled={!isValid || setTargets.isPending}
              size="sm"
            >
              {setTargets.isPending && (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              )}
              저장
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
