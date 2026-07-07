import type { CategoryBudget, CategorySpendingRate } from '@/entities/budget/model/types';
import type { Category } from '@/entities/category/model/types';
import type { CarryoverSettingResponse } from '@/shared/types/carryover';

export interface UnifiedCategoryRow {
  category: Category;
  allocation: CategoryBudget | null;
  rate: CategorySpendingRate | null;
  allocated: number;
  spent: number;
  remaining: number;
  usage_rate: number;
  status: 'normal' | 'warning' | 'exceeded' | null;
  carryover: CarryoverSettingResponse | null;
}
