import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  BudgetCategory,
  BudgetCategoryCreateRequest,
  BudgetCategoryUpdateRequest,
  BudgetSummaryResponse,
  Expense,
  ExpenseCreateRequest,
  ExpenseUpdateRequest,
  PaginatedResponse,
  FixedExpense,
  FixedExpenseCreateRequest,
  FixedExpenseUpdateRequest,
  Installment,
  InstallmentCreateRequest,
  InstallmentUpdateRequest,
} from '@/shared/types';

// Query Keys

export const budgetKeys = {
  all: ['budget'] as const,
  categories: () => [...budgetKeys.all, 'categories'] as const,
  summary: (start?: string, end?: string) =>
    [...budgetKeys.all, 'summary', start, end] as const,
  expenses: () => [...budgetKeys.all, 'expenses'] as const,
  expenseList: (filters: Record<string, unknown>) =>
    [...budgetKeys.expenses(), filters] as const,
  fixedExpenses: () => [...budgetKeys.all, 'fixedExpenses'] as const,
  installments: () => [...budgetKeys.all, 'installments'] as const,
};

// --- Category Hooks ---

export function useCategories() {
  return useQuery({
    queryKey: budgetKeys.categories(),
    queryFn: async () => {
      const { data } = await apiClient.get<BudgetCategory[]>(
        '/v1/budget/categories',
      );
      return data;
    },
  });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: BudgetCategoryCreateRequest) => {
      const { data: result } = await apiClient.post<BudgetCategory>(
        '/v1/budget/categories',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.categories() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
    },
  });
}

export function useUpdateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: BudgetCategoryUpdateRequest;
    }) => {
      const { data: result } = await apiClient.put<BudgetCategory>(
        `/v1/budget/categories/${id}`,
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.categories() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
    },
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.put(`/v1/budget/categories/${id}`, { is_active: false });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.categories() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
    },
  });
}

// --- Summary Hook ---

export interface BudgetSummaryFilters {
  start?: string;
  end?: string;
}

export function useBudgetSummary(filters: BudgetSummaryFilters = {}) {
  return useQuery({
    queryKey: budgetKeys.summary(filters.start, filters.end),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.start) params.append('start', filters.start);
      if (filters.end) params.append('end', filters.end);
      const { data } = await apiClient.get<BudgetSummaryResponse>(
        `/v1/budget/summary?${params.toString()}`,
      );
      return data;
    },
  });
}

// --- Expense Hooks ---

export interface ExpenseFilters {
  category_id?: string;
  start?: string;
  end?: string;
  page?: number;
  per_page?: number;
}

export function useExpenses(filters: ExpenseFilters = {}) {
  return useQuery({
    queryKey: budgetKeys.expenseList(filters as Record<string, unknown>),
    queryFn: async () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
      const { data } = await apiClient.get<PaginatedResponse<Expense>>(
        `/v1/expenses?${params.toString()}`,
      );
      return data;
    },
  });
}

export function useCreateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ExpenseCreateRequest) => {
      const { data: result } = await apiClient.post<Expense>(
        '/v1/expenses',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.expenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useUpdateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: ExpenseUpdateRequest;
    }) => {
      const { data: result } = await apiClient.put<Expense>(
        `/v1/expenses/${id}`,
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.expenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useDeleteExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/expenses/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.expenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

// --- Fixed Expense Hooks ---

export function useFixedExpenses() {
  return useQuery({
    queryKey: budgetKeys.fixedExpenses(),
    queryFn: async () => {
      const { data } = await apiClient.get<FixedExpense[]>(
        '/v1/fixed-expenses',
      );
      return data;
    },
  });
}

export function useCreateFixedExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: FixedExpenseCreateRequest) => {
      const { data: result } = await apiClient.post<FixedExpense>(
        '/v1/fixed-expenses',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.fixedExpenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.expenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateFixedExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: FixedExpenseUpdateRequest;
    }) => {
      const { data: result } = await apiClient.put<FixedExpense>(
        `/v1/fixed-expenses/${id}`,
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.fixedExpenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.expenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useDeleteFixedExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/fixed-expenses/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.fixedExpenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.expenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useToggleFixedExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data: result } = await apiClient.patch<FixedExpense>(
        `/v1/fixed-expenses/${id}/toggle`,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.fixedExpenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.expenses() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// --- Installment Hooks ---

export function useInstallments() {
  return useQuery({
    queryKey: budgetKeys.installments(),
    queryFn: async () => {
      const { data } = await apiClient.get<Installment[]>('/v1/installments');
      return data;
    },
  });
}

export function useCreateInstallment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: InstallmentCreateRequest) => {
      const { data: result } = await apiClient.post<Installment>(
        '/v1/installments',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.installments() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
    },
  });
}

export function useUpdateInstallment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: InstallmentUpdateRequest;
    }) => {
      const { data: result } = await apiClient.put<Installment>(
        `/v1/installments/${id}`,
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.installments() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
    },
  });
}

export function useDeleteInstallment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/installments/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.installments() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.all });
    },
  });
}
