import { useState } from 'react';
import { ASSET_TYPE_LABELS, TRANSACTION_TYPE_LABELS } from '@/shared/types';
import { Card, CardContent } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select';

interface TransactionFilterProps {
  onFilterChange: (filters: {
    asset_type?: string;
    tx_type?: string;
    memo?: string;
    start_date?: string;
    end_date?: string;
  }) => void;
}

const ALL_VALUE = '__all__';

const ASSET_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: ALL_VALUE, label: '전체' },
  ...Object.entries(ASSET_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

const TX_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: ALL_VALUE, label: '전체' },
  ...Object.entries(TRANSACTION_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

export function TransactionFilter({ onFilterChange }: TransactionFilterProps) {
  const [assetType, setAssetType] = useState(ALL_VALUE);
  const [txType, setTxType] = useState(ALL_VALUE);
  const [memo, setMemo] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const handleApply = () => {
    onFilterChange({
      asset_type: assetType !== ALL_VALUE ? assetType : undefined,
      tx_type: txType !== ALL_VALUE ? txType : undefined,
      memo: memo || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
  };

  const handleReset = () => {
    setAssetType(ALL_VALUE);
    setTxType(ALL_VALUE);
    setMemo('');
    setStartDate('');
    setEndDate('');
    onFilterChange({});
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-end gap-4">
          {/* 자산 유형 */}
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">자산 유형</Label>
            <Select value={assetType} onValueChange={setAssetType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="전체" />
              </SelectTrigger>
              <SelectContent>
                {ASSET_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 거래 유형 */}
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">거래 유형</Label>
            <Select value={txType} onValueChange={setTxType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="전체" />
              </SelectTrigger>
              <SelectContent>
                {TX_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 메모 검색 */}
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">메모 검색</Label>
            <Input
              type="text"
              placeholder="검색어 입력"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              className="w-[180px]"
            />
          </div>

          {/* 시작일 */}
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">시작일</Label>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          {/* 종료일 */}
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">종료일</Label>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          {/* 버튼 */}
          <div className="flex gap-2">
            <Button onClick={handleApply}>검색</Button>
            <Button variant="outline" onClick={handleReset}>
              초기화
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
