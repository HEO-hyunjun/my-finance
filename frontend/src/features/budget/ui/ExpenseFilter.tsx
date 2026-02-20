import { useState } from 'react';
import type { BudgetCategory } from '@/shared/types';
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

export interface ExpenseFilterValues {
  category_id?: string;
  memo?: string;
  start?: string;
  end?: string;
}

interface ExpenseFilterProps {
  categories: BudgetCategory[];
  onFilterChange: (filters: ExpenseFilterValues) => void;
}

const ALL_VALUE = '__all__';

export function ExpenseFilter({ categories, onFilterChange }: ExpenseFilterProps) {
  const [categoryId, setCategoryId] = useState(ALL_VALUE);
  const [memo, setMemo] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const activeCategories = categories.filter((c) => c.is_active);

  const categoryOptions = [
    { value: ALL_VALUE, label: '전체' },
    ...activeCategories.map((c) => ({
      value: c.id,
      label: `${c.icon} ${c.name}`,
    })),
  ];

  const handleApply = () => {
    onFilterChange({
      category_id: categoryId !== ALL_VALUE ? categoryId : undefined,
      memo: memo || undefined,
      start: startDate || undefined,
      end: endDate || undefined,
    });
  };

  const handleReset = () => {
    setCategoryId(ALL_VALUE);
    setMemo('');
    setStartDate('');
    setEndDate('');
    onFilterChange({});
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end sm:gap-4">
          {/* 카테고리 */}
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">카테고리</Label>
            <Select value={categoryId} onValueChange={setCategoryId}>
              <SelectTrigger className="w-full sm:w-[160px]">
                <SelectValue placeholder="전체" />
              </SelectTrigger>
              <SelectContent>
                {categoryOptions.map((opt) => (
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
              className="w-full sm:w-[160px]"
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
          <div className="col-span-2 flex gap-2 sm:col-span-1">
            <Button onClick={handleApply} className="flex-1 sm:flex-none">검색</Button>
            <Button variant="outline" onClick={handleReset} className="flex-1 sm:flex-none">
              초기화
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
