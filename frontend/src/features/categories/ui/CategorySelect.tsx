import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select';
import type { CategoryDirection } from '@/entities/category/model/types';
import { useCategories } from '../api';

interface CategorySelectProps {
  direction?: CategoryDirection;
  value: string | null;
  onChange: (value: string | null) => void;
  placeholder?: string;
}

const CLEAR_VALUE = '__clear__';

export function CategorySelect({
  direction,
  value,
  onChange,
  placeholder = '카테고리 선택',
}: CategorySelectProps) {
  const { data: categories = [], isLoading } = useCategories(direction);

  const handleValueChange = (selected: string) => {
    onChange(selected === CLEAR_VALUE ? null : selected);
  };

  return (
    <Select
      value={value ?? ''}
      onValueChange={handleValueChange}
      disabled={isLoading}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={CLEAR_VALUE}>
          <span className="text-muted-foreground">— 없음 —</span>
        </SelectItem>
        {categories.map((category) => (
          <SelectItem key={category.id} value={category.id}>
            <span className="flex items-center gap-2">
              {category.icon && (
                <span aria-hidden="true">{category.icon}</span>
              )}
              {category.color && (
                <span
                  className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: category.color }}
                  aria-hidden="true"
                />
              )}
              <span>{category.name}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
