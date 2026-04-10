export type CategoryDirection = 'income' | 'expense';

export interface Category {
  id: string;
  direction: CategoryDirection;
  name: string;
  icon: string | null;
  color: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export interface CategoryCreate {
  direction: CategoryDirection;
  name: string;
  icon?: string | null;
  color?: string | null;
  sort_order?: number;
}

export interface CategoryUpdate {
  name?: string | null;
  icon?: string | null;
  color?: string | null;
  sort_order?: number | null;
  is_active?: boolean | null;
}
