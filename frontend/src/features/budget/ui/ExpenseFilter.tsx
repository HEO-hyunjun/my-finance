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
      start: startDate || undefined,
      end: endDate || undefined,
    });
  };

  const handleReset = () => {
    setCategoryId(ALL_VALUE);
    setStartDate('');
    setEndDate('');
    onFilterChange({});
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-end gap-4">
          {/* 카테고리 */}
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">카테고리</Label>
            <Select value={categoryId} onValueChange={setCategoryId}>
              <SelectTrigger className="w-[180px]">
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
